"""The static power of a deselected OpenRAM macro, with ngspice, once the macro has settled.

Author: Miguel Simões

OpenRAM measures the leakage of a macro (the .lib's cell_leakage_power, and the
leakage of run_sram_char.sh) in a transient that, with ngspice, starts every node
at 0 V (UIC: no operating point), with every port deselected and the clock low,
and averages the supply power from 5 to 10 ns. A deselected macro drives neither
its bitlines, which are precharged only for an access, nor the sense amplifiers'
inputs, which follow the selected column of each bit through the column
multiplexer. Ten nanoseconds after the power-up they still sit between the rails,
and the sense amplifiers' output stages draw a crossover current; they settle
within a few microseconds, at the balance of their leakage currents. OpenRAM's
figure is that of the first 10 ns, and depends on how the simulation starts.

Where they settle depends on the data: a selected column whose cells hold one
value pulls its bitlines to the rails, one that holds both settles between them,
and the sense amplifier of that bit then keeps drawing its crossover current. The
static power of a deselected macro is therefore a function of its contents and
of the address on its input.

This measure is OpenRAM's leakage run until the macro has settled:
- OpenRAM's stimulus (chip selects and write enable 1, its output load) and
  options (UIC, gear, RELTOL 1e-3); the address and data inputs 0, or the given
  ones;
- one clock pulse at 1-2 ns, every port deselected, so that every flip-flop holds
  its input, as after any clock; then the clock stays low;
- the data: by default every bitcell holds 0 (an .ic in the bitcell subcircuits);
  with --data, every cell of the data array holds its bit of the given words
  (hierarchical .ic; the array's place and geometry are read from the netlist),
  and the cells the file leaves unknown ("xx") hold 0 or seeded random bits;
- 5 us instead of 10 ns, with a step of at most 1 ns (the macro does not switch
  after the pulse; OpenRAM's 10 ps would take 500 000 steps). The result is the
  average supply power over 4.5-5 us; the windows 3-4 us and 4-4.5 us must agree
  with it within 2 %, or the measure fails. The voltages of the selected column's
  bitline and of the sense amplifier's input of every bit, at 10 ns, 1 us and
  5 us, show where they settled (OpenRAM's node names).

Usage: sram_leakage.py <OpenRAM netlist .sp> <macro> <work dir> <ngspice> <models dir>
         [--data <file of words, hex or xx> --addr A --din D --fill zero|seed:N]
Prints one JSON line: the macro, the static power (mW, 4.5-5 us), every window (mW), the
largest relative difference of the checked windows, the probed voltages (V) and, with
--data, the ones in the selected column of each bit. Writes in the work dir
leakage_stim.sp, leakage.lis (ngspice's listing) and leakage_measures.txt.
"""
import argparse
import json
import random
import re
import subprocess
from pathlib import Path

LOAD = '0.2091f'      # OpenRAM's output load in its own leakage run of these macros
END_NS = 5000
WINDOWS = (('leak_5_10ns', 5, 10), ('leak_0p5_1us', 500, 1000), ('leak_1_2us', 1000, 2000),
           ('leak_2_3us', 2000, 3000), ('leak_3_4us', 3000, 4000), ('leak_4_4p5us', 4000, 4500),
           ('leak_4p5_5us', 4500, 5000))
CHECKED = ('leak_3_4us', 'leak_4_4p5us')
PROBE_NS = (10, 1000, 5000)


def subckts(net):
    """name -> (ports, instance lines with their continuations joined), from the netlist"""
    out, name, ports, body, header, inst = {}, None, [], [], False, False
    for line in net.split('\n'):
        m = re.match(r'\.SUBCKT\s+(\S+)(.*)', line, re.I)
        if m:
            name, ports, body, header, inst = m.group(1), m.group(2).split(), [], True, False
            out[name] = (ports, body)
            continue
        if name is None:
            continue
        if re.match(r'\.ENDS', line, re.I):
            name = None
        elif line.startswith('+'):
            if header:
                ports.extend(line[1:].split())
            elif inst:
                body[-1] += ' ' + line[1:]
        else:
            header = False
            inst = line[:1] in 'Xx'
            if inst:
                body.append(line)
    return out


def path_to(sub, top, target):
    """instance path (list of instance names) from top to the first instance of subckt target"""
    for inst in sub[top][1]:
        t = inst.split()
        if t[-1] == target:
            return [t[0]]
        if t[-1] in sub:
            p = path_to(sub, t[-1], target)
            if p:
                return [t[0]] + p
    return None


def with_cells_at_zero(net):
    """.ic Q=0, Q_bar=1 just before .ENDS of every bitcell subcircuit that holds a state"""
    out, name, n = [], None, 0
    for line in net.split('\n'):
        m = re.match(r'\.SUBCKT\s+(\S+)', line, re.I)
        if m:
            name = m.group(1)
        if name and re.match(r'\.ENDS', line, re.I):
            if re.match(r'(dummy_)?cell_', name, re.I):
                out.append('.ic v(Q)=0 v(Q_bar)=1')
                n += 1
            name = None
        out.append(line)
    return '\n'.join(out), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('netlist'); ap.add_argument('macro'); ap.add_argument('work'); ap.add_argument('ngspice')
    ap.add_argument('models')
    ap.add_argument('--data'); ap.add_argument('--addr', type=int, default=0); ap.add_argument('--din', type=int, default=0)
    ap.add_argument('--fill', default='zero')
    a = ap.parse_args()
    macro, work = a.macro, Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    net = Path(a.netlist).read_text()
    sub = subckts(net)
    if macro not in sub or sub[macro][0][-2:] != ['vdd', 'gnd']:
        raise SystemExit(f'{macro}: top-level subcircuit not found in {a.netlist}')
    pins = sub[macro][0]
    node = {p: re.sub(r'\[(\d+)\]', r'_\1', p) for p in pins}
    bits = len([p for p in pins if p.lower().startswith('dout0')])
    words = 2 ** len([p for p in pins if p.lower().startswith('addr0')])
    mux = len([p for p in sub[f'{macro}_column_mux_array'][0] if p.startswith('sel_')]) \
        if f'{macro}_column_mux_array' in sub else 1
    bank = path_to(sub, macro, f'{macro}_bank')
    array = path_to(sub, macro, f'{macro}_bitcell_array')
    if not bank or not array:
        raise SystemExit(f'{macro}: bank or bitcell array not found')
    lc = lambda p: '.'.join(x.lower() for x in [f'x{macro}'] + p)
    extra, info = [], {}
    if a.data:
        toks = Path(a.data).read_text().split()
        if len(toks) != words:
            raise SystemExit(f'{a.data}: {len(toks)} words, the macro has {words}')
        rng = random.Random(int(a.fill.split(':')[1])) if a.fill.startswith('seed:') else None
        if not rng and a.fill != 'zero':
            raise SystemExit('--fill zero or seed:N')
        vals = [int(t, 16) if t.lower() != 'xx' else (rng.getrandbits(bits) if rng else 0) for t in toks]
        for w, v in enumerate(vals):
            for b in range(bits):
                c = lc(array + [f'xbit_r{w // mux}_c{mux * b + w % mux}'])
                extra.append(f'.ic v({c}.q)={(v >> b) & 1} v({c}.q_bar)={1 - ((v >> b) & 1)}')
        m = a.addr % mux
        info = dict(column=m, ones=[sum((vals[w] >> b) & 1 for w in range(m, words, mux)) for b in range(bits)],
                    cells=words // mux, unknown=sum(t.lower() == 'xx' for t in toks), fill=a.fill)
        text = net
    else:
        text, n = with_cells_at_zero(net)
        if not n:
            raise SystemExit(f'{macro}: no bitcell subcircuit')
    (work / 'netlist.sp').write_text(text)

    lines = [f'* static power of {macro} deselected, settled (sram_leakage.py)',
             f'.include "{a.models}/PMOS_VTG.inc"', f'.include "{a.models}/NMOS_VTG.inc"',
             f'.include "{work}/netlist.sp"', 'Vvdd vdd 0 1.0',
             f'X{macro} ' + ' '.join(node[p] for p in pins) + f' {macro}']
    for p in pins[:-2]:
        n, pl = node[p], p.lower()
        k = re.search(r'\[(\d+)\]', p)
        k = int(k.group(1)) if k else 0
        if pl.startswith('dout'):
            lines.append(f'CL{n} {n} 0 {LOAD}')
        elif pl.startswith('din0'):
            lines.append(f'V{n} {n} 0 DC {(a.din >> k) & 1}')
        elif pl.startswith('addr0'):
            lines.append(f'V{n} {n} 0 DC {(a.addr >> k) & 1}')
        elif pl.startswith(('din', 'addr')):
            lines.append(f'V{n} {n} 0 DC 0')
        elif pl.startswith(('csb', 'web')):
            lines.append(f'V{n} {n} 0 DC 1.0')
        elif pl.startswith('clk'):
            lines.append(f'V{n} {n} 0 PWL(0 0 1n 0 1.05n 1.0 2n 1.0 2.05n 0)')
        else:
            raise SystemExit(f'{macro}: unknown pin {p}')
    lines += extra
    for name, x, y in WINDOWS:
        lines.append(f".meas tran {name} avg par('(-1*v(vdd)*I(vvdd))') from={x}n to={y}n")
    m = a.addr % mux
    for b in range(bits):
        for t in PROBE_NS:
            lines.append(f'.meas tran v_bl{b}_{t}ns find v({lc(bank)}.bl_0_{mux * b + m}) at={t}n')
            lines.append(f'.meas tran v_sa{b}_{t}ns find v({lc(bank)}.xport_data0.xsense_amp_array0.xsa_d{b}.dint) at={t}n')
    lines += ['.TEMP 25', f'.TRAN 10p {END_NS}n 0n 1n UIC', '.OPTIONS POST=1 RELTOL=0.001 PROBE method=gear ACCT',
              '.end', '']
    (work / 'leakage_stim.sp').write_text('\n'.join(lines))
    (work / '.spiceinit').write_text('set num_threads=2\nset ngbehavior=hsa\nset ng_nomodcheck\n')

    lis = work / 'leakage.lis'
    subprocess.run([a.ngspice, '-b', '-o', str(lis), str(work / 'leakage_stim.sp')], cwd=work, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    text = lis.read_text(errors='replace')
    keep = re.compile(r'^(leak_|v_|\s*(Warning|Error|Note)|Total |Transient |Accepted |Rejected |Circuit Equations)',
                      re.I)
    (work / 'leakage_measures.txt').write_text(''.join(l for l in text.splitlines(True) if keep.match(l)))

    def value(name):
        mm = re.search(r'^' + name + r'\s*=\s*([0-9.eE+-]+)', text, re.M | re.I)
        return float(mm.group(1)) if mm else None

    res = {}
    for name, _, _ in WINDOWS:
        x = value(name)
        if x is None:
            raise SystemExit(f'{macro}: no measure {name} in {lis}')
        res[name] = 1e3 * x   # W -> mW
    probes = {f'{kind}{b}_{t}ns': value(f'v_{kind}{b}_{t}ns') for kind in ('bl', 'sa') for b in range(bits)
              for t in PROBE_NS}
    p = res['leak_4p5_5us']
    spread = max(abs(res[k] / p - 1) for k in CHECKED)
    print(json.dumps(dict(macro=macro, leakage_mW=p, windows_mW=res, spread=spread, probes_V=probes,
                          addr=a.addr, din=a.din, data=a.data and Path(a.data).name, **info)))
    if spread > 0.02:
        raise SystemExit(f'{macro}: the supply has not settled (windows {res})')


if __name__ == '__main__':
    main()
