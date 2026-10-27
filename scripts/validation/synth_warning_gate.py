#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""The synthesis and layout warning gate of ble-rx-best, ble-rx-micro and ble-tx-min: every warning of a run must be one
of the reviewed exceptions of synth_warning_exceptions.tsv, else the gate fails.

  synth_warning_gate.py [--vivado LOG ...] [--yosys DIR ...] [--librelane DIR ...] [--exceptions TSV]

--vivado:    a Vivado log (synthesis and implementation; impl.tcl mode ooc_hd prints every message): its
             WARNING and CRITICAL WARNING lines; its ERROR lines fail the gate.
--yosys:     a results/area/<label>/ directory of run_area.sh: the Warning lines of every top's yosys.log.gz.
--librelane: a results/layout/<label>/ directory of run.sh: warning.log (every warning of the flow), and
             the signoff metrics, which must be clean (DRC, LVS, antenna, setup, hold, slew, capacitance,
             fanout).
The exceptions are tab-separated: tool, a regular expression the whole warning line must match, the reason.
Prints each warning with the exception it falls under, the unreviewed ones, and RESULT: PASS or FAIL.
"""
import argparse
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_exceptions(path):
    ex = []
    for n, line in enumerate(open(path), 1):
        if not line.strip() or line.startswith('#'):
            continue
        f = line.rstrip('\n').split('\t')
        if len(f) != 3:
            sys.exit('%s:%d: tool, pattern, reason' % (path, n))
        ex.append((f[0], re.compile(f[1]), f[2], n))
    return ex


def vivado(path):
    warn, err = [], []
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('WARNING:') or line.startswith('CRITICAL WARNING:'):
            warn.append(re.sub(r' \[[A-Za-z]:/[^\]]*\]$', '', line))   # the source file and line: not part of it
        elif line.startswith('ERROR:'):
            err.append(line)
    return warn, err


def yosys(d):
    warn = []
    for f in sorted(glob.glob(os.path.join(d, '*', 'yosys.log.gz'))):
        top = os.path.basename(os.path.dirname(f))
        for line in gzip.open(f, 'rt', errors='replace'):
            if line.startswith('Warning'):
                warn.append('%s: %s' % (top, line.rstrip('\n')))
    return warn


SIGNOFF = {   # the metric, and what it must be
    'route__drc_errors': 0, 'klayout__drc_error__count': 0, 'magic__drc_error__count': 0,
    'design__lvs_error__count': 0, 'antenna__violating__nets': 0,
    'design__max_slew_violation__count': 0, 'design__max_cap_violation__count': 0,
    'design__max_fanout_violation__count': 0,
}


def fanout_violators(d):
    """(pin, fanout) of every max-fanout violation, over the signoff corners' checks reports."""
    out = set()
    for f in glob.glob(os.path.join(d, 'sta', '*.checks.rpt.gz')):
        on = False   # inside the 'max fanout' table of the report
        for line in gzip.open(f, 'rt', errors='replace'):
            s = line.strip()
            if s == 'max fanout':
                on = True
            elif on and 'VIOLATED' in s:
                p = s.split()
                out.add((p[0], int(p[2])))
            elif on and (s.startswith('max ') or s.startswith('===')):
                on = False
    return sorted(out)


def librelane(d, ex):
    """Warnings, errors, and the metric exceptions used [(exception line, what)]."""
    warn, err, used = [], [], []
    w = os.path.join(d, 'warning.log')
    if not os.path.exists(w):
        err.append('%s: no warning.log' % d)
    else:
        warn = [l.rstrip('\n') for l in open(w, errors='replace') if l.strip()]
    m = json.load(open(os.path.join(d, 'metrics.json')))
    metric_ex = {e[1].pattern: e for e in ex if e[0] == 'librelane-metric'}
    for k, want in SIGNOFF.items():
        v = m.get(k)
        if v is not None and v == want:
            continue
        e = metric_ex.get(k)
        if e and k == 'magic__drc_error__count' and m.get('klayout__drc_error__count') == 0:
            # Magic's errors, every one inside the GlobalFoundries SRAM (run.sh's check), the foundry's deck 0
            s = os.path.join(d, 'magic_drc_sram.txt')
            if os.path.exists(s) and re.search(r'\b(\d+) located, 0 outside the SRAM', open(s).read()):
                used.append((e[3], '%s = %s: %s' % (k, v, open(s).read().strip())))
                continue
        if e and k == 'design__max_fanout_violation__count':
            vio = fanout_violators(d)
            if vio and all(re.fullmatch(r'clkbuf_\S+/Z', p) for p, _ in vio):
                used.append((e[3], '%s = %s: clock-tree buffers %s' % (k, v, ', '.join('%s (%d)' % x for x in vio))))
                continue
        err.append('%s: %s = %s (must be %s)' % (d, k, v, want))
    for k in ('timing__setup__ws', 'timing__hold__ws'):
        if m.get(k) is None or m[k] < 0:
            err.append('%s: %s = %s (must be >= 0)' % (d, k, m.get(k)))
    return warn, err, used


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--vivado', nargs='*', default=[])
    ap.add_argument('--yosys', nargs='*', default=[])
    ap.add_argument('--librelane', nargs='*', default=[])
    ap.add_argument('--exceptions', default=os.path.join(HERE, 'synth_warning_exceptions.tsv'))
    a = ap.parse_args()
    ex = load_exceptions(a.exceptions)
    runs = [('vivado', p, *vivado(p), []) for p in a.vivado] + [('yosys', p, yosys(p), [], []) for p in a.yosys] + \
           [('librelane', p, *librelane(p, ex)) for p in a.librelane]
    bad = 0
    for tool, path, warn, err, metric_used in runs:
        used = {}
        unrev = []
        for w in warn:
            hit = next((e for e in ex if e[0] == tool and e[1].fullmatch(w)), None)
            if hit:
                used[hit[3]] = used.get(hit[3], 0) + 1
            else:
                unrev.append(w)
        print('== %s %s: %d warnings, %d reviewed, %d unreviewed, %d errors' % (tool, path, len(warn), len(warn) - len(unrev), len(unrev), len(err)))
        for n, c in sorted(used.items()):
            e = next(e for e in ex if e[3] == n)
            print('   reviewed (exception line %d) x %d: %s' % (n, c, e[2]))
        for n, what in metric_used:
            e = next(e for e in ex if e[3] == n)
            print('   reviewed signoff metric (exception line %d): %s; %s' % (n, what, e[2]))
        for w in sorted(set(unrev)):
            print('   UNREVIEWED x %d: %s' % (unrev.count(w), w))
        for e in err:
            print('   ERROR: %s' % e)
        bad |= bool(unrev or err)
    print('RESULT: %s' % ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
