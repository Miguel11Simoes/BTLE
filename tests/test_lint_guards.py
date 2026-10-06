"""Require real lint diagnostics and illegal-state failures for deliberate defects."""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('lint_gate', ROOT/'scripts/validation/run_lint.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    # A diagnostic must fail even if a wrapper accidentally returns zero.
    assert not gate.complete_success(0, '%Warning-WIDTH: deliberate width mismatch')
    assert not gate.complete_success(0, '%Error: deliberate simulator/tool error')
    assert not gate.complete_success(1, '')
    assert gate.complete_success(0, '')
    rows = []
    with tempfile.TemporaryDirectory(prefix='btle-lint-guards-') as temp:
        work = Path(temp)
        for d in ('verilog', 'tests', 'scripts/validation'):
            shutil.copytree(ROOT/d, work/d, ignore=shutil.ignore_patterns('__pycache__', '*.vcd', '*.txt'))

        def run(name, recovery=False, expected=None):
            output = work/'evidence'/name
            script = 'tests/test_lint_recovery.py' if recovery else 'scripts/validation/run_lint.py'
            proc = subprocess.run([sys.executable, str(work/script), '--output', str(output)], cwd=work,
                                  capture_output=True, text=True, timeout=300)
            text = proc.stdout+proc.stderr
            for log in sorted(output.glob('*.log')):
                text += '\n'+log.read_text()
            report = json.loads((output/'result.json').read_text()) if (output/'result.json').exists() else {}
            if 'error' in report:
                text += '\n'+report['error']
            good = (proc.returncode == 0 and report.get('status') == 'PASS') if expected is None else (
                proc.returncode != 0 and expected in text and report.get('status') != 'PASS')
            (a.output/(name+'.log')).write_text(text)
            rows.append(dict(name=name, exit=proc.returncode, expected_failure=expected is not None,
                             witness=expected, status='PASS' if good else 'FAIL'))
            if not good:
                raise RuntimeError(name+' did not produce its concrete witness: '+text[-2000:])

        run('baseline-lint')
        run('baseline-recovery', recovery=True)
        mutations = [
          ('width', 'btle_ll.v', "axi_araddr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};", "axi_araddr  <= 32'b0;", '%Warning-WIDTHTRUNC'),
          ('unused', 'btle_controller.v', 'endmodule', 'wire accidental_orphan_signal = gpio[0];\nendmodule', '%Warning-UNUSEDSIGNAL'),
          ('syntax', 'btle_controller.v', 'endmodule', 'endmodul', '%Error'),
          ('unreviewed-waiver', 'btle_controller.v', 'endmodule', '/* verilator lint_off WIDTH */\nendmodule', 'unreviewed or broad lint directive'),
        ]
        for name, file, before, after, witness in mutations:
            f = work/'verilog'/file
            original = f.read_text()
            if original.count(before) != 1:
                raise RuntimeError('mutation target not unique: '+name)
            try:
                f.write_text(original.replace(before, after))
                run(name, expected=witness)
            finally:
                f.write_text(original)
        for file, state, witness in [('btle_ll.v', 'll_state', 'LL illegal state did not recover'),
                                     ('btle_rx_core.v', 'phy_rx_state', 'RX illegal state did not recover safely'),
                                     ('crc24.v', 'crc_state', 'CRC illegal state did not recover safely')]:
            f = work/'verilog'/file
            original = f.read_text()
            marker = 'case('+state+')'
            if marker not in original:
                continue  # One-bit CRC implementation has no unused binary encoding.
            start = original.index(marker)
            end = original.index('endcase', start)
            body, count = re.subn(r'\s+default: begin\s+.*?\s+end\s*$', '\n    ', original[start:end], flags=re.S)
            if count != 1:
                raise RuntimeError('recovery mutation target not unique: '+state)
            try:
                f.write_text(original[:start]+body+original[end:])
                run('missing-'+state+'-lint', expected='%Warning-CASEINCOMPLETE')
                run('missing-'+state+'-behavior', recovery=True, expected=witness)
            finally:
                f.write_text(original)
    (a.output/'result.json').write_text(json.dumps(dict(status='PASS', checks=rows), indent=2)+'\n')
    print(f'PASS: {len(rows)} baseline/negative-control checks; tool errors and warnings remain fatal')


if __name__ == '__main__':
    main()
