#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Summarise a results/area/<label>/ run as a Markdown table.

Per top: mapped standard cells, flip-flops, cell area (um2, Nangate45) and the
SRAM bits held by the blackboxed sdpram_* macros, read from the netlist
parameters. The cell total is cross-checked between stat.json and the netlist.
"""
import json
import sys
from pathlib import Path

RAM_DEFAULTS = {'DATA_WIDTH': 8, 'ADDRESS_WIDTH': 11}  # sdpram_*.v defaults


def param(cell, name):
    value = cell.get('parameters', {}).get(name)
    if value is None:
        return RAM_DEFAULTS[name]
    return int(value, 2) if set(str(value)) <= {'0', '1'} else int(value)


def design_stat(stat):
    design = stat['design']
    by_type = design.get('num_cells_by_type', {})
    return int(design['num_cells']), float(design.get('area', 0.0)), by_type


def summarise(top_dir):
    stat = json.loads((top_dir / 'stat.json').read_text())
    netlist = json.loads((top_dir / 'netlist.json').read_text())
    cells_total, area, by_type = design_stat(stat)
    top = next(n for n, m in netlist['modules'].items()
               if m.get('attributes', {}).get('top'))
    cells = netlist['modules'][top]['cells'].values()
    rams = [c for c in cells if c['type'].lstrip('\\').startswith('sdpram_')]
    if len(list(netlist['modules'][top]['cells'])) != cells_total:
        raise RuntimeError(f'{top_dir.name}: netlist/stat cell-total mismatch')
    ram_bits = sum(param(c, 'DATA_WIDTH') << param(c, 'ADDRESS_WIDTH') for c in rams)
    flops = sum(n for t, n in by_type.items() if t.lstrip('\\').startswith(('DFF', 'SDFF')))
    return {'cells': cells_total - len(rams), 'flops': flops, 'area': area,
            'rams': len(rams), 'ram_bits': ram_bits}


def main():
    run = Path(sys.argv[1])
    print(f'# Area run `{run.name}`\n')
    print('Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.')
    print('SRAMs are blackboxed macros, reported in bits, not as cells or area.\n')
    print('| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |')
    print('|---|---:|---:|---:|---:|---:|')
    tops = [p for p in run.iterdir() if p.is_dir()]
    for top_dir in sorted(tops, key=lambda p: (p / 'stage.ys').stat().st_mtime):
        if not (top_dir / 'stat.json').exists():
            print(f'| `{top_dir.name}` | FAIL | | | | |')
            continue
        s = summarise(top_dir)
        print(f"| `{top_dir.name}` | {s['cells']} | {s['flops']} | {s['area']:.1f} | "
              f"{s['rams']} | {s['ram_bits']} |")


if __name__ == '__main__':
    main()
