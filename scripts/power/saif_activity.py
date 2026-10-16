#!/usr/bin/env python3
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
"""Switching activity of two gate-level netlists from one Verilator SAIF.

Inputs: the SAIF of a scenario run, the SAIF of the setup-only run (subtracted
net by net: the setup phase is identical in every run), the two netlists, the
liberty, and the window length in bb_clk cycles.

Counting rules
  * A net is counted once, in the module where it is DRIVEN (a cell output, a
    RAM model output, or, in the top module, a primary input). Nets that only
    pass through a hierarchy boundary are not counted twice.
  * Pin-capacitance load of a net = sum of the liberty input-pin capacitances
    of the cells it drives, summed over every module it reaches. Wires,
    clock-tree buffers and parasitics are NOT included: this is a pre-layout
    proxy of switched capacitance, not power.
  * Clock load = the CK pins of flip-flops. Reported apart from the data load.
  * Toggle rate of a net = window toggles / window cycles (bb_clk, 16 MHz).
  * Hotspot = a non-clock net with toggle rate > 0.1.
  * Blocks are attributed from instance paths (see BLOCKS). RAM models are
    blackbox macros in synthesis; their activity is reported as toggles on the
    nets connected to their ports.
"""
import json, math, re, sys
from collections import defaultdict

# ------------------------------------------------------------------ liberty --
def parse_liberty(path):
    txt = open(path).read()
    unit = re.search(r'capacitive_load_unit\s*\(\s*([0-9.]+)\s*,\s*(ff|pf|nf|uf|mf|f)\s*\)\s*;', txt, re.I)
    if not unit: raise ValueError('missing/unsupported liberty capacitive_load_unit')
    scale = float(unit[1]) * {'ff':1., 'pf':1e3, 'nf':1e6, 'uf':1e9, 'mf':1e12, 'f':1e15}[unit[2].lower()]
    if not math.isfinite(scale) or scale <= 0: raise ValueError('invalid capacitance unit')
    cells = {}
    for m in re.finditer(r'\bcell\s*\(\s*"?([\w]+)"?\s*\)\s*\{', txt):
        name, i, depth = m.group(1), m.end(), 1
        j = i
        while depth and j < len(txt):
            c = txt[j]
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            j += 1
        body = txt[i:j]
        pins, is_seq = {}, ('ff (' in body or 'ff(' in body or 'latch' in body)
        for pm in re.finditer(r'\bpin\s*\(\s*"?([\w]+)"?\s*\)\s*\{', body):
            k, d = pm.end(), 1
            e = k
            while d and e < len(body):
                if body[e] == '{': d += 1
                elif body[e] == '}': d -= 1
                e += 1
            pb = body[k:e]
            dm = re.search(r'direction\s*:\s*"?(\w+)"?', pb)
            cm = re.search(r'\bcapacitance\s*:\s*([^;]+);', pb)
            clk = re.search(r'\bclock\s*:\s*"?true"?', pb) is not None
            direction = dm.group(1) if dm else '?'
            if direction == 'input' and cm is None: raise ValueError(f'missing input capacitance: {name}.{pm.group(1)}')
            cap = float(cm.group(1)) * scale if cm else 0.0
            if not math.isfinite(cap) or cap < 0: raise ValueError(f'invalid capacitance: {name}.{pm.group(1)}')
            pins[pm.group(1)] = (direction, cap, clk)
        cells[name] = pins
    if not cells: raise ValueError("empty liberty cell library")
    return cells

# ----------------------------------------------------------------- netlist --
ID = r'(?:\\\S+|[A-Za-z_][\w$]*)'
def norm(tok):
    """'\\foo.bar [3]' -> 'foo.bar[3]';  '_012_' -> '_012_'."""
    tok = tok.strip()
    m = re.match(r'^(\\\S+|[A-Za-z_][\w$]*)\s*(\[\s*\d+\s*\])?$', tok)
    if not m:
        return None
    base = m.group(1).lstrip('\\')
    return base + (m.group(2).replace(' ', '') if m.group(2) else '')

def split_top(s):
    out, depth, cur = [], 0, ''
    for c in s:
        if c in '({': depth += 1
        if c in ')}': depth -= 1
        if c == ',' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += c
    if cur.strip(): out.append(cur)
    return out

def expand(expr, widths):
    """Connection expression -> list of bit names (MSB first); constants -> None."""
    expr = expr.strip()
    if expr.startswith('{') and expr.endswith('}'):
        bits = []
        for part in split_top(expr[1:-1]):
            bits += expand(part, widths)
        return bits
    m = re.match(r"^\d*'s?[bhdo][0-9a-fA-FxXzZ_]+$", expr)
    if m:
        w = int(expr.split("'")[0]) if expr.split("'")[0] else 1
        return [None] * w
    m = re.match(r'^(\\\S+|[A-Za-z_][\w$]*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]$', expr)
    if m:
        base, hi, lo = m.group(1).lstrip('\\'), int(m.group(2)), int(m.group(3))
        step = -1 if hi >= lo else 1
        return [f'{base}[{i}]' for i in range(hi, lo + step, step)]
    n = norm(expr)
    if n is None:
        raise ValueError(f"unsupported mapped-netlist connection: {expr}")
    w = widths.get(n)      # first: an escaped name may hold brackets ('\data_internal[0]', a vector)
    if w is None:
        return [n]
    hi, lo = w
    step = -1 if hi >= lo else 1
    return [f'{n}[{i}]' for i in range(hi, lo + step, step)]

def saif_name(net, widths):
    """Netlist bit -> the name Verilator's SAIF gives it: bits counted from 0 whatever the declared
    LSB ('octet_buf' [31:8]: netlist bit 8 is SAIF bit 0), a [0:0] vector written without an index."""
    m = re.match(r'^(.*)\[(\d+)\]$', net)
    if not m or m.group(1) not in widths:
        return net
    hi, lo = widths[m.group(1)]
    if hi == lo:
        return m.group(1)
    return f'{m.group(1)}[{int(m.group(2)) - min(hi, lo)}]'

def parse_netlist(path):
    txt = open(path).read()
    mods = {}
    for mm in re.finditer(r'^module\s+(\S+?)\s*\((.*?)\);(.*?)^endmodule', txt, re.S | re.M):
        name, body = mm.group(1), mm.group(3)
        widths, ports = {}, {}
        for d in re.finditer(r'^\s*(input|output|inout|wire|reg)\s+(?:signed\s+)?(\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*(' + ID + r')\s*;', body, re.M):
            n = d.group(5).lstrip('\\')
            if d.group(2): widths[n] = (int(d.group(3)), int(d.group(4)))
            if d.group(1) in ('input', 'output', 'inout'): ports[n] = d.group(1)
        insts = []
        for im in re.finditer(r'^\s*(' + ID + r')\s+(?:#\(.*?\)\s*)?(' + ID + r')\s*\((.*?)\);', body, re.M | re.S):
            typ, inst, conns = im.group(1).lstrip('\\'), im.group(2).lstrip('\\'), im.group(3)
            if typ in ('module', 'input', 'output', 'wire', 'reg', 'assign'):
                continue
            pins = {}
            for c in re.finditer(r'\.(\w+)\s*\(', conns):
                k, depth, e = c.end(), 1, c.end()
                while depth and e < len(conns):
                    if conns[e] == '(': depth += 1
                    elif conns[e] == ')': depth -= 1
                    e += 1
                pins[c.group(1)] = conns[k:e-1]
            insts.append((typ, inst, pins))
        assigns = []
        for am in re.finditer(r'^\s*assign\s+(.+?)\s*=\s*(.+?);', body, re.M):
            assigns.append((am.group(1), am.group(2)))
        mods[name] = dict(widths=widths, ports=ports, insts=insts, assigns=assigns)
    return mods

# -------------------------------------------------------------------- SAIF --
def parse_saif(path):
    """{(instance path tuple, net): TC}"""
    tc = {}
    stack = []
    inst_re = re.compile(r'^\s*\(INSTANCE\s+(\S+)')
    net_re = re.compile(r'^\s*\((\S+)\s+\(T0.*\(TC\s+(\d+)\)\)')
    depth_stack = []
    with open(path) as f:
        for line in f:
            m = inst_re.match(line)
            if m:
                stack.append(m.group(1).replace('\\', ''))
                continue
            m = net_re.match(line)
            if m:
                key = (tuple(stack), m.group(1).replace('\\', ''))
                if key in tc: raise ValueError(f'duplicate SAIF net: {key}')
                tc[key] = int(m.group(2))
                continue
            s = line.strip()
            if s == ')' and stack:
                # closes either a NET list or an INSTANCE; NET lists are opened by "(NET"
                if depth_stack and depth_stack[-1] == 'NET':
                    depth_stack.pop()
                else:
                    stack.pop()
            elif s.startswith('(NET'):
                depth_stack.append('NET')
    if not tc: raise ValueError("empty SAIF activity")
    return tc

# ---------------------------------------------------------------- analysis --
# Clock inputs of btle_controller. Their flip-flop CK loads sit inside the
# blocks, so they are recognised by name where they are driven (the top).
CLOCK_PORTS = {'rf_clk', 'bb_clk', 's00_axi_aclk', 'bram_clk_a'}

BLOCKS = [  # (block, substring of the instance path), first match wins
    ('gauss_filter', 'gauss_filter_i'),
    ('btle_tx (other)', 'btle_tx_i'),
    ('btle_rx', 'btle_rx_i'),
    ('btle_ll', 'btle_ll_i'),
    ('auxiliary_daemon', 'auxiliary_daemon_i'),
    ('clock_domain_conversion', 'clock_domain_conversion_iq_i'),
]
def block_of(path):
    p = '/'.join(path)
    for b, key in BLOCKS:
        if key in p:
            return b
    return 'top glue'

def analyse(design_scope, top_module, mods, lib, tc_run, tc_setup, window):
    res = dict(nets=0, toggles=0, clock_toggles=0, clk_cap_tog=0.0, data_cap_tog=0.0,
               hot_nets=0, blocks=defaultdict(lambda: dict(nets=0, toggles=0, data_cap_tog=0.0,
                                                          clk_cap_tog=0.0, hot_nets=0, cells=0)),
               mem_port_toggles=0, mem_instances=0, cells=0, missing=0, top_nets=[], missing_nets=[])
    def walk(module, path):
        m = mods[module]
        widths = m['widths']
        load, clk_load, driven = defaultdict(float), defaultdict(float), set()
        mem_nets = set()
        blk = block_of(path)
        for typ, inst, pins in m['insts']:
            if typ in lib:
                res['cells'] += 1; res['blocks'][blk]['cells'] += 1
                for pin, expr in pins.items():
                    if pin not in lib[typ]: raise ValueError(f'unknown liberty pin {typ}.{pin}')
                    d, cap, isclk = lib[typ][pin]
                    if d not in ('input', 'output', 'inout') or not math.isfinite(cap) or cap < 0:
                        raise ValueError(f'invalid liberty pin {typ}.{pin}')
                    for b in expand(expr, widths):
                        if b is None: continue
                        if d == 'input':
                            if isclk: clk_load[b] += cap
                            else: load[b] += cap
                        elif d == 'output':
                            driven.add(b)
            elif typ in mods:
                walk(typ, path + (inst,))
                for pin, expr in pins.items():      # child outputs drive parent nets
                    if mods[typ]['ports'].get(pin) == 'output':
                        pass                          # counted in the child, at its driver
            else:                                     # Explicit RAM model (blackbox in synthesis)
                if not typ.startswith(('sdpram_', 'sin_table_ram', 'pdu_buffer_ram', 'gauss_table_ram')):
                    raise ValueError(f'unknown mapped cell/module: {typ}')
                res['mem_instances'] += 1
                for pin, expr in pins.items():
                    for b in expand(expr, widths):
                        if b is not None: mem_nets.add(b)
                        if b is not None and pin in ('read_data',): driven.add(b)
        if module == top_module:
            for p, d in m['ports'].items():
                if d == 'input':
                    for b in expand(p, widths): driven.add(b)
        def win(net):
            key = (path, saif_name(net, widths))
            if key not in tc_run or key not in tc_setup:
                res['missing_nets'].append('/'.join(path) + '/' + net)
                return None
            delta = tc_run[key] - tc_setup[key]
            if delta < 0: raise ValueError(f'SAIF counter decreased: {key}')
            return delta
        # switched-capacitance proxy: every net segment with loads in this module
        for net in set(load) | set(clk_load):
            t = win(net)
            if t is None:
                res['missing'] += 1; continue
            res['data_cap_tog'] += t * load.get(net, 0.0)
            res['clk_cap_tog'] += t * clk_load.get(net, 0.0)
            res['blocks'][blk]['data_cap_tog'] += t * load.get(net, 0.0)
            res['blocks'][blk]['clk_cap_tog'] += t * clk_load.get(net, 0.0)
        # toggle counts: nets counted where driven
        for net in driven:
            t = win(net)
            if t is None:
                res['missing'] += 1; continue
            is_clock = ((clk_load.get(net, 0.0) > 0 and load.get(net, 0.0) == 0) or
                        (module == top_module and net.split('[')[0] in CLOCK_PORTS))
            res['nets'] += 1; res['toggles'] += t
            res['blocks'][blk]['nets'] += 1; res['blocks'][blk]['toggles'] += t
            if is_clock:
                res['clock_toggles'] += t
            elif t / window > 0.1:
                res['hot_nets'] += 1; res['blocks'][blk]['hot_nets'] += 1
            if not is_clock:
                res['top_nets'].append((t / window, blk, '/'.join(path) + '/' + net))
        for net in mem_nets:
            t = win(net)
            if t is not None: res['mem_port_toggles'] += t
    walk(top_module, design_scope)
    res['top_nets'] = sorted(res['top_nets'], reverse=True)[:15]
    res['blocks'] = dict(res['blocks'])
    res['missing_nets'] = sorted(set(res['missing_nets']))
    return res

def main():
    (saif_run, saif_setup, ref_netlist, dut_netlist, liberty, window, scenario, out_json) = sys.argv[1:9]
    window = int(window)
    if window <= 0: raise SystemExit("positive activity window required")
    lib = parse_liberty(liberty)
    tc_run, tc_setup = parse_saif(saif_run), parse_saif(saif_setup)
    ref_m, dut_m = parse_netlist(ref_netlist), parse_netlist(dut_netlist)
    out = dict(scenario=scenario, window_cycles=window)
    out['ref'] = analyse(('tb_activity', 'u_ref'), 'btle_controller_ref', ref_m, lib, tc_run, tc_setup, window)
    out['dut'] = analyse(('tb_activity', 'u_dut'), 'btle_controller', dut_m, lib, tc_run, tc_setup, window)
    incomplete = [d for d in ('ref', 'dut') if out[d]['missing_nets'] or out[d]['cells'] <= 0 or out[d]['nets'] <= 0]
    out['status'] = 'INCOMPLETE' if incomplete else 'COMPLETE'
    for d in ('ref', 'dut'):
        if any(not math.isfinite(out[d][k]) or out[d][k] < 0 for k in ('toggles','clock_toggles','data_cap_tog','clk_cap_tog')):
            raise SystemExit('invalid activity totals')
    with open(out_json, 'w') as output: json.dump(out, output, indent=1, default=float, allow_nan=False)
    if incomplete:
        raise SystemExit('incomplete activity evidence: ' + ', '.join(incomplete) + '; see missing_nets in ' + out_json)
    for d in ('ref', 'dut'):
        r = out[d]
        print(f"{scenario} {d}: cells {r['cells']} nets {r['nets']} toggles {r['toggles']} "
              f"({r['toggles']/window:.1f}/cycle) clock_toggles {r['clock_toggles']} hot {r['hot_nets']} "
              f"data_fF_tog {r['data_cap_tog']:.4g} clk_fF_tog {r['clk_cap_tog']:.4g} "
              f"mem_port_toggles {r['mem_port_toggles']} missing {r['missing']}")

if __name__ == '__main__':
    main()
