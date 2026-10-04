"""Fail-closed verdicts shared by simulation and mutation runners."""
import argparse
from pathlib import Path
import re
import sys


BAD = re.compile(r"\b(?:FAIL(?:ED)?|MISMATCH|FATAL|ERROR)\b|\b[1-9]\d*\s+(?:difference|error)\s+found", re.I)


def bad_lines(text):
    # Upstream prints '0 error found! ... Test PASS.' on successful checks.
    return [line for line in text.splitlines()
            if BAD.search(re.sub(r"\b0\s+(?:difference|error)\s+found!?", "", line, flags=re.I))]


def sim_pass(code, text, marker):
    return code == 0 and bool(re.search(r"^\s*" + re.escape(marker) + r"(?:\s|:|$)", text, re.M)) and not bad_lines(text)


def mutant_caught(code, text):
    # Icarus $fatal(1) is exit 1. Crashes, timeouts and absent verdicts are errors.
    if code != 1 or re.search(r"queue overflows|stimulus.*(?:contract|invalid)|missing vectors", text, re.I):
        return False
    return bool(re.search(r"^\s*(?:MISMATCH\b|FAIL (?:sweep|random|macro|at)\b.*(?:I/Q|valid/last))", text, re.M))


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['pass', 'mutant', 'sby-pass', 'sby-fail', 'positive'])
    p.add_argument('args', nargs='+')
    a = p.parse_args()
    if a.mode == 'positive':
        try:
            ok = all(positive(s) for s in a.args)
        except (ValueError, argparse.ArgumentTypeError):
            ok = False
    else:
        code, filename, *rest = a.args
        code = int(code)
        text = Path(filename).read_text(errors='replace') if Path(filename).is_file() else ''
        if a.mode == 'pass':
            ok = sim_pass(code, text, rest[0])
        elif a.mode == 'mutant':
            ok = mutant_caught(code, text)
        else:
            expected = 'PASS' if a.mode == 'sby-pass' else 'FAIL'
            ok = code == (0 if expected == 'PASS' else 2) and text.split()[:1] == [expected]
    if not ok:
        print('VERDICT REJECTED: ' + a.mode + ' ' + ' '.join(a.args), file=sys.stderr)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
