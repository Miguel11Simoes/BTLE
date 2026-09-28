#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Summary of one run_tx_compare.sh label: TX area of the Gaussian filter options.

Reads results/area/<label>/<name>/summary.md (std cells, flip-flops, cell area,
SRAM macros and bits per top) and results/compare/<label>/openram_summary.md
(the OpenRAM macros of the SRAM tables), and prints Markdown tables. Also
writes data.json next to the summary.

Usage: summarize_tx.py <repo> <label>
"""
import json
import re
import sys
from pathlib import Path

VARIANTS = [  # name, Gaussian filter, where the table is, taps after fabrication
    ('master', 'upstream FIR, 17 terms', '- (9 tap registers)', 'rewritable'),
    ('ble-tx-fir2', 'folded FIR, 8 pairs + centre', '- (9 tap registers)', 'rewritable'),
    ('ble-tx-table', 'tables, constants', 'ROM: logic', 'fixed'),
    ('ble-tx-table-reg', 'tables, rebuilt from the taps', 'REG: 2 560 flip-flops', 'rewritable'),
    ('ble-tx-table-sram', 'tables, rebuilt from the taps', 'SRAM: 3 macros, 2 560 bits', 'rewritable'),
]
TABLE_MODULES = ['gauss_table_builder', 'gauss_table_reg', 'gauss_table_sram']


def num(x):
    return f'{x:,.0f}'.replace(',', ' ')


def pct(ref, val):
    d = 100.0 * (val - ref) / ref
    return '0' if abs(d) < 0.05 else f'{d:+.1f} %'


def read_area(path):
    rows = {}
    for line in path.read_text().splitlines():
        m = re.match(r'^\| `(\w+)` \| (\d+) \| (\d+) \| ([\d.]+) \| (\d+) \| (\d+) \|$', line)
        if m:
            rows[m.group(1)] = dict(cells=int(m.group(2)), flops=int(m.group(3)), area=float(m.group(4)),
                                    macros=int(m.group(5)), sram_bits=int(m.group(6)))
    return rows


def read_openram(path):
    macros = {}
    for line in path.read_text().splitlines():
        m = re.match(r'^\| `(\w+)` \| (\d+) x (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|', line)
        if m:
            macros[m.group(1)] = dict(words=int(m.group(2)), bits_per_word=int(m.group(3)), bits=int(m.group(4)),
                                      width=float(m.group(5)), height=float(m.group(6)), area=float(m.group(7)))
    return macros


def main():
    repo, label = Path(sys.argv[1]), sys.argv[2]
    area = {n: read_area(repo / 'results' / 'area' / label / n / 'summary.md') for n, *_ in VARIANTS}
    openram = read_openram(repo / 'results' / 'compare' / label / 'openram_summary.md')
    macro_area = sum(m['area'] for m in openram.values())
    macro_bits = sum(m['bits'] for m in openram.values())

    # table macros: only the SRAM variant has sdpram instances inside gauss_filter (2 560 bits)
    def table_macros(n):
        return macro_area if area[n]['gauss_filter']['sram_bits'] > 0 else 0.0

    def total(n, top):
        return area[n][top]['area'] + (table_macros(n) if top in ('gauss_filter', 'gfsk_modulation', 'btle_tx') else 0.0)

    ref = 'master'
    print(f'# TX area of the Gaussian filter options, run `{label}`\n')
    print('Yosys 0.68 + ABC, Nangate45 std cells; the SRAM banks of the tables are OpenRAM '
          f'macros in FreePDK45 ({num(macro_bits)} bits, {macro_area:.1f} µm²), added to the '
          'std-cell area. The RAMs every option shares (TX COS/SIN tables, 32 768 bits, and '
          'TX packet buffer, 4 096 bits) are left out. RX is not measured.\n')

    print('## `gauss_filter`\n')
    print('| Option | Branch | Table | Taps after fabrication | Std cells | Flip-flops | Cell area (µm²) '
          '| Table macros (µm²) | **Total (µm²)** | vs upstream FIR |')
    print('|---|---|---|---|---:|---:|---:|---:|---:|---:|')
    for n, what, where, taps in VARIANTS:
        g = area[n]['gauss_filter']
        t = total(n, 'gauss_filter')
        print(f"| {what} | `{n}` | {where} | {taps} | {num(g['cells'])} | {num(g['flops'])} | {g['area']:.1f} | "
              f"{table_macros(n):.1f} | **{t:.1f}** | {'—' if n == ref else pct(total(ref, 'gauss_filter'), t)} |")
    print()

    print('## Whole transmitter, `btle_tx`\n')
    print('| Option | Branch | Std cells | Flip-flops | Cell area (µm²) | Table macros (µm²) | **Total (µm²)** '
          '| vs upstream |')
    print('|---|---|---:|---:|---:|---:|---:|---:|')
    for n, what, *_ in VARIANTS:
        b = area[n]['btle_tx']
        t = total(n, 'btle_tx')
        print(f"| {what} | `{n}` | {num(b['cells'])} | {num(b['flops'])} | {b['area']:.1f} | {table_macros(n):.1f} | "
              f"**{t:.1f}** | {'—' if n == ref else pct(total(ref, 'btle_tx'), t)} |")
    print()

    print('## Inside the rewritable tables\n')
    print('| Branch | Part | Std cells | Flip-flops | Cell area (µm²) | Macros (µm²) |')
    print('|---|---|---:|---:|---:|---:|')
    for n in ('ble-tx-table-reg', 'ble-tx-table-sram'):
        for m in TABLE_MODULES:
            if m in area[n]:
                a = area[n][m]
                mac = macro_area if m == 'gauss_table_sram' else 0.0
                print(f"| `{n}` | `{m}` | {num(a['cells'])} | {num(a['flops'])} | {a['area']:.1f} | {mac:.1f} |")
    print()
    print('OpenRAM macros (FreePDK45, one read/write port):\n')
    print('| Macro | Words x bits | Bits | Area (µm²) | µm² per bit |')
    print('|---|---|---:|---:|---:|')
    for name, m in openram.items():
        print(f"| `{name}` | {m['words']} x {m['bits_per_word']} | {m['bits']} | {m['area']:.1f} | {m['area']/m['bits']:.2f} |")
    print()

    (repo / 'results' / 'compare' / label / 'data.json').write_text(json.dumps(
        dict(label=label, area=area, openram=openram, table_macro_area=macro_area,
             totals={n: {top: total(n, top) for top in ('gauss_filter', 'gfsk_modulation', 'btle_tx')}
                     for n, *_ in VARIANTS}), indent=1))


if __name__ == '__main__':
    main()
