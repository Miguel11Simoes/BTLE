#!/usr/bin/env python3
"""The tables of docs/Senseworks/TX_TAG_COMPARISON.md, from the results of the tag's runs (run tx-tag).

Author: Miguel Simões

  python3 scripts/senseworks/tag_summary.py [--liberty LIB] > results/senseworks/tx_tag_summary.md

Reads, at the repository root:
  results/area/tx-tag/<configuration>/<top>/stat.json   run_area.sh (Nangate45), the five configurations
  results/timing/tx-tag/<branch>/summary.tsv             run_sta.sh (STA_SET=tx, reference ble-tx-min)
  results/layout/<label>/metrics.json                    the GF180MCU layouts (LibreLane), the tags' and
                                                         ble-tx-min's (tx-clean-gf180, -sram64)
and computes the time on the air of each packet. The 32 x 8 SRAM of ble-tx-min (OpenRAM, FreePDK45) is
results/area/openram-min (2 475.8 um^2) and results/power/sram-leakage-min (16.41 uW); the leakage of the
standard cells is scripts/power/logic_leakage.py's (the liberty's cell_leakage_power).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/power"))
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402
from logic_leakage import cell_leakage  # noqa: E402

CONFIGS = [  # (results/area/tx-tag/<name>, label, SRAM macro area um^2, SRAM leakage uW)
    ("ble-tx-min", "`ble-tx-min` (AdvData 32 × 8 SRAM)", 2475.8, 16.41),
    ("ble-tx-min-flops", "`ble-tx-min`, AdvData in flip-flops", 0.0, 0.0),
    ("ble-tx-tag-8", "**`ble-tx-tag-8`**", 0.0, 0.0),
    ("ble-tx-tag-12", "**`ble-tx-tag-12`**", 0.0, 0.0),
    ("ble-tx-tag-18", "**`ble-tx-tag-18`**", 0.0, 0.0),
]
TAGS = [(8, "ble-tx-tag-8"), (12, "ble-tx-tag-12"), (18, "ble-tx-tag-18")]
LAYOUTS = [("tx-clean-gf180", "`ble-tx-min`, AdvData in flip-flops"),
           ("tx-clean-gf180-sram64", "`ble-tx-min`, AdvData in the SRAM 64 × 8"),
           ("tx-tag-8-gf180", "**`ble-tx-tag-8`**"), ("tx-tag-12-gf180", "**`ble-tx-tag-12`**"),
           ("tx-tag-18-gf180", "**`ble-tx-tag-18`**")]
SIGNOFF = ["route__drc_errors", "klayout__drc_error__count", "magic__drc_error__count", "design__lvs_error__count",
           "antenna__violating__nets", "design__max_slew_violation__count", "design__max_cap_violation__count",
           "design__max_fanout_violation__count"]


def fmt(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", " ")


def stat(config: str, top: str) -> dict | None:
    p = ROOT / "results/area/tx-tag" / config / top / "stat.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d["design"] if "design" in d else next(iter(d["modules"].values()))


def flops(s: dict) -> int:
    return sum(n for c, n in s.get("num_cells_by_type", {}).items() if c.startswith(("DFF", "SDFF", "TLAT")))


def sram_bits(s: dict) -> int:
    return sum(n for c, n in s.get("num_cells_by_type", {}).items() if c.startswith("sdpram"))


def leakage(s: dict, leak: dict) -> tuple[float, float]:
    total = ff = 0.0
    for c, n in s.get("num_cells_by_type", {}).items():
        v = leak.get(c)
        if v is None:
            continue
        total += v * n
        if c.startswith(("DFF", "SDFF", "TLAT")):
            ff += v * n
    return total / 1000.0, ff / 1000.0   # nW -> uW


def airtime() -> str:
    rows = ["| Packet | PDU (bytes) | On the air (bytes) | Time | One event (3 channels) | vs `ble-tx-min`'s 39-byte PDU |",
            "|---|---:|---:|---:|---:|---:|"]
    ref = 3 * (1 + 4 + 39 + 3) * 8
    cases = [("`ble-tx-min`'s campaigns: 39-byte PDU (31 bytes of AdvData)", 39),
             ("the minimal packet, no FEC (AdvA, `05 FF CID CID d0 d1`)", 14)]
    cases += [(f"**`ble-tx-tag-{t}`** (+{tag_bch.parity_bytes(t)} bytes of parity)", 2 + tag_bch.payload_length(t))
              for t, _ in TAGS]
    for label, pdu in cases:
        us = (1 + 4 + pdu + 3) * 8
        rows.append(f"| {label} | {pdu} | {1 + 4 + pdu + 3} | {us} µs | {3 * us} µs | {100 * (3 * us / ref - 1):+.1f} % |")
    return "\n".join(rows)


def area(leak: dict) -> str:
    rows = ["| `btle_tx` | cells | flip-flops | logic (µm²) | SRAM macro (µm²) | **TX total (µm²)** | vs `ble-tx-min` | "
            "logic leakage (µW) | + SRAM | **TX static (µW)** |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    base = None
    for name, label, macro, sram_leak in CONFIGS:
        s = stat(name, "btle_tx")
        if s is None:
            rows.append(f"| {label} | — | — | — | — | — | — | — | — | — |")
            continue
        total = s["area"] + macro
        base = total if base is None else base
        lk, _ = leakage(s, leak)
        rows.append(f"| {label} | {s['num_cells']} | {flops(s)} | {fmt(s['area'])} | {fmt(macro) if macro else '—'} | "
                    f"**{fmt(total)}** | {100 * (total / base - 1):+.1f} % | {lk:.2f} | {sram_leak:.2f} | "
                    f"**{lk + sram_leak:.2f}** |")
    return "\n".join(rows)


def blocks() -> str:
    tops = ["crc24", "scramble", "gfsk_modulation", "btle_tx", "btle_phy", "btle_ll", "btle_controller"]
    rows = ["| Cell area (µm²) | " + " | ".join(f"`{t}`" for t in tops) + " |",
            "|---|" + "---:|" * len(tops)]
    for name, label, _, _ in CONFIGS:
        cells = []
        for t in tops:
            s = stat(name, t)
            cells.append(fmt(s["area"]) if s else "—")
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    rows.append("")
    rows.append("| `btle_controller` | cells | flip-flops | cell area (µm²) | SRAM bits | of which `btle_phy` (µm², SRAM bits) |")
    rows.append("|---|---:|---:|---:|---:|---:|")
    for name, label, _, _ in CONFIGS:
        s, p = stat(name, "btle_controller"), stat(name, "btle_phy")
        if s is None or p is None:
            continue
        rows.append(f"| {label} | {s['num_cells']} | {flops(s)} | {fmt(s['area'])} | {sram_bits_of(name, 'btle_controller')} | "
                    f"{fmt(p['area'])}, {sram_bits_of(name, 'btle_phy')} |")
    return "\n".join(rows)


def sram_bits_of(config: str, top: str) -> str:
    p = ROOT / "results/area/tx-tag" / config / "summary.md"
    if not p.exists():
        return "—"
    for line in p.read_text().splitlines():
        if line.startswith(f"| `{top}` |"):
            return line.split("|")[-2].strip()
    return "—"


def timing() -> str:
    rows = ["| | comb. path (ns) | min period (ns) | slack at 62.5 ns | Fmax (MHz) |", "|---|---:|---:|---:|---:|"]
    seen = set()
    for t, branch in TAGS:
        p = ROOT / "results/timing/tx-tag" / branch / "summary.tsv"
        if not p.exists():
            continue
        for line in p.read_text().splitlines()[1:]:
            f = line.split("\t")
            name = {"ref_controller": "`ble-tx-min` `btle_controller` (receiver included, default parameters)",
                    "ref_btle_tx": "`ble-tx-min` `btle_tx` (GAUSS_TABLE=1)",
                    "dut_controller": f"`{branch}` `btle_controller`", "dut_btle_tx": f"**`{branch}` `btle_tx`**"}[f[0]]
            if name in seen:
                continue
            seen.add(name)
            rows.append(f"| {name} | {float(f[2]):.3f} | {float(f[4]):.3f} | +{float(f[5]):.3f} ns | {float(f[6]):.1f} |")
    return "\n".join(rows)


def layout() -> str:
    def m(label):
        p = ROOT / "results/layout" / label / "metrics.json"
        return json.loads(p.read_text()) if p.exists() else None
    ms = [(lab, name, m(lab)) for lab, name in LAYOUTS]
    ms = [x for x in ms if x[2] is not None]
    cls = lambda d, c: d.get(f"design__instance__area__class:{c}", 0.0)  # noqa: E731
    rows = ["| GF180MCU-D (µm²) | " + " | ".join(name for _, name, _ in ms) + " |", "|---|" + "---:|" * len(ms)]
    lines = [
        ("eFuse blocks (AdvA, OTP)", lambda d: cls(d, "macro") - sram(d)),
        ("SRAM", lambda d: sram(d)),
        ("Logic: combinational, flip-flops, inverters, buffers",
         lambda d: cls(d, "multi_input_combinational_cell") + cls(d, "sequential_cell") + cls(d, "inverter") + cls(d, "buffer")),
        ("Timing-repair buffers + clock trees", lambda d: cls(d, "timing_repair_buffer") + cls(d, "clock_buffer") + cls(d, "clock_inverter")),
        ("Taps, end caps, antenna diodes", lambda d: cls(d, "tap_cell") + cls(d, "endcap_cell") + cls(d, "antenna_cell")),
        ("**Placed cells + macros**", lambda d: d["design__instance__area"] - cls(d, "fill_cell")),
    ]
    for label, f in lines:
        vals = [f(d) for _, _, d in ms]
        rows.append(f"| {label} | " + " | ".join("—" if v == 0 and 'SRAM' in label else fmt(v) for v in vals) + " |")
    rows.append("| flip-flops | " + " | ".join(str(int(d.get("design__instance__count__class:sequential_cell", 0))) for _, _, d in ms) + " |")
    rows.append("")
    rows.append("| Signoff | " + " | ".join(name for _, name, _ in ms) + " |")
    rows.append("|---|" + "---:|" * len(ms))
    rows.append("| DRC: routing, KLayout, Magic | " + " | ".join(
        f"{d.get('route__drc_errors')}, {d.get('klayout__drc_error__count')}, {d.get('magic__drc_error__count')}" for _, _, d in ms) + " |")
    for key, label in [("design__lvs_error__count", "LVS errors"), ("antenna__violating__nets", "antenna violations"),
                       ("design__max_slew_violation__count", "max slew violations"),
                       ("design__max_cap_violation__count", "max capacitance violations"),
                       ("design__max_fanout_violation__count", "max fanout violations")]:
        rows.append(f"| {label} | " + " | ".join(str(d.get(key)) for _, _, d in ms) + " |")
    rows.append("| worst setup / hold slack, 9 corners (ns) | " + " | ".join(
        f"+{d['timing__setup__ws']:.3f} / +{d['timing__hold__ws']:.3f}" for _, _, d in ms) + " |")
    rows.append("| IR drop, worst (mV) | " + " | ".join(f"{1000 * d.get('ir__drop__worst', 0):.2f}" for _, _, d in ms) + " |")
    rows.append("| clock skew, worst (ns) | " + " | ".join(f"{d.get('clock__skew__worst_setup', 0):.2f}" for _, _, d in ms) + " |")
    rows.append("| OpenSTA vectorless power, 5 V (mW) | " + " | ".join(f"{1000 * d.get('power__total', 0):.2f}" for _, _, d in ms) + " |")
    return "\n".join(rows)


def sram(d: dict) -> float:
    # the GF180 SRAM 64 x 8 of the sram64 layout: the macros minus the six eFuse blocks (8 075.35 um^2 each)
    return max(0.0, d.get("design__instance__area__class:macro", 0.0) - 6 * 8075.35)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--liberty", default=str(Path.home() / "eda/NangateOpenCellLibrary_typical.lib"))
    a = parser.parse_args()
    leak, unit = cell_leakage(Path(a.liberty).read_text())
    assert unit.lower() == "1nw", unit
    print("# The senseworks tag's transmitters: the tables (run `tx-tag`)\n")
    print("Generated by `scripts/senseworks/tag_summary.py`.\n")
    print("## Time on the air\n\n" + airtime() + "\n")
    print("## Area and leakage of the transmitter (Nangate45 / FreePDK45)\n\n" + area(leak) + "\n")
    print("## The blocks and the controller\n\n" + blocks() + "\n")
    print("## Timing (Nangate45, pre-layout)\n\n" + timing() + "\n")
    print("## Layout in GF180MCU-D (LibreLane)\n\n" + layout() + "\n")


if __name__ == "__main__":
    main()
