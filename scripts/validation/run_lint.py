#!/usr/bin/env python3
"""Strict controller lint over every supported Boolean architecture configuration.

Warnings are fatal. Only the exact source-local exceptions in lint_exceptions.json
are accepted; no command-line warning suppression or automatic waiver generation.
"""
import argparse, hashlib, itertools, json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
FLAGS = ('ENABLE_IQ_CAPTURE', 'LL_MINIMAL', 'GAUSS_TABLE', 'PDU_WRITE_STROBE')

def sources(root):
    files = sorted((root/'verilog').glob('*.v'))
    files = [f for f in files if not f.name.endswith('_tb.v') and f.name not in
             ('btle_controller_wrapper.v', 'sdpram_two_clk_xilinx.v')]
    if not files or not (root/'verilog/btle_controller.v').is_file():
        raise ValueError('missing controller RTL')
    return files

def exceptions(root, files):
    found = []
    for f in files:
        text = f.read_text()
        blocks = list(re.finditer(r'/\* verilator lint_off (\w+) \*/\n([^\n]+)\n/\* verilator lint_on \1 \*/', text))
        if text.count('lint_off') != len(blocks) or text.count('lint_on') != len(blocks):
            raise ValueError('unreviewed or broad lint directive: '+str(f))
        for m in blocks:
            found.append(dict(file=str(f.relative_to(root)), rule=m[1], declaration=m[2].strip()))
    expected = json.loads((root/'scripts/validation/lint_exceptions.json').read_text())
    if found != expected:
        raise ValueError('source-local lint exceptions differ from reviewed inventory')
    return found

def configurations(root):
    text = (root/'verilog/btle_controller.v').read_text().split(') (')[0]
    text = re.sub(r'//[^\n]*', '', text)
    names = [n for n in FLAGS if re.search(r'parameter\s+integer\s+'+n+r'\b', text)]
    return [dict(zip(names, bits)) for bits in itertools.product((0, 1), repeat=len(names))]

def complete_success(code, output):
    return code == 0 and not re.search(r'%Warning|%Error|\b(?:fatal|error):', output, re.I)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.timeout <= 0: raise ValueError('timeout must be positive')
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(status='FAIL', configurations=[], exceptions=[], rtl_sha256={})
    dest = args.output/'result.json'
    try:
        files = sources(ROOT)
        result['exceptions'] = exceptions(ROOT, files)
        result['rtl_sha256'] = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        executable = os.environ.get('VERILATOR', 'verilator')
        version = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=15)
        if version.returncode or not version.stdout.startswith('Verilator '):
            raise RuntimeError('Verilator version probe failed')
        result['tool'] = version.stdout.strip()
        configs = configurations(ROOT)
        if not configs: raise ValueError('empty lint configuration matrix')
        for index, params in enumerate(configs):
            cmd = [executable, '--lint-only', '--Wall', '--top-module', 'btle_controller']
            cmd += [f'-G{k}={v}' for k, v in params.items()]
            cmd += [str(f.relative_to(ROOT)) for f in files]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=args.timeout)
            output = run.stdout+run.stderr
            log = args.output/f'config-{index:02d}.log'
            log.write_text(output)
            ok = complete_success(run.returncode, output)
            result['configurations'].append(dict(parameters=params, command=cmd, exit=run.returncode,
                log=log.name, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), status='PASS' if ok else 'FAIL'))
        if len(result['configurations']) == len(configs) and all(r['status']=='PASS' for r in result['configurations']):
            result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = str(exc)
    dest.write_text(json.dumps(result, indent=2)+'\n')
    print(f"{result['status']}: {sum(r['status']=='PASS' for r in result['configurations'])}/{len(result['configurations'])} lint configurations; reviewed exceptions: {len(result['exceptions'])}")
    return 0 if result['status']=='PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
