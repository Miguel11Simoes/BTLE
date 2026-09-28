#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Cross-branch summary of one run_compare.sh label.

Reads only committed files:
  results/area/<label>/<name>/summary.md
  results/timing/<label>/<name>/summary.tsv, endpoints.txt
  results/power/<label>/<name>/<scenario>.json, runs.txt
  results/compare/<label>/provenance.txt
and prints Markdown tables (one column per configuration, the first one being
the reference) plus consistency checks. Also writes data.json next to the
summary.

Usage: summarize_compare.py <repo> <label> <name> ...
"""
import json
import re
import sys
from pathlib import Path

SCENARIOS = ['rx', 'tx', 'mixed', 'idle', 'idle0']
AREA_TOPS = ['btle_controller', 'btle_phy', 'btle_rx', 'btle_tx', 'gauss_filter',
             'btle_ll', 'auxiliary_daemon', 'clock_domain_conversion_iq']
BLOCKS = ['btle_rx', 'gauss_filter', 'btle_tx (other)', 'btle_ll', 'auxiliary_daemon',
          'clock_domain_conversion', 'top glue']


def num(x):
    return f'{x:,.0f}'.replace(',', ' ')


def same(a, b):
    """Counts must be equal. Capacitance sums (floats) are equal up to the order
    in which saif_activity.py adds them: it iterates over Python sets, whose order
    changes from one process to the next, so the last bits (~1e-15) may differ."""
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1.0)
    return a == b


def same_all(xs, ys):
    return len(xs) == len(ys) and all(same(x, y) for x, y in zip(xs, ys))


def pct(ref, val):
    if ref == 0:
        return '0' if val == 0 else 'n/a'
    d = 100.0 * (val - ref) / ref
    return '0' if abs(d) < 0.05 else f'{d:+.1f} %'


def read_area(run):
    rows = {}
    for line in (run / 'summary.md').read_text().splitlines():
        m = re.match(r'^\| `(\w+)` \| (\d+) \| (\d+) \| ([\d.]+) \| (\d+) \| (\d+) \|$', line)
        if m:
            rows[m.group(1)] = dict(cells=int(m.group(2)), flops=int(m.group(3)), area=float(m.group(4)),
                                    macros=int(m.group(5)), sram_bits=int(m.group(6)))
    return rows


def read_timing(run):
    rows = {}
    lines = (run / 'summary.tsv').read_text().splitlines()
    head = lines[0].split('\t')
    for line in lines[1:]:
        v = line.split('\t')
        rows[v[0]] = {k: float(x) for k, x in zip(head[1:], v[1:])}
    for line in (run / 'endpoints.txt').read_text().splitlines():
        name, rest = line.split('\t', 1)
        start, _, end = rest.partition('End-point = ')
        rows.setdefault(name, {})['start'] = start.strip().rstrip('.')
        rows[name]['end'] = end.strip().rstrip('.')
    return rows


def read_activity(run):
    out = {}
    events = {}
    runs = run / 'runs.txt'
    if runs.exists():
        for line in runs.read_text().splitlines():
            s, _, rest = line.partition(': ')
            events[s] = rest
    for s in SCENARIOS:
        f = run / f'{s}.json'
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        w = d['window_cycles']
        side = {}
        for k in ('ref', 'dut'):
            r = d[k]
            side[k] = dict(
                toggles_per_cycle=(r['toggles'] - r['clock_toggles']) / w,
                hot_nets=r['hot_nets'], data=r['data_cap_tog'], clock=r['clk_cap_tog'],
                total=r['data_cap_tog'] + r['clk_cap_tog'], mem=r['mem_port_toggles'], cells=r['cells'],
                blocks={b: dict(toggles_per_cycle=v['toggles'] / w, data=v['data_cap_tog'],
                                clock=v['clk_cap_tog'], cells=v['cells'])
                        for b, v in r['blocks'].items()})
        side['window'] = w
        side['events'] = events.get(s, '')
        out[s] = side
    return out


def main():
    repo, label, names = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    res = repo / 'results'
    prov = (res / 'compare' / label / 'provenance.txt').read_text()
    conf = {}
    for line in prov.splitlines():
        v = line.strip().split('\t')
        if len(v) == 5 and v[0] in names:
            conf[v[0]] = dict(rev=v[1], commit=v[2], tree=v[3], params=v[4])
    area = {n: read_area(res / 'area' / label / n) for n in names}
    timing = {n: read_timing(res / 'timing' / label / n) for n in names}
    act = {n: read_activity(res / 'power' / label / n) for n in names}
    ref = names[0]
    checks = []

    print(f'# Cross-branch comparison, run `{label}`\n')
    print('Each branch in its own configuration, measured in one run with the same flows '
          '(Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; '
          'Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: '
          '`vectors.tar.gz`). '
          f'Differences are relative to `{ref}`.\n')

    print('## Configurations\n')
    print('| Branch | Measured revision | Commit | `verilog/` tree | Parameters |')
    print('|---|---|---|---|---|')
    for n in names:
        c = conf.get(n, {})
        print(f"| `{n}` | `{c.get('rev', '?')}` | `{c.get('commit', '?')[:7]}` | `{c.get('tree', '?')[:7]}` | "
              f"{c.get('params', '?')} |")
    print()

    # ------------------------------------------------------------------ area
    print('## Area, `btle_controller`\n')
    print('| Measure | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
    print('|---|' + '---:|' * len(names))
    for key, title, fmt in (('cells', 'Std cells', num), ('flops', 'Flip-flops', num),
                            ('area', 'Cell area (µm²)', lambda x: num(round(x))),
                            ('sram_bits', 'SRAM bits', num)):
        r0 = area[ref]['btle_controller'][key]
        cells = []
        for n in names:
            v = area[n]['btle_controller'][key]
            cells.append(fmt(v) if n == ref else f'{fmt(v)} ({pct(r0, v)})')
        print(f'| {title} | ' + ' | '.join(cells) + ' |')
    print()
    print('Std cells per top (each top synthesised alone):\n')
    print('| Top | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
    print('|---|' + '---:|' * len(names))
    for top in AREA_TOPS:
        r0 = area[ref].get(top, {}).get('cells', 0)
        cells = []
        for n in names:
            v = area[n].get(top, {}).get('cells')
            cells.append('—' if v is None else (num(v) if n == ref else f'{num(v)} ({pct(r0, v)})'))
        print(f'| `{top}` | ' + ' | '.join(cells) + ' |')
    print()
    base = res / 'area' / 'baseline-upstream'
    if base.exists():
        b = read_area(base)['btle_controller']['cells']
        v = area[ref]['btle_controller']['cells']
        checks.append((f'`{ref}` controller cells equal the committed run `baseline-upstream` ({num(b)})', v == b))

    # additivity of the cell savings: each change alone vs all together
    if all(n in names for n in ('ble-tx-table', 'ble-rx-dm', 'ble-opt')):
        c = {n: area[n]['btle_controller']['cells'] for n in names}
        s_tx, s_rx, s_all = c[ref] - c['ble-tx-table'], c[ref] - c['ble-rx-dm'], c[ref] - c['ble-opt']
        a1a2 = sum(area[ref][t]['cells'] - area['ble-opt'][t]['cells'] for t in ('auxiliary_daemon', 'btle_ll'))
        print('Additivity of the savings (std cells of `btle_controller`):\n')
        print('| Saving | Cells |')
        print('|---|---:|')
        print(f'| B2 alone (`ble-tx-table`) | {num(s_tx)} |')
        print(f'| B1 alone (`ble-rx-dm`) | {num(s_rx)} |')
        print(f'| A1 + A2, measured on their own tops (`auxiliary_daemon`, `btle_ll`) | {num(a1a2)} |')
        print(f'| **Sum of the parts** | **{num(s_tx + s_rx + a1a2)}** |')
        print(f'| **All together (`ble-opt`)** | **{num(s_all)}** |')
        print(f'| Residual (interaction + flow noise) | {num(s_all - (s_tx + s_rx + a1a2))} |')
        print()

    # ---------------------------------------------------------------- timing
    print('## Static timing, `btle_controller`, 62.5 ns (16 MHz)\n')
    print('| Measure | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
    print('|---|' + '---:|' * len(names))
    for key, title, unit in (('unbuffered_ns', 'Unbuffered path', ' ns'), ('comb_path_ns', 'Logic path', ' ns'),
                             ('seq_overhead_ns', 'Register overhead', ' ns'), ('min_period_ns', 'Min period', ' ns'),
                             ('slack_at_target_ns', 'Slack at 62.5 ns', ' ns'), ('fmax_MHz', 'Fmax', ' MHz')):
        r0 = timing[ref]['dut_controller'][key]
        cells = []
        for n in names:
            v = timing[n]['dut_controller'][key]
            s = f'{v:.3f}{unit}' if unit == ' ns' else f'{v:.1f}{unit}'
            cells.append(s if n == ref or key == 'slack_at_target_ns' else f'{s} ({pct(r0, v)})')
        print(f'| {title} | ' + ' | '.join(cells) + ' |')
    print()
    print('| Branch | Worst path start | End |')
    print('|---|---|---|')
    for n in names:
        t = timing[n]['dut_controller']
        print(f"| `{n}` | `{t.get('start', '?')}` | `{t.get('end', '?')}` |")
    print()
    r_rows = [timing[n].get('ref_controller') for n in names]
    ok_t = all(r and r.get('min_period_ns') == r_rows[0].get('min_period_ns') and r.get('start') == r_rows[0].get('start')
               for r in r_rows)
    checks.append(('upstream controller timed identically in every run (period and path)', ok_t))
    t0 = timing[ref]
    checks.append((f'`{ref}` dut controller timed identically to the upstream reference',
                   t0['dut_controller'].get('min_period_ns') == t0['ref_controller'].get('min_period_ns')))

    # -------------------------------------------------------------- activity
    print('## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)\n')
    print('Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): '
          'a pre-layout proxy, not power. Δ against upstream in the same simulation.\n')
    print('| Scenario | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
    print('|---|' + '---:|' * len(names))
    for s in SCENARIOS:
        cells = []
        for n in names:
            d = act[n].get(s)
            if not d:
                cells.append('—'); continue
            cells.append(f"{d['dut']['total']:.3g}" if n == ref else
                         f"{d['dut']['total']:.3g} ({pct(d['ref']['total'], d['dut']['total'])})")
        print(f'| `{s}` | ' + ' | '.join(cells) + ' |')
    print()
    for s in SCENARIOS:
        if not all(s in act[n] for n in names):
            continue
        print(f'### Scenario `{s}`\n')
        print('| Measure | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
        print('|---|' + '---:|' * len(names))
        for key, title, f in (('toggles_per_cycle', 'Non-clock toggles / cycle', lambda x: f'{x:.1f}'),
                              ('hot_nets', 'Nets with activity > 10 %', num),
                              ('data', 'Data load × toggles (fF)', lambda x: f'{x:.3g}'),
                              ('clock', 'Clock (CK pins) load × toggles (fF)', lambda x: f'{x:.3g}'),
                              ('total', '**Data + clock**', lambda x: f'{x:.3g}'),
                              ('mem', 'RAM-port toggles', num)):
            r0 = act[ref][s]['dut'][key]
            cells = []
            for n in names:
                v = act[n][s]['dut'][key]
                cells.append(f(v) if n == ref else f'{f(v)} ({pct(act[n][s]["ref"][key], v)})')
            print(f'| {title} | ' + ' | '.join(cells) + ' |')
        print()
        if s in ('mixed', 'rx', 'tx', 'idle'):
            print(f'Toggles / cycle per block, `{s}`:\n')
            print('| Block | ' + ' | '.join(f'`{n}`' for n in names) + ' |')
            print('|---|' + '---:|' * len(names))
            for b in BLOCKS:
                r0 = act[ref][s]['dut']['blocks'].get(b, {}).get('toggles_per_cycle', 0.0)
                cells = []
                for n in names:
                    v = act[n][s]['dut']['blocks'].get(b, {}).get('toggles_per_cycle', 0.0)
                    cells.append(f'{v:.1f}' if n == ref else f'{v:.1f} ({pct(r0, v)})')
                print(f'| {b} | ' + ' | '.join(cells) + ' |')
            print()
    keys = ('toggles_per_cycle', 'hot_nets', 'mem', 'data', 'clock')
    for s in SCENARIOS:
        refs = [act[n][s]['ref'] for n in names if s in act[n]]
        ok = all(same_all([r[k] for k in keys], [refs[0][k] for k in keys]) for r in refs)
        checks.append((f'upstream side identical in every run, scenario `{s}`', ok))
        d0 = act[ref].get(s)
        if d0:
            checks.append((f'`{ref}` equals upstream exactly, scenario `{s}`',
                           same_all([d0['dut'][k] for k in keys], [d0['ref'][k] for k in keys])))
    vref = res / 'compare' / label / 'vectors.sha256'
    for n in names:
        f = res / 'power' / label / n / 'vectors.sha256'
        checks.append((f'`{n}`: activity run on the shared vector set (`vectors.sha256`)',
                       vref.exists() and f.exists() and f.read_text() == vref.read_text()))
    for n in names:
        ok = all(s in act[n] and 'mismatches 0' in act[n][s]['events'] for s in SCENARIOS)
        checks.append((f'`{n}`: gate-level outputs identical to upstream on every clock, 5 scenarios', ok))

    print('## Consistency checks\n')
    print('| Check | Result |')
    print('|---|---|')
    for text, ok in checks:
        print(f"| {text} | {'PASS' if ok else '**FAIL**'} |")
    print()

    (res / 'compare' / label / 'data.json').write_text(json.dumps(
        dict(label=label, names=names, configurations=conf, area=area, timing=timing, activity=act,
             checks=[dict(check=t, ok=ok) for t, ok in checks]), indent=1))
    if not all(ok for _, ok in checks):
        sys.exit(1)


if __name__ == '__main__':
    main()
