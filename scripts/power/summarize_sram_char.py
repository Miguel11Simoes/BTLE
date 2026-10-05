"""Summarize run_sram_char.sh: the energies of SRAM macros from their SPICE .lib.

Author: Miguel Simões

Usage: summarize_sram_char.py <results/power/label> <macro ...> [--leakage <leakage.json>]
       -> summary.md on stdout, char.json

Each <macro>_TT_1p0V_25C.lib (or .lib.gz) holds, per clock pin and case, OpenRAM's
measure: the average supply power over one clock cycle (mW, rise and fall: a 1 or
a 0 written or read; their mean is used), with the other port deselected, and
OpenRAM's leakage of the whole array (every port deselected, clock low). The
period of the measurement is read from <macro>.log (openram_char.py) and checked
against the .lib's minimum_period.

OpenRAM's leakage is the supply power of the first 10 ns after a power-up from
0 V (sram_leakage.py): the bitlines and the sense amplifiers' inputs, driven by
nothing in a deselected macro, have not settled, and it comes out above the
power of a whole deselected clock. With --leakage, the leakage is the settled one
of run_sram_leakage.sh (every macro must be in that file), and OpenRAM's figure is
kept beside it. In char.json, per macro:

  access_pJ   the energy of an access, relative to a deselected clock of the same
              port: (P_access - P_deselected) x period. A write turned into a
              deselected clock saves exactly this.
  clock_pJ    the energy of a deselected clock beyond the leakage, every port
              deselected: (P_deselected - leakage) x period. The macro gates its
              array with the chip select, not its clock buffers and input
              flip-flops, which take every clock; run_sram_energy.sh counts it on
              every clock. Relative to OpenRAM's figure (without --leakage) it is
              a signed diagnostic, often below zero.
  energy_pJ   each case relative to the leakage: (P - leakage) x period.
  leakage_mW  the leakage used: the settled one with --leakage, else OpenRAM's
              (leakage_source says which); leakage_openram_mW is OpenRAM's.

The deselected clock of the read/write port is the case "csb0 & web0" (the
write enable high, as in a long idle); "csb0 & !web0", a deselected clock after
a write, is in power_mW.
"""
import gzip
import json
import math
import re
import sys
from pathlib import Path


def read(p):
    return gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text()


def main():
    argv = sys.argv[1:]
    settled, settled_path = {}, None
    if '--leakage' in argv:
        i = argv.index('--leakage')
        if i + 1 >= len(argv):
            raise SystemExit("--leakage needs a file")
        settled_path = argv[i + 1]
        settled = json.loads(Path(settled_path).read_text())
        if not isinstance(settled, dict):
            raise SystemExit(f"{settled_path}: not a leakage file of run_sram_leakage.sh")
        del argv[i:i + 2]
    if not argv:
        raise SystemExit("usage: summarize_sram_char.py <results/power/label> <macro ...> [--leakage <file>]")
    out, macros = Path(argv[0]), argv[1:]
    if not macros or len(macros) != len(set(macros)):
        raise SystemExit("unique nonempty macro list required")
    for name in macros:
        match = re.fullmatch(r"sram_(1rw|1rw1r)_(\d+)x(\d+)", name)
        if not match or int(match[2]) <= 0 or int(match[3]) <= 0:
            raise SystemExit(f"invalid macro name/geometry: {name}")
    data = {}
    for name in macros:
        lib = out / f"{name}_TT_1p0V_25C.lib"
        if not lib.exists():
            lib = out / f"{name}_TT_1p0V_25C.lib.gz"
        logp = out / f"{name}.log"
        if not logp.exists():
            logp = out / f"{name}.log.gz"
        if not lib.exists():
            continue
        text, log = read(lib), read(logp) if logp.exists() else ''
        ports, ws, nw = re.match(r"sram_(1rw|1rw1r)_(\d+)x(\d+)$", name).groups()
        leak = leak_or = float(re.search(r"(?<![A-Za-z_])cell_leakage_power\s*:\s*([0-9.eE+-]+)", text).group(1))
        if settled_path is not None:
            entry = settled.get(name)
            if not isinstance(entry, dict):
                raise SystemExit(f"{name}: not in {settled_path}")
            leak = entry.get("leakage_mW")
            if isinstance(leak, bool) or not isinstance(leak, (int, float)) or not math.isfinite(leak) or leak <= 0:
                raise SystemExit(f"{name}: invalid settled leakage {leak!r} in {settled_path}")
            if not math.isfinite(leak_or) or leak_or < 0:
                raise SystemExit(f"{name}: invalid OpenRAM leakage")
        periods =[float(p) for p in re.findall(r'timing_type\s*:\s*"minimum_period";.*?rise_constraint\(scalar\)\s*\{\s*values\("([0-9.eE+-]+)"\)', text, re.S)]
        measured = [float(p) for p in re.findall(r"CHAR: measuring at ([0-9.eE+-]+) ns", log)]
        if not (periods and measured and abs(periods[0] - measured[-1]) < 1e-6):
            raise SystemExit(f"{name}: period of the .lib {periods[:1]} and of the log {measured[-1:]} do not agree")
        period = measured[-1]
        if not math.isfinite(leak) or leak < 0 or not math.isfinite(period) or period <= 0:
            raise SystemExit(f"{name}: invalid leakage or period")
        if any(not math.isfinite(v) or abs(v-period) >= 1e-6 for v in periods):
            raise SystemExit(f"{name}: inconsistent minimum periods")
        power = {}
        for pin in re.finditer(r"pin\((clk\d)\)\{(.*?)\n    \}", text, re.S):
            for ip in re.finditer(r'internal_power\(\)\{\s*when\s*:\s*"([^"]+)";\s*rise_power\(scalar\)\{\s*values\("([^"]+)"\);\s*\}\s*fall_power\(scalar\)\{\s*values\("([^"]+)"\);', pin.group(2), re.S):
                cases = power.setdefault(pin.group(1), {})
                if ip.group(1) in cases:
                    raise SystemExit(f"{name}: duplicate power case")
                values = [float(ip.group(2)), float(ip.group(3))]
                if any(not math.isfinite(v) or v < 0 for v in values):
                    raise SystemExit(f"{name}: invalid measured power")
                cases[ip.group(1)] = values
        mean = lambda pin, cond: sum(power[pin][cond]) / 2

        def vs_leak(pin, cond):
            return round((mean(pin, cond) - leak) * period, 6)

        def vs_idle(pin, cond, idle):
            return round((mean(pin, cond) - mean(pin, idle)) * period, 6)

        e = {"write": vs_leak("clk0", "!csb0 & !web0"), "read": vs_leak("clk0", "!csb0 & web0"),
             "idle": vs_leak("clk0", "csb0 & web0"), "idle_web_low": vs_leak("clk0", "csb0 & !web0")}
        a = {"write": vs_idle("clk0", "!csb0 & !web0", "csb0 & web0"),
             "read": vs_idle("clk0", "!csb0 & web0", "csb0 & web0")}
        if ports == "1rw1r":
            e.update(read1=vs_leak("clk1", "!csb1"), idle1=vs_leak("clk1", "csb1"))
            a.update(read1=vs_idle("clk1", "!csb1", "csb1"))
        if any(not math.isfinite(v) or v < 0 for v in a.values()) or any(not math.isfinite(v) for v in e.values()):
            raise SystemExit(f"{name}: invalid computed access energy")
        data[name] = dict(ports=ports, words=int(nw), bits=int(ws), period_ns=period, leakage_mW=leak,
                          leakage_openram_mW=leak_or,
                          leakage_source=f"run_sram_leakage.sh ({settled_path})" if settled_path is not None else "OpenRAM",
                          power_mW=power, access_pJ=a, clock_pJ=e["idle"], energy_pJ=e)
    (out / "char.json").write_text(json.dumps(data, indent=1) + "\n")
    print("# SRAM macros characterized with SPICE, FreePDK45\n")
    print("OpenRAM's measures: the average supply power of one clock cycle, at the period shown. The energy")
    print("of an access is relative to a deselected clock of the same port, (P_access - P_deselected) x period;")
    print("a deselected clock costs its own energy beyond the leakage, (P_deselected - leakage) x period: the")
    print("macro gates its array with the chip select, not its clock buffers and input flip-flops.")
    if settled_path is not None:
        print("The leakage is the settled one of run_sram_leakage.sh; OpenRAM's figure, the first 10 ns after a")
        print("power-up from 0 V, is shown beside it.\n")
        print("| Macro | Period (ns) | Leakage (uW) | OpenRAM's leakage (uW) | Write (pJ) | Read (pJ) | Port 1 read (pJ) | Deselected clock (pJ) |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|")
    else:
        print("The leakage is OpenRAM's figure, the first 10 ns after a power-up from 0 V (sram_leakage.py), so the")
        print("last column is a signed diagnostic, not the energy of a deselected clock.\n")
        print("| Macro | Period (ns) | Leakage (uW) | Write (pJ) | Read (pJ) | Port 1 read (pJ) | Deselected clock vs leakage (pJ) |")
        print("|---|---:|---:|---:|---:|---:|---:|")
    for name, d in data.items():
        a, e = d["access_pJ"], d["energy_pJ"]
        r1 = f"{a['read1']:.3f}" if "read1" in a else "-"
        idle = f"{e['idle']:+.3f}" + (f" / {e['idle1']:+.3f}" if "idle1" in e else "")
        lk = f"{1000 * d['leakage_mW']:.2f}" + (f" | {1000 * d['leakage_openram_mW']:.2f}" if settled_path is not None else "")
        print(f"| `{name}` | {d['period_ns']:g} | {lk} | {a['write']:.3f} | {a['read']:.3f} | {r1} | {idle} |")
    missing = [m for m in macros if m not in data]
    if missing:
        print(f"\nNot characterized: {', '.join(missing)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
