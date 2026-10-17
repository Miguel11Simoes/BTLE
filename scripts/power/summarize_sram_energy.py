"""Summarize run_sram_energy.sh: SRAM accesses and energy of the transmitter.

Author: Miguel Simões

Usage: summarize_sram_energy.py <results/power/label> <char.json> <window cycles> <name ...>

For each configuration <name>, <label>/<name>/counts_<scenario>.txt holds the
SRAMCOUNT lines of one simulation (sram_count_models.v), u_ref (upstream) and
u_dut (the configuration) side by side. The window's counts are those of the
scenario minus those of the setup-only run. Dynamic energy of a memory in the
window, with the energies of its macro (summarize_sram_char.py, char.json):

  every clock:                                 clocks x clock (a deselected clock
                                               beyond the leakage: the macro's
                                               clock buffers and input flip-flops,
                                               which take every clock)
  1RW macro (pdu_buffer_ram, sin_table_ram):   + writes x write + reads x read
  1RW1R macro (sdpram_one_clk, sdpram_two_clk: port 0 writes, port 1 reads):
                                               + writes x write + reads x port 1 read
                                               (OpenRAM measures each port with
                                               the other one deselected; a clock
                                               that uses both is their sum)
  (write, read: each relative to a deselected clock of the same port). The clock
  energy must be the one against the settled leakage (summarize_sram_char.py
  --leakage): a negative one is rejected. Plus char.json's leakage x the window's
  time (16 MHz bb_clk), for every memory, shown apart: it does not depend on the
  clocks or the accesses.

A memory whose macro is not in char.json is shown with its counts and no energy,
and the totals that would need it are marked incomplete; the command fails.

Prints summary.md; writes data.json next to the counts. Checks, which make the
exit status 1 when they fail: upstream's counts are the same in every
configuration's runs; the memories outside the transmitter count the same in
u_ref and u_dut (the same RTL and stimulus); the "master" configuration counts
the same as upstream everywhere; every TX memory clock counts the window.
Every simulation must count a VCO memory and a packet buffer on each side, except the
configurations named in NO_VCO_MEMORY (run_sram_energy.sh: a vco.v that instantiates no
memory, the fixed tables of ble-tx-rom, ble-tx-cordic and ble-tx-min), whose dut must count none.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

SCENARIOS = ["rx", "tx", "mixed", "idle", "idle0"]
BB_CLK_MHZ = 16.0
LINE = re.compile(r"^SRAMCOUNT (\S+) (\w+) (\d+)x(\d+) clocks (\d+) writes (\d+) reads (\d+) both (\d+)(?: read_clocks (\d+))?\s*$")
ONE_PORT = {"pdu_buffer_ram", "sin_table_ram"}


def read_counts(path, dut_vco=True):
    """dut_vco=False: the configuration's vco.v instantiates no memory (ble-tx-rom, ble-tx-cordic, ble-tx-min:
    the tables are fixed); its dut must then count no VCO memory at all."""
    counts = {}
    for line in Path(path).read_text().splitlines():
        m = LINE.match(line)
        if not m:
            raise SystemExit(f"{path}: not a SRAMCOUNT line: {line!r}")
        inst, model, words, bits, clocks, writes, reads, both, read_clocks = m.groups()
        if inst in counts:
            raise SystemExit(f"{path}: duplicate memory {inst}")
        if model not in ONE_PORT | {"sdpram_one_clk", "sdpram_two_clk"}:
            raise SystemExit(f"{path}: unknown memory model {model}")
        if int(words) <= 0 or int(bits) <= 0:
            raise SystemExit(f"{path}: invalid memory geometry")
        counts[inst] = dict(model=model, words=int(words), bits=int(bits), clocks=int(clocks), writes=int(writes),
                            reads=int(reads), both=int(both),
                            read_clocks=int(read_clocks) if read_clocks is not None else int(clocks))
    if not counts:
        raise SystemExit(f"{path}: empty SRAM counts")
    for which in ("ref", "dut"):
        paths=[side(i)[1] for i in counts if side(i)[0] == which]
        has_vco = any(".vco_i." in "."+i for i in paths)
        if which == "dut" and not dut_vco:
            if has_vco:
                raise SystemExit(f"{path}: dut VCO memory counted, but the configuration's vco.v instantiates none")
        elif not has_vco:
            raise SystemExit(f"{path}: missing {which} VCO memory counts")
        if not any("btle_tx_sdpram_two_clk_i" in i or "btle_tx_pdu_buffer_i" in i for i in paths):
            raise SystemExit(f"{path}: missing {which} packet buffer counts")
    return counts


def window_counts(scenario, setup):
    out = {}
    if scenario.keys() != setup.keys():
        raise SystemExit("memory inventory differs between setup and scenario")
    for inst, c in scenario.items():
        s = setup.get(inst)
        if s is None:
            raise SystemExit(f"{inst}: not in the setup run")
        out[inst] = dict(c, **{k: c[k] - s[k] for k in ("clocks", "writes", "reads", "both", "read_clocks")})
        if any(c[k] != s[k] for k in ("model", "words", "bits")):
            raise SystemExit(f"{inst}: memory geometry/model changed")
        w=out[inst]
        if any(w[k] < 0 for k in ("clocks", "writes", "reads", "both", "read_clocks")):
            raise SystemExit(f"{inst}: counters decreased after setup")
        if w["writes"] > w["clocks"] or w["reads"] > w["read_clocks"] or w["both"] > min(w["writes"], w["reads"]):
            raise SystemExit(f"{inst}: impossible access counts")
        if w["model"] in ONE_PORT and (w["both"] or w["writes"]+w["reads"] > w["clocks"]):
            raise SystemExit(f"{inst}: impossible one-port accesses")
    return out


def side(inst):  # ('ref' | 'dut', the path below the controller)
    m = re.match(r"^tb_activity\.u_(ref|dut)\.(.*)$", inst)
    if not m:
        raise SystemExit(f"{inst}: neither u_ref nor u_dut")
    return m.group(1), m.group(2)


def role(path):
    if "vco_i." in path:
        return "VCO " + ("cos table" if "cos_table" in path else "sin table" if "sin_table_sdpram" in path
                         else "quarter sine table")
    return "packet buffer" if ".btle_tx_i." in "." + path else path


def macro_of(c):
    kind = "1rw" if c["model"] in ONE_PORT else "1rw1r"
    return f"sram_{kind}_{c['bits']}x{c['words']}"


def energy_pj(c, ch):
    """(clock, access) energies of the window (pJ), and the deselected clocks of a one-port memory.
    Accesses are relative to the deselected clock; the clock energy is relative to the settled leakage."""
    a = ch["access_pJ"]
    required = ("write", "read") if c["model"] in ONE_PORT else ("write", "read1")
    for key, value in ([("leakage_mW", ch["leakage_mW"]), ("period_ns", ch["period_ns"]), ("clock_pJ", ch.get("clock_pJ"))]
                       + [(k, a[k]) for k in required]):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise SystemExit(f"invalid characterization value {key}={value}")
    if ch["period_ns"] <= 0 or ch["words"] != c["words"] or ch["bits"] != c["bits"]:
        raise SystemExit("characterization period/geometry mismatch")
    if ch["ports"] != ("1rw" if c["model"] in ONE_PORT else "1rw1r"):
        raise SystemExit("characterization port mismatch")
    clock = c["clocks"] * ch["clock_pJ"]
    if c["model"] in ONE_PORT:
        return clock, c["writes"] * a["write"] + c["reads"] * a["read"], c["clocks"] - c["writes"] - c["reads"]
    return clock, c["writes"] * a["write"] + c["reads"] * a["read1"], None


def fmt(x, digits=2):
    return "—" if x is None else f"{x:.{digits}f}"


def main():
    out, char_path, window, names = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    if window <= 0 or not names or len(names) != len(set(names)):
        raise SystemExit("positive window and unique nonempty configuration list required")
    char = json.loads(char_path.read_text())
    seconds = window / (BB_CLK_MHZ * 1e6)
    problems = []
    runs = {}  # name -> scenario -> window counts
    no_vco = set(os.environ.get("NO_VCO_MEMORY", "").split())  # set by run_sram_energy.sh from each dut's vco.v
    if "master" in no_vco:
        raise SystemExit("master (upstream) has VCO memories")
    for n in names:
        setup = read_counts(out / n / "counts_setup.txt", n not in no_vco)
        runs[n] = {s: window_counts(read_counts(out / n / f"counts_{s}.txt", n not in no_vco), setup) for s in SCENARIOS}

    # checks
    first = names[0]
    for n in names:
        for s in SCENARIOS:
            ref = {i: c for i, c in runs[n][s].items() if side(i)[0] == "ref"}
            ref0 = {i: c for i, c in runs[first][s].items() if side(i)[0] == "ref"}
            if ref != ref0:
                problems.append(f"{n} {s}: upstream's counts differ from those of the {first} runs")
            by_path = {}
            for i, c in runs[n][s].items():
                by_path.setdefault(side(i)[1], {})[side(i)[0]] = c
            for path, sides in by_path.items():
                tx = ".btle_tx_i." in "." + path
                if (not tx or n == "master") and sides.get("ref") != sides.get("dut"):
                    problems.append(f"{n} {s}: {path} counts differently in u_ref and u_dut")
                for d, c in sides.items():
                    if tx and (c["clocks"] != window or c["read_clocks"] != window):
                        problems.append(f"{n} {s}: {d} {path}: {c['clocks']}/{c['read_clocks']} clocks, not {window}")
                    if tx and c["both"] and c["model"] in ONE_PORT:
                        problems.append(f"{n} {s}: {d} {path}: {c['both']} clocks write and read a one-port memory")

    # energies: master = upstream (u_ref), every other name its u_dut
    configs = [("master", first, "ref")] + [(n, n, "dut") for n in names if n != "master"]
    table = {}
    missing = set()
    for label, run, which in configs:
        for s in SCENARIOS:
            rows = []
            for inst, c in sorted(runs[run][s].items()):
                d, path = side(inst)
                if d != which or ".btle_tx_i." not in "." + path:
                    continue
                m = macro_of(c)
                if m in char:
                    ec, ea, idle = energy_pj(c, char[m])
                    clk, acc = ec * 1e-12 / seconds * 1e6, ea * 1e-12 / seconds * 1e6
                    e, dyn, leak = ec + ea, clk + acc, 1000 * char[m]["leakage_mW"]
                    if any(not math.isfinite(v) or v < 0 for v in (e, clk, acc, dyn, leak)):
                        raise SystemExit(f"{m}: invalid computed energy/power")
                else:
                    missing.add(m)
                    e = clk = acc = dyn = leak = None
                    idle = c["clocks"] - c["writes"] - c["reads"] if c["model"] in ONE_PORT else None
                rows.append(dict(memory=role(path), path=path, macro=m, writes=c["writes"], reads=c["reads"],
                                 deselected=idle, clocks=c["clocks"], energy_nJ=None if e is None else e / 1000,
                                 clock_uW=clk, access_uW=acc, dynamic_uW=dyn, leakage_uW=leak))
            table.setdefault(label, {})[s] = rows
    if missing:
        problems.append("incomplete energy characterization: " + ", ".join(sorted(missing)))
    (out / "data.json").write_text(json.dumps(dict(window_cycles=window, seconds=seconds, char=str(char_path),
                                                   configurations=table, not_characterized=sorted(missing),
                                                   problems=problems), indent=1) + "\n")

    def total(label, s, key):
        vals = [r[key] for r in table[label][s]]
        return None if any(v is None for v in vals) else sum(vals)

    print("# SRAM accesses and energy of the transmitter\n")
    print(f"Window: {window} clocks of bb_clk = s00_axi_aclk (16 MHz), {1000 * seconds:g} ms, setup subtracted. "
          f"Energies from the SPICE characterization of each OpenRAM macro (`{char_path}`): every clock costs "
          "the energy of a deselected clock (the macro's clock buffers and input flip-flops), every access its "
          "energy relative to a deselected clock; dynamic power = their sum / window time, the clock part and "
          "the access part shown apart. Leakage: char.json's, the same in every scenario.\n")
    if missing:
        print(f"Not characterized (counts only, no energy): {', '.join(f'`{m}`' for m in sorted(missing))}.\n")
    for s in SCENARIOS:
        print(f"## Scenario {s}\n")
        print("| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) "
              "| Dynamic (uW) | Leakage (uW) |")
        print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for label, _, _ in configs:
            for r in table[label][s]:
                desel = "-" if r["deselected"] is None else f"{r['deselected']}"
                print(f"| {label} | {r['memory']} | `{r['macro']}` | {r['writes']} | {r['reads']} | {desel} | "
                      f"{fmt(r['clock_uW'])} | {fmt(r['access_uW'])} | {fmt(r['dynamic_uW'])} | "
                      f"{fmt(r['leakage_uW'])} |")
        print()
    print("## Totals: the transmitter's SRAMs, dynamic power (uW)\n")
    print("| Configuration | " + " | ".join(SCENARIOS) + " | of which clocks | Leakage (uW) |")
    print("|---|" + "---:|" * (len(SCENARIOS) + 2))
    for label, _, _ in configs:
        cells = [fmt(total(label, s, "dynamic_uW")) for s in SCENARIOS]
        print(f"| {label} | " + " | ".join(cells) + f" | {fmt(total(label, SCENARIOS[0], 'clock_uW'))} "
              f"| {fmt(total(label, SCENARIOS[0], 'leakage_uW'))} |")
    print("\n— : a memory of that configuration is not characterized. The clock part is the same in every "
          "scenario: every memory takes every clock.\n")
    if problems:
        print("## Check failures\n")
        for p in problems:
            print(f"- {p}")
        print("\nCHECKS: FAIL")
        sys.exit(1)
    print("Checks: upstream's counts equal in every run; memories outside the transmitter, and the master "
          "configuration, count the same in u_ref and u_dut; every TX memory clock counts the window.")


if __name__ == "__main__":
    main()
