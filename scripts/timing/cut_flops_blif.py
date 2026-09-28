#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Turn a mapped BLIF into the register-to-register combinational network for ABC.

ABC's timing engine (stime) skips sequential cells, so every flip-flop is
removed and replaced by the boundary it represents:
  * its Q/QN outputs become primary inputs  (launch points, after clock-to-Q)
  * its D input becomes a primary output    (capture points, before setup)
Asynchronous set/reset pins are dropped: they are static in operation, and
recovery/removal is not checked here. Macros with no library timing (the RAM
models, and Yosys $print cells) are cut the same way: outputs become primary
inputs, inputs become primary outputs.

Yosys writes library cells as .subckt while ABC wants .gate, wraps long lines
with a trailing backslash, and uses net names with characters ABC's BLIF
reader cannot handle ($ \\ [ ] : .). Lines are joined, cells renamed and every
net renamed n<number>; the mapping is written out so the reported critical
path can be translated back.

Usage: cut_flops_blif.py <in.blif> <out.blif> <report.txt> <names.map> <liberty>
"""
import re, sys

SEQ = re.compile(r'^(SDFF|DFF|TLAT|DLH|DLL)')
OUT_PINS = ('Q', 'QN')
CLK_RST_PINS = ('CK', 'CLK', 'RN', 'SN', 'R', 'S', 'SE', 'SI', 'GN', 'G')
MACRO_OUT = ('read_data', 'rddata', 'dout', 'data_out')

src, dst, rep, mapfile, liberty = sys.argv[1:6]
LIB_TXT = open(liberty).read()
LIB_CELLS = set(re.findall(r'^\s*cell\s*\(\s*"?(\w+)"?\s*\)', LIB_TXT, re.M))

def cell_output_pins(txt):
    """{cell: {output pin names}} from the liberty."""
    out = {}
    for m in re.finditer(r'\bcell\s*\(\s*"?(\w+)"?\s*\)\s*\{', txt):
        name, i, depth = m.group(1), m.end(), 1
        while depth and i < len(txt):
            if txt[i] == '{': depth += 1
            elif txt[i] == '}': depth -= 1
            i += 1
        body = txt[m.end():i]
        pins = set()
        for pm in re.finditer(r'\bpin\s*\(\s*"?(\w+)"?\s*\)\s*\{', body):
            j, d = pm.end(), 1
            while d and j < len(body):
                if body[j] == '{': d += 1
                elif body[j] == '}': d -= 1
                j += 1
            if re.search(r'direction\s*:\s*"?output"?', body[pm.end():j]):
                pins.add(pm.group(1))
        out[name] = pins
    return out
OUT_OF = cell_output_pins(LIB_TXT)

# join continuation lines, then split into statements
text = open(src).read().replace('\\\n', ' ')
lines = [l.rstrip() for l in text.split('\n')]

names, order = {}, []
def nm(orig):
    if orig not in names:
        names[orig] = f'n{len(names)}'
        order.append(orig)
    return names[orig]

gates, luts, launch, capture, driven = [], [], [], [], set()
alias, const_nets, inverters, raw_gates = {}, [], [], []
cap_label = {}
inputs, outputs, n_seq, n_macro, kinds = [], [], 0, 0, {}
i = 0
while i < len(lines):
    ln = lines[i]; i += 1
    if not ln or ln.startswith('#') or ln.startswith('.model') or ln.startswith('.end'):
        continue
    m = re.match(r'^\.(inputs|outputs)\s+(.*)$', ln)
    if m:
        (inputs if m.group(1) == 'inputs' else outputs).extend(m.group(2).split())
        continue
    m = re.match(r'^\.names\s+(.*)$', ln)
    if m:
        # ABC rejects .names nodes in a mapped network, so they are removed:
        # an alias (b = a) becomes a net rename, an inversion becomes INV_X1,
        # and a constant becomes a primary input (constant in the real design,
        # so any path from it is false).
        nets = m.group(1).split()
        cover = []
        while i < len(lines) and re.match(r'^[01\- ]+$', lines[i]) and lines[i].strip():
            cover.append(lines[i].strip()); i += 1
        # an alias or a constant leaves no driver behind, so it does not count
        # as one: only the inverter does (added to `driven` below)
        if len(nets) == 1:
            const_nets.append(nets[0])
        elif len(nets) == 2 and cover == ['1 1']:
            alias[nets[1]] = nets[0]
        elif len(nets) == 2 and cover == ['0 1']:
            inverters.append((nets[0], nets[1]))
        else:
            sys.exit(f'unsupported .names with {len(nets)} nets and cover {cover}')
        continue
    m = re.match(r'^\.(subckt|gate)\s+(\S+)\s+(.*)$', ln)
    if not m:
        continue
    cell, conns = m.group(2), m.group(3).split()
    pins = dict(c.split('=', 1) for c in conns if '=' in c)
    if cell not in LIB_CELLS and not SEQ.match(cell):        # macro: cut
        n_macro += 1
        kinds[cell + ' (macro)'] = kinds.get(cell + ' (macro)', 0) + 1
        for p, net in pins.items():
            if any(k in p for k in MACRO_OUT):
                launch.append(net)
            elif p not in CLK_RST_PINS and p.lower() not in ('clk', 'clkb', 'rst', 'rstb', 'en', 'trg'):
                capture.append(net)
    elif SEQ.match(cell):                                    # flip-flop: cut
        n_seq += 1
        kinds[cell] = kinds.get(cell, 0) + 1
        q = pins.get('Q') or pins.get('QN')
        for p, net in pins.items():
            if p in OUT_PINS:
                launch.append(net)
            elif p not in CLK_RST_PINS:
                capture.append(net)
                if q:                  # name the endpoint after its register
                    cap_label[net] = q
    else:
        raw_gates.append((cell, pins))
        for p, net in pins.items():
            if p in OUT_OF.get(cell, ()):
                driven.add(net)

def resolve(net):
    seen = set()
    while net in alias and net not in seen:
        seen.add(net); net = alias[net]
    return net

used = set()
for cell, pins in raw_gates:
    gates.append('.gate ' + cell + ' ' + ' '.join(f'{p}={nm(resolve(n))}' for p, n in pins.items()))
    used |= {resolve(n) for p, n in pins.items() if p not in OUT_OF.get(cell, ())}
for a, b in inverters:
    gates.append(f'.gate INV_X1 A={nm(resolve(a))} ZN={nm(resolve(b))}')
    used.add(resolve(a)); driven.add(b)
launch = [resolve(n) for n in launch]
capture = [resolve(n) for n in capture]
inputs = [resolve(n) for n in inputs] + [resolve(n) for n in const_nets]
outputs = [resolve(n) for n in outputs]
driven = {resolve(n) for n in driven} - {resolve(n) for n in const_nets}

# A cut flip-flop output that some other cell or alias also drives (Yosys can
# alias nets) must NOT become a primary input: that would be a second driver.
launch = [n for n in dict.fromkeys(launch) if n not in driven]
capture = [c for c in dict.fromkeys(capture) if c not in set(launch)]
# Nets that nothing drives (the design has some: undriven register bits, issue
# U8) become primary inputs. ABC would otherwise tie them to constant 0 and
# delete the logic behind them, hiding paths.
floating = [n for n in sorted(used - driven - set(inputs) - set(launch))]
ins_orig = list(dict.fromkeys(inputs + launch + floating))
outs_orig = [x for x in dict.fromkeys([o for o in outputs if o not in set(launch)] + capture)
             if x in driven or x in set(ins_orig)]
ins, outs = [nm(x) for x in ins_orig], [nm(x) for x in outs_orig]
body = ['.model cut', '.inputs ' + ' '.join(ins), '.outputs ' + ' '.join(outs)] + luts + gates + ['.end', '']
open(dst, 'w').write('\n'.join(body))
open(mapfile, 'w').write(''.join(f'{names[o]} {o}\n' for o in order))
# ABC's "topo" renames the ports piN/poN by position, so the reported start and
# end points can only be read back through this list. A capture point is named
# after the register it feeds, which says more than the D net does.
with open(mapfile + '.io', 'w') as f:
    for k, x in enumerate(ins_orig):
        f.write(f'pi{k} {x}\n')
    for k, x in enumerate(outs_orig):
        f.write(f'po{k} {cap_label.get(x, x)}\n')
open(rep, 'w').write(
    f"sequential cells cut: {n_seq}\nmacros cut (no library timing): {n_macro}\n" +
    ''.join(f"  {k}: {v}\n" for k, v in sorted(kinds.items())) +
    f"combinational gates: {len(gates)} (of which {len(inverters)} from inverting aliases)\n"
    f"aliases resolved: {len(alias)}\nconstant nets as inputs: {len(const_nets)}\n"
    f"launch points (flop/macro outputs as inputs): {len(launch)}\n"
    f"capture points (flop/macro inputs as outputs): {len(capture)}\n"
    f"undriven nets as inputs: {len(floating)}\n" +
    ''.join(f"  {n}\n" for n in floating))
print(f"cut {n_seq} flops, {n_macro} macros; {len(gates)} gates; "
      f"{len(launch)} launch, {len(capture)} capture, {len(floating)} undriven")
