#!/usr/bin/env python3
"""The tables of docs/Senseworks/TX_POC_TMP100.md, from the results of run tx-poc-tmp100 and of the branches it is compared with.

Author: Miguel Simões

  python3 scripts/senseworks/poc_summary.py [--liberty LIB] > results/senseworks/tx_poc_tmp100_summary.md

Reads, at the repository root:
  results/area/tx-poc-tmp100/<top>/stat.json               run_area.sh (Nangate45)
  results/timing/tx-poc-tmp100/summary.tsv                 run_sta.sh (STA_SET=poc, reference ble-tx-tag-1byte)
  results/layout/tx-poc-tmp100-<efuse|rom>-gf180/metrics.json  the GF180MCU layouts (LibreLane)
  results/fpga/xc7z020-tmp100/tmp100/               Vivado, the controller out of context
and, of the branches it is compared with, from themselves, by git (REVS): ble-tx-tag-8, ble-tx-tag-1byte, ble-tx-poc.
The leakage of the standard cells is scripts/power/logic_leakage.py's (the liberty's cell_leakage_power). A pad's area is the
GF180MCU I/O library's LEF, gf180mcu_fd_io__in_c and __bi_t, 75 x 350 um, ESD protection included.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/power"))
from logic_leakage import cell_leakage  # noqa: E402

RUN = "tx-poc-tmp100"
REVS = {"ble-tx-tag-8": "86a194a6", "ble-tx-tag-1byte": "7fb89713", "ble-tx-poc": "a289da0a"}
PAD_UM2 = 75.0 * 350.0
EXTRA_PADS = [("`rate[2:0]`, had the chip kept the rate", 3)]               # what this chip adds to the tag's pins, with what it is


def fmt(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", " ")


def read_rev(rev: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def design_of(text: str | None) -> dict | None:
    if text is None:
        return None
    d = json.loads(text)
    return d["design"] if "design" in d else next(iter(d["modules"].values()))


def stat_here(top: str) -> dict | None:
    p = ROOT / "results/area" / RUN / top / "stat.json"
    return design_of(p.read_text()) if p.exists() else None


def stat_rev(branch: str, path: str) -> dict | None:
    return design_of(read_rev(REVS[branch], path))


def flops(s: dict) -> int:
    return sum(n for c, n in s.get("num_cells_by_type", {}).items() if c.startswith(("DFF", "SDFF", "TLAT")))


def leakage_uw(s: dict, leak: dict) -> float:
    return sum(leak.get(c, 0.0) * n for c, n in s.get("num_cells_by_type", {}).items()) / 1000.0


def area_table(leak: dict) -> str:
    rows = ["| Nangate45, AdvA a constant | cells | flip-flops | cell area (µm²) | leakage (µW) |", "|---|---:|---:|---:|---:|"]
    cases = [("`ble-tx-tag-8` `btle_tx`, on its pair, config ports free", stat_rev("ble-tx-tag-8", "results/area/tx-tag/ble-tx-tag-8/btle_tx/stat.json")),
             ("`btle_tx` with the direct port, two bytes, config ports free", stat_here("btle_tx")),
             ("`ble-tx-poc` `tag_chip`, compiled profile (the generic core)", stat_rev("ble-tx-poc", "results/area/tx-poc/otp/tag_chip/stat.json")),
             ("`ble-tx-poc` `tag_chip`, EEPROM", stat_rev("ble-tx-poc", "results/area/tx-poc/eeprom/tag_chip/stat.json")),
             ("`tag_chip_rate`: the period on three pins", stat_here("tag_chip_rate")),
             ("**`tag_chip`**: this branch's chip", stat_here("tag_chip"))]
    for label, s in cases:
        if s is None:
            rows.append(f"| {label} | — | — | — | — |")
        else:
            rows.append(f"| {label} | {s['num_cells']} | {flops(s)} | {fmt(s['area'])} | {leakage_uw(s, leak):.2f} |")
    return "\n".join(rows)


def timing_table() -> str:
    p = ROOT / "results/timing" / RUN / "summary.tsv"
    if not p.exists():
        return "(no run)"
    names = {"ref_controller": "`ble-tx-tag-1byte` `btle_controller`", "dut_controller": "this branch's `btle_controller`",
             "ref_btle_tx": "`ble-tx-tag-1byte` `btle_tx`", "dut_btle_tx": "`btle_tx`, direct port",
             "dut_tag_chip": "**`tag_chip`**", "dut_tag_chip_rate": "`tag_chip_rate`, the period on pins"}
    rows = ["| Nangate45, pre-layout | comb. path (ns) | min period (ns) | slack at 62.5 ns | Fmax (MHz) |", "|---|---:|---:|---:|---:|"]
    for line in p.read_text().splitlines()[1:]:
        f = line.split("\t")
        rows.append(f"| {names[f[0]]} | {float(f[2]):.3f} | {float(f[4]):.3f} | +{float(f[5]):.3f} ns | {float(f[6]):.1f} |")
    return "\n".join(rows)


def layout_table() -> str:
    def here(label):
        p = ROOT / "results/layout" / label / "metrics.json"
        return json.loads(p.read_text()) if p.exists() else None

    def rev(branch, label):
        text = read_rev(REVS[branch], f"results/layout/{label}/metrics.json")
        return json.loads(text) if text else None

    ms = [("`ble-tx-tag-8`, `btle_tx`", rev("ble-tx-tag-8", "tx-tag-8-gf180")),
          ("`ble-tx-poc`, compiled profile", rev("ble-tx-poc", "tx-poc-otp-gf180")),
          ("**`tag_chip`, eFuse**", here(f"{RUN}-efuse-gf180")),
          ("**`tag_chip`, no eFuse**", here(f"{RUN}-rom-gf180"))]
    ms = [m for m in ms if m[1] is not None]
    cls = lambda d, c: d.get(f"design__instance__area__class:{c}", 0.0)  # noqa: E731
    rows = ["| GF180MCU-D (µm²) | " + " | ".join(n for n, _ in ms) + " |", "|---|" + "---:|" * len(ms)]
    for label, f in [
        ("eFuse blocks (AdvA, OTP)", lambda d: cls(d, "macro")),
        ("Logic: combinational, flip-flops, inverters, buffers",
         lambda d: cls(d, "multi_input_combinational_cell") + cls(d, "sequential_cell") + cls(d, "inverter") + cls(d, "buffer")),
        ("Timing-repair buffers + clock trees", lambda d: cls(d, "timing_repair_buffer") + cls(d, "clock_buffer") + cls(d, "clock_inverter")),
        ("Taps, end caps, antenna diodes", lambda d: cls(d, "tap_cell") + cls(d, "endcap_cell") + cls(d, "antenna_cell")),
        ("**Placed cells + macros**", lambda d: d["design__instance__area"] - cls(d, "fill_cell")),
    ]:
        rows.append(f"| {label} | " + " | ".join(fmt(f(d)) for _, d in ms) + " |")
    rows.append("| flip-flops | " + " | ".join(str(int(d.get("design__instance__count__class:sequential_cell", 0))) for _, d in ms) + " |")
    rows += ["", "| Signoff | " + " | ".join(n for n, _ in ms) + " |", "|---|" + "---:|" * len(ms)]
    rows.append("| DRC: routing, KLayout, Magic | " + " | ".join(
        f"{d.get('route__drc_errors')}, {d.get('klayout__drc_error__count')}, {d.get('magic__drc_error__count')}" for _, d in ms) + " |")
    for key, label in [("design__lvs_error__count", "LVS errors"), ("antenna__violating__nets", "antenna violations"),
                       ("design__max_slew_violation__count", "max slew violations"),
                       ("design__max_cap_violation__count", "max capacitance violations"),
                       ("design__max_fanout_violation__count", "max fanout violations")]:
        rows.append(f"| {label} | " + " | ".join(str(d.get(key)) for _, d in ms) + " |")
    rows.append("| worst setup / hold slack, 9 corners (ns) | " + " | ".join(
        f"+{d['timing__setup__ws']:.3f} / +{d['timing__hold__ws']:.3f}" for _, d in ms) + " |")
    return "\n".join(rows)


def fpga_table() -> str:
    d = ROOT / "results/fpga/xc7z020-tmp100/tmp100"
    if not d.exists():
        return "(no run)"
    hier = (d / "impl_util_hier.rpt").read_text()
    rows = ["| xc7z020, routed | LUTs | flip-flops | RAMB36 | RAMB18 | DSP48 |", "|---|---:|---:|---:|---:|---:|"]
    for name, label in (("btle_controller", "**`btle_controller`**"), ("tag_fsm_i", "of which `tag_fsm`"), ("btle_tx_i", "of which `btle_tx`")):
        m = re.search(r"^\|\s*" + name + r"\s*\|[^|]*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
                      hier, re.M)
        if m:
            rows.append(f"| {label} | {m.group(1)} | {m.group(2)} | {m.group(3)} | {m.group(4)} | {m.group(5)} |")
    timing = (d / "timing.rpt").read_text()
    wns = re.findall(r"^\s*(\w+)\s+(-?\d+\.\d+)\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+", timing, re.M)
    rows += ["", "WNS: " + ", ".join(f"`{clk}` {float(w):+.3f} ns" for clk, w in wns if clk in ("bb_clk", "rf_clk", "axi_clk", "bram_clk"))]
    return "\n".join(rows)


def pad_table() -> str:
    rows = ["| Pads beyond SCL, SDA, clock, reset and the radio's | Pads | GF180MCU-D, cell area of the pads (µm²) |", "|---|---:|---:|"]
    for label, n in EXTRA_PADS:
        rows.append(f"| {label} | {n} | {fmt(n * PAD_UM2, 0)} |")
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--liberty", default=str(Path.home() / "eda/NangateOpenCellLibrary_typical.lib"))
    a = parser.parse_args()
    leak, unit = cell_leakage(Path(a.liberty).read_text())
    assert unit.lower() == "1nw", unit
    print(f"# The tag: the tables (run `{RUN}`)\n")
    print("Generated by `scripts/senseworks/poc_summary.py`.\n")
    print("## Area and leakage (Nangate45 / FreePDK45)\n\n" + area_table(leak) + "\n")
    print("## Timing (Nangate45, pre-layout)\n\n" + timing_table() + "\n")
    print("## Layout in GF180MCU-D (LibreLane)\n\n" + layout_table() + "\n")
    print("## The pads\n\n" + pad_table() + "\n")
    print("## FPGA (Vivado, out of context)\n\n" + fpga_table() + "\n")


if __name__ == "__main__":
    main()
