#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Markdown summary of results/power/<label>/*.json (one file per scenario)."""
import json, sys
from pathlib import Path

run = Path(sys.argv[1])
order = ['rx', 'tx', 'mixed', 'idle', 'idle0']
data = {s: json.load(open(run / f'{s}.json')) for s in order if (run / f'{s}.json').exists()}

def pct(a, b):
    return 'n/a' if a == 0 else f'{100.0 * (b - a) / a:+.1f} %'
def fmt(x):
    return f'{x:,.0f}'.replace(',', ' ')

prov = (run / 'provenance.txt').read_text() if (run / 'provenance.txt').exists() else ''
dut = next((line[len('dut='):] for line in prov.splitlines() if line.startswith('dut=')), 'the dut')

print(f'# Switching activity, run `{run.name}`\n')
print('Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs '
      f'{dut} (dut), simulated side by side on identical stimuli. Setup subtracted; '
      'window = the same number of bb_clk cycles for both. Capacitance figures are '
      'liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.\n')

print('## Totals per scenario\n')
print('| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | '
      'Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |')
print('|---|---:|---|---:|---|---|---:|---|---:|---:|---|')
for s, d in data.items():
    r, u, w = d['ref'], d['dut'], d['window_cycles']
    rt, ut = r['toggles'] - r['clock_toggles'], u['toggles'] - u['clock_toggles']
    print(f"| {s} | {fmt(w)} | {rt/w:.1f} → {ut/w:.1f} | {pct(rt, ut)} | {r['hot_nets']} → {u['hot_nets']} | "
          f"{r['data_cap_tog']:.3g} → {u['data_cap_tog']:.3g} | {pct(r['data_cap_tog'], u['data_cap_tog'])} | "
          f"{r['clk_cap_tog']:.3g} → {u['clk_cap_tog']:.3g} | {pct(r['clk_cap_tog'], u['clk_cap_tog'])} | "
          f"{pct(r['data_cap_tog'] + r['clk_cap_tog'], u['data_cap_tog'] + u['clk_cap_tog'])} | "
          f"{fmt(r['mem_port_toggles'])} → {fmt(u['mem_port_toggles'])} |")
print('\nToggles exclude the clock nets; clock activity is in the CK-pin column.\n')

for s in ('mixed', 'rx', 'tx', 'idle'):
    if s not in data: continue
    d = data[s]; w = d['window_cycles']
    print(f'## Per block, scenario `{s}`\n')
    print('| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | '
          'Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |')
    print('|---|---|---|---:|---|---:|---|---:|---|---|')
    blocks = sorted(set(d['ref']['blocks']) | set(d['dut']['blocks']))
    for b in blocks:
        r = d['ref']['blocks'].get(b, {}); u = d['dut']['blocks'].get(b, {})
        g = lambda x, k: x.get(k, 0)
        rr = g(r, 'toggles') / max(g(r, 'nets'), 1) / w; ur = g(u, 'toggles') / max(g(u, 'nets'), 1) / w
        print(f"| {b} | {g(r,'cells')} → {g(u,'cells')} | {g(r,'toggles')/w:.1f} → {g(u,'toggles')/w:.1f} | "
              f"{pct(g(r,'toggles'), g(u,'toggles'))} | {g(r,'data_cap_tog'):.3g} → {g(u,'data_cap_tog'):.3g} | "
              f"{pct(g(r,'data_cap_tog'), g(u,'data_cap_tog'))} | {g(r,'clk_cap_tog'):.3g} → {g(u,'clk_cap_tog'):.3g} | "
              f"{pct(g(r,'clk_cap_tog'), g(u,'clk_cap_tog'))} | {rr:.4f} → {ur:.4f} | {g(r,'hot_nets')} → {g(u,'hot_nets')} |")
    print()

if 'mixed' in data:
    print('## Most active non-clock nets, scenario `mixed`\n')
    for d in ('ref', 'dut'):
        print(f'{d}:\n')
        print('| Toggle rate | Block | Net |'); print('|---:|---|---|')
        for rate, blk, net in data['mixed'][d]['top_nets'][:10]:
            print(f'| {rate:.3f} | {blk} | `{net}` |')
        print()
