"""Strict upstream regression: errors, missing stimuli and shared failures never PASS.

Usage: run_rx_regression.sh LABEL [REF_REV]
Env: OSS_CAD, PY, DUT_DEFAULTS, REGRESSION_JOBS (default 4),
REGRESSION_TIMEOUT (seconds, default 120), REGRESSION_SEED (default 1),
REGRESSION_VECTORS (optional saved vector directory containing config folders).
Exit 0: all 270 checks passed. Exit 1: failures/errors/differences. Exit 2:
incomplete stimulus coverage without other failures. Every log and exit code is kept.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from result_guard import bad_lines, positive

TBS = ('gfsk_demodulation_tb', 'btle_rx_core_tb', 'btle_rx_tb', 'btle_tx_tb', 'btle_controller_tb')
MARKERS = {
    'gfsk_demodulation_tb': ('output bit Test PASS.', 'output signal for decision Test PASS.'),
    'btle_rx_core_tb': ('Test PASS.', '0 difference found'),
    'btle_rx_tb': ('Test PASS.', '0 difference found'),
    'btle_tx_tb': ('output I Test PASS.', 'output Q Test PASS.'),
    'btle_controller_tb': ('output tx I Test PASS.', 'output tx Q Test PASS.', 'rx CRC Test PASS.', 'rx PDU Test PASS.', 'TEST FINISH.'),
}


def normalized(text):
    return ' '.join(text.split())


def classify(code, log, tb):
    if code != 0:
        return 'TIMEOUT' if code == 124 else 'ERROR'
    if re.search(r'\b(?:NO|NOT) INPUT!', log):
        return 'NO_STIMULUS'
    if bad_lines(log):
        return 'FAIL'
    flat = normalized(log)
    return 'PASS' if all(m in flat for m in MARKERS[tb]) else 'INCOMPLETE'


def output_problem(directory, names, allow_rejection=False):
    for name in names:
        path = directory / name
        if not path.is_file():
            return 'MISSING_OUTPUT'
        tokens = path.read_text().split()
        if any('x' in token.lower() or 'z' in token.lower() for token in tokens):
            return 'UNKNOWN_OUTPUT'
        reference = directory / (path.stem + '_ref.txt')
        if not tokens:
            crc_ref = directory / (path.stem + '_crc_ok_ref.txt')
            if (allow_rejection and name in {'btle_rx_test_output.txt', 'btle_rx_btle_rx_core_test_output.txt'}
                    and reference.is_file() and not reference.read_text().strip()
                    and crc_ref.is_file() and crc_ref.read_text().strip() == '0'):
                continue  # Explicit observed packet rejection, not an empty comparison.
            return 'MISSING_OUTPUT'
        # RX-core's bit dump is the raw demodulator stream; the similarly named
        # Python file is the decoded PDU bit stream. The upstream bench compares
        # the decoded octets below, not these two different bit streams.
        if name == 'btle_rx_btle_rx_core_test_output_bit.txt':
            continue
        if reference.is_file():
            expected = reference.read_text().split()
            if not expected:
                return 'EMPTY_REFERENCE'
            # These two benches dump octets as hex; every other output is decimal.
            radix = 16 if name in {'btle_rx_test_output.txt', 'btle_rx_btle_rx_core_test_output.txt'} else 10
            try:
                actual_values = [int(t, radix) for t in tokens]
                expected_values = [int(t, radix) for t in expected]
            except ValueError:
                return 'INVALID_OUTPUT_OR_REFERENCE'
            # The upstream demodulator checker deliberately skips its first
            # pipeline sample. RX core dumps the CRC after the checked PDU;
            # crc_ok is checked separately by the testbench.
            if name.startswith('btle_rx_gfsk_demodulation_test_output_'):
                actual_values = actual_values[1:]
            elif name == 'btle_rx_btle_rx_core_test_output.txt':
                if len(actual_values) < len(expected_values):
                    return 'OUTPUT_COUNT'
                actual_values = actual_values[:len(expected_values)]
            if len(actual_values) != len(expected_values):
                return 'OUTPUT_COUNT'
            if actual_values != expected_values:
                return 'FAIL'

    return None


def pair_verdict(ref, dut, outputs_equal):
    if any(s in {'ERROR', 'TIMEOUT', 'INCOMPLETE', 'MISSING_OUTPUT', 'UNKNOWN_OUTPUT', 'EMPTY_REFERENCE', 'INVALID_OUTPUT_OR_REFERENCE', 'OUTPUT_COUNT'} for s in (ref, dut)):
        return 'ERROR'
    if ref == dut == 'NO_STIMULUS':
        return 'NO_STIMULUS'
    if ref != dut or not outputs_equal:
        return 'DIFFERENT'
    return 'PASS' if ref == dut == 'PASS' else 'BOTH_FAIL'


def final_status(counts, expected):
    if sum(counts.values()) != expected or any(counts.get(k, 0) for k in ('ERROR', 'DIFFERENT', 'BOTH_FAIL')):
        return 'FAIL', 1
    if counts.get('NO_STIMULUS', 0):
        return 'INCOMPLETE', 2
    return ('PASS', 0) if counts.get('PASS', 0) == expected else ('FAIL', 1)


def run(cmd, cwd, log, timeout):
    with log.open('w') as stream:
        try:
            return subprocess.run(cmd, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            stream.write('\nHARNESS TIMEOUT\n')
            return 124
        except OSError as exc:
            stream.write(str(exc) + '\n')
            return 127


def manifest(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob('*.txt'))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('label')
    p.add_argument('ref_rev', nargs='?', default='upstream-baseline')
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', a.label) or a.label in {'.', '..'}:
        p.error('label must be a single directory name')
    repo = Path(__file__).resolve().parents[2]
    jobs = positive(os.environ.get('REGRESSION_JOBS', '4'))
    limit = positive(os.environ.get('REGRESSION_TIMEOUT', '120'))
    seed = positive(os.environ.get('REGRESSION_SEED', '1'))
    cad = Path(os.environ.get('OSS_CAD', str(Path.home() / 'eda/oss-cad-suite-20260907'))) / 'bin'
    iv = os.environ.get('IVERILOG', str(cad / 'iverilog'))
    vvp = os.environ.get('VVP', str(cad / 'vvp'))
    out = repo / 'results/validation' / a.label / 'rx_regression'
    out.mkdir(parents=True, exist_ok=False)
    os.environ['MPLBACKEND'] = 'Agg'
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    provenance = dict(ref=git('rev-parse', a.ref_rev).decode().strip(),
                      dut=git('rev-parse', 'HEAD').decode().strip(),
                      dut_defaults=os.environ.get('DUT_DEFAULTS', ''), seed=seed,
                      jobs=jobs, timeout=limit, python=sys.version,
                      simulator=vvp, compiler=iv,
                      dirty=git('status', '--porcelain', '--', 'verilog').decode(),
                      rtl_sha256={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((repo/'verilog').glob('*.v'))},
                      harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      trace_changes='Only $dumpfile/$dumpvars removed from simulation copies',
                      controller_tb='Bundled controller bench: U9, strict counts, unknown checks and explicit rejection')
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    configs = list(itertools.product((0, 1, 2), (20, 12, 8), (0, 20, 50), (0, 5)))
    with tempfile.TemporaryDirectory(prefix='btle-strict-') as temp:
        work = Path(temp)
        for side in ('ref', 'dut'):
            dest = work / side
            dest.mkdir()
            if side == 'ref':
                # git archive contains only trusted repository paths, extracted by git/tar.
                arc = subprocess.run(['git', '-C', str(repo), 'archive', a.ref_rev, 'verilog', 'python'], stdout=subprocess.PIPE, check=True)
                subprocess.run(['tar', '-x', '-C', str(dest)], input=arc.stdout, check=True)
            else:
                shutil.copytree(repo / 'verilog', dest / 'verilog', ignore=shutil.ignore_patterns('*.txt', '*.vcd', '*_tb'))
        for spec in os.environ.get('DUT_DEFAULTS', '').split():
            file, assignment = spec.split(':'); param, value = assignment.split('=')
            path = work / 'dut/verilog' / file
            text, n = re.subn(r'(parameter integer ' + re.escape(param) + r' = )\d+', r'\g<1>' + str(int(value)), path.read_text())
            if not n:
                raise RuntimeError('DUT_DEFAULTS not applied: ' + spec)
            path.write_text(text)
        tb_sources = {}
        files = {}
        outputs = {}
        for side in ('ref', 'dut'):
            rtl = work / side / 'verilog'
            for tb in TBS:
                source = (repo / 'scripts/validation/upstream_controller_tb.v' if tb == 'btle_controller_tb' else rtl / (tb + '.v')).read_text()
                source = re.sub(r'^\s*\$dump(?:file|vars)\b[^;]*;', '', source, flags=re.M)
                (rtl / (tb + '.v')).write_text(source)
                tb_sources[tb] = source
                names = re.findall(r'\b(\w*FILENAME)\s*=\s*"([^"]+)"', source)
                files[tb] = [name for key, name in names if 'OUTPUT' not in key or 'REF' in key]
                outputs[tb] = [name for key, name in names if 'OUTPUT' in key and 'REF' not in key]
                design = [str(f) for f in rtl.glob('*.v') if not f.name.endswith('_tb.v') and f.name not in {'btle_controller_wrapper.v', 'sdpram_two_clk_xilinx.v'}]
                code = run([iv, '-s', tb, '-o', str(work / side / tb), str(rtl / (tb + '.v')), *design], rtl, out / f'compile_{side}_{tb}.log', limit)
                if code:
                    (out / 'result.txt').write_text(f'RESULT: ERROR (compile {side}/{tb}, exit {code})\n')
                    return 1
        vecroot = Path(os.environ['REGRESSION_VECTORS']) if os.environ.get('REGRESSION_VECTORS') else out / 'vectors'
        def prepare(item):
            idx, (ex, snr, ppm, delay) = item
            name = f'ex{ex}_snr{snr}_ppm{ppm}_d{delay}'
            vec = vecroot / name
            if not os.environ.get('REGRESSION_VECTORS'):
                gen = work / ('gen_' + name)
                shutil.copytree(work / 'ref/python', gen / 'python')
                (gen / 'verilog').mkdir()
                # Seed the original unmodified generator before executing it.
                bootstrap = "import runpy,sys,numpy as np,random; s=int(sys.argv.pop(1)); np.random.seed(s); random.seed(s); runpy.run_path('test_vector_for_btle_verilog.py',run_name='__main__')"
                code = run([sys.executable, '-c', bootstrap, str(seed + idx), str(ex), str(snr), str(ppm), str(delay)], gen / 'python', out / f'gen_{name}.log', limit)
                if code:
                    raise RuntimeError(f'vector generation {name}: exit {code}')
                shutil.copytree(gen / 'verilog', vec)
            if not vec.is_dir():
                raise RuntimeError('missing vector directory: ' + str(vec))
            hashes = manifest(vec)
            (out / f'vectors_{name}.sha256').write_text(''.join(f'{h}  {f}\n' for f,h in hashes.items()))
            return name, vec
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            vectors = list(pool.map(prepare, enumerate(configs)))
        def execute(item):
            name, vec, tb = item
            case = work / (name + '_' + tb)
            statuses = {}; codes = {}; verdicts = {}; observed = {}; rejected = {}
            missing = [f for f in files[tb] if not (vec / f).is_file()]
            empty = [f for f in files[tb] if 'input' in f and (vec / f).is_file() and not (vec / f).read_text().strip()]
            if missing or empty:
                return dict(config=name, testbench=tb, ref_status='NO_STIMULUS', dut_status='NO_STIMULUS', ref_exit='', dut_exit='', outputs='not_run', result='NO_STIMULUS', coverage='not_run', detail='missing/empty: ' + ','.join(missing + empty))
            for side in ('ref', 'dut'):
                d = case / side; d.mkdir(parents=True)
                for f in vec.glob('*.txt'):
                    # Saved vectors may contain old simulator outputs. Only a
                    # file produced by this invocation can satisfy a check.
                    if f.name not in outputs[tb]:
                        shutil.copy2(f, d / f.name)
                logpath = d / 'sim.log'
                code = run([vvp, '-n', str(work / side / tb)], d, logpath, limit)
                log = logpath.read_text(errors='replace')
                status = classify(code, log, tb)
                if status == 'PASS':
                    status = output_problem(d, outputs[tb], allow_rejection='VERIFIED_REJECTION:' in log) or status
                observed[side] = {f:(d/f).read_bytes() for f in outputs[tb] if (d/f).is_file()}
                statuses[side] = status; codes[side] = code
                rejected[side] = 'VERIFIED_REJECTION:' in log
                verdicts[side] = normalized('\n'.join(l for l in log.splitlines() if re.search(r'Test PASS|Test FAIL|difference found|error found|NO INPUT|FATAL|ERROR', l, re.I)))
                with gzip.open(out / f'{name}_{tb}_{side}.log.gz', 'wt') as f:
                    f.write(log)
                (out / f'{name}_{tb}_{side}.outputs.json').write_text(json.dumps({f:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for f,data in observed[side].items()},sort_keys=True))
                if status != 'PASS':
                    with gzip.open(out / f'{name}_{tb}_{side}.outputs.json.gz', 'wt') as f:
                        json.dump({name:data.decode(errors='replace') for name,data in observed[side].items()},f)
            equal = observed['ref'] == observed['dut'] and verdicts['ref'] == verdicts['dut']
            result = pair_verdict(statuses['ref'], statuses['dut'], equal)
            return dict(config=name, testbench=tb, ref_status=statuses['ref'], dut_status=statuses['dut'], ref_exit=codes['ref'], dut_exit=codes['dut'], outputs='equal' if equal else 'different', result=result, coverage='packet_rejection' if all(rejected.values()) else 'data_comparison', detail=verdicts['ref'] + ' | ' + verdicts['dut'])
        tasks = [(name, vec, tb) for name,vec in vectors for tb in TBS]
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            rows = list(pool.map(execute, tasks))
        with (out / 'summary.tsv').open('w',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');writer.writeheader();writer.writerows(rows)
        counts = Counter(row['result'] for row in rows)
        status, code = final_status(counts, len(configs)*len(TBS))
        result = f'runs={len(rows)} ' + ' '.join(f'{k}={counts[k]}' for k in ('PASS','BOTH_FAIL','NO_STIMULUS','DIFFERENT','ERROR')) + f'\nRESULT: {status}\n'
        (out / 'result.txt').write_text(result)
        print(result, end='')
        return code


if __name__ == '__main__':
    sys.exit(main())
