#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Clock-to-Q and setup times of the flip-flops used, from the liberty.

ABC's stime measures only the combinational logic between registers, so the
period also needs the launch (clock-to-Q) and capture (setup) times:
    T >= t_CQ + t_comb + t_setup
For each flip-flop type this prints the WORST value in the liberty tables
(over every input slew and output load in the characterised range), which is
pessimistic but safe.

Usage: seq_constraints.py <liberty> <cell> [cell ...]
"""
import math, re, sys

def cell_body(txt, name):
    m = re.search(r'\bcell\s*\(\s*"?' + re.escape(name) + r'"?\s*\)\s*\{', txt)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth and i < len(txt):
        if txt[i] == '{': depth += 1
        elif txt[i] == '}': depth -= 1
        i += 1
    if depth: raise ValueError("unclosed liberty cell")
    return txt[m.end():i]

def blocks(body, kind):
    for m in re.finditer(r'\b' + kind + r'\s*\(([^)]*)\)\s*\{', body):
        i, depth = m.end(), 1
        while depth and i < len(body):
            if body[i] == '{': depth += 1
            elif body[i] == '}': depth -= 1
            i += 1
        if depth: raise ValueError("unclosed liberty block")
        yield m.group(1).strip().strip('"'), body[m.end():i]

def max_values(block):
    vals = []
    for v in re.finditer(r'values\s*\((.*?)\)\s*;', block, re.S):
        raw = v.group(1).replace('"', '').replace('\\', '')
        for token in re.split(r'[,\s]+', raw.strip()):
            if not token: continue
            value = float(token)
            if not math.isfinite(value): raise ValueError('nonfinite timing table value')
            vals.append(value)
    return max(vals) if vals else None

def main():
    liberty, cells = sys.argv[1], sys.argv[2:]
    if not cells or len(cells) != len(set(cells)):
        raise SystemExit('nonempty unique sequential-cell list required')
    txt = open(liberty).read()
    unit = re.search(r'time_unit\s*:\s*"([0-9.]+)\s*(s|ms|us|ns|ps|fs)"\s*;', txt)
    if not unit: raise SystemExit('missing/unsupported liberty time_unit')
    scale = float(unit[1]) * {'s':1e9,'ms':1e6,'us':1e3,'ns':1.,'ps':1e-3,'fs':1e-6}[unit[2]]
    if not math.isfinite(scale) or scale <= 0: raise SystemExit('invalid liberty time unit')
    print(f"{'cell':<12} {'clk->Q (ns)':>12} {'setup (ns)':>12}")
    worst_cq = worst_su = 0.0
    for c in cells:
        body = cell_body(txt, c)
        if body is None:
            raise SystemExit(f"{c}: sequential cell not in library")
        cq = su = 0.0
        found_cq = found_su = False
        for pin, pb in blocks(body, 'pin'):
            for _, tb in blocks(pb, 'timing'):
                ttype = re.search(r'timing_type\s*:\s*"?(\w+)"?', tb)
                ttype = ttype.group(1) if ttype else 'combinational'
                for tabkind in ('cell_rise', 'cell_fall', 'rise_constraint', 'fall_constraint'):
                    for _, tab in blocks(tb, tabkind):
                        v = max_values(tab)
                        if v is None: continue
                        if ttype in ('setup_rising', 'setup_falling') and 'constraint' in tabkind:
                            su = max(su, v * scale)
                            found_su = True
                        elif ttype in ('rising_edge', 'falling_edge', 'combinational'):
                            if tabkind in ('cell_rise', 'cell_fall') and pin in ('Q', 'QN'):
                                cq = max(cq, v * scale)
                                found_cq = True
        if not found_cq or not found_su:
            raise SystemExit(f'{c}: missing clock-to-Q or setup table')
        if not math.isfinite(cq + su): raise SystemExit(f'{c}: nonfinite timing result')
        print(f"{c:<12} {cq:12.4f} {su:12.4f}")
        worst_cq, worst_su = max(worst_cq, cq), max(worst_su, su)
    print(f"{'WORST':<12} {worst_cq:12.4f} {worst_su:12.4f}")
    print(f"sequential_overhead_ns {worst_cq + worst_su:.4f}")

if __name__ == '__main__':
    main()
