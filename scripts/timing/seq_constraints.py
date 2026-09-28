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
import re, sys

def cell_body(txt, name):
    m = re.search(r'\bcell\s*\(\s*"?' + re.escape(name) + r'"?\s*\)\s*\{', txt)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth and i < len(txt):
        if txt[i] == '{': depth += 1
        elif txt[i] == '}': depth -= 1
        i += 1
    return txt[m.end():i]

def blocks(body, kind):
    for m in re.finditer(r'\b' + kind + r'\s*\(([^)]*)\)\s*\{', body):
        i, depth = m.end(), 1
        while depth and i < len(body):
            if body[i] == '{': depth += 1
            elif body[i] == '}': depth -= 1
            i += 1
        yield m.group(1).strip().strip('"'), body[m.end():i]

def max_values(block):
    vals = []
    for v in re.finditer(r'values\s*\((.*?)\)\s*;', block, re.S):
        for num in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', v.group(1)):
            vals.append(float(num))
    return max(vals) if vals else None

def main():
    liberty, cells = sys.argv[1], sys.argv[2:]
    txt = open(liberty).read()
    print(f"{'cell':<12} {'clk->Q (ns)':>12} {'setup (ns)':>12}")
    worst_cq = worst_su = 0.0
    for c in cells:
        body = cell_body(txt, c)
        if body is None:
            print(f"{c:<12} {'not in library':>12}")
            continue
        cq = su = 0.0
        for pin, pb in blocks(body, 'pin'):
            for _, tb in blocks(pb, 'timing'):
                ttype = re.search(r'timing_type\s*:\s*"?(\w+)"?', tb)
                ttype = ttype.group(1) if ttype else 'combinational'
                for tabkind in ('cell_rise', 'cell_fall', 'rise_constraint', 'fall_constraint'):
                    for _, tab in blocks(tb, tabkind):
                        v = max_values(tab)
                        if v is None: continue
                        if ttype in ('setup_rising', 'setup_falling') and 'constraint' in tabkind:
                            su = max(su, v)
                        elif ttype.startswith('rising_edge') or ttype == 'combinational':
                            if tabkind in ('cell_rise', 'cell_fall') and pin in ('Q', 'QN'):
                                cq = max(cq, v)
        print(f"{c:<12} {cq:12.4f} {su:12.4f}")
        worst_cq, worst_su = max(worst_cq, cq), max(worst_su, su)
    print(f"{'WORST':<12} {worst_cq:12.4f} {worst_su:12.4f}")
    print(f"sequential_overhead_ns {worst_cq + worst_su:.4f}")

if __name__ == '__main__':
    main()
