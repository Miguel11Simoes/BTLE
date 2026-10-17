#!/usr/bin/env python3
"""The figures of docs/TX_FINAL_DECISIONS.md: upstream's transmitter against ble-tx-min, side by side.

Author: Miguel Simões

  python3 scripts/figures/tx_final_figures.py results/figures/tx-final/data.json results/figures/tx-final

Every number comes from data.json, which names the evidence file of each one (no number is computed
here but sums and percentages). Matplotlib only; the palette is the validated default of the
project's chart guidelines (blue, orange, aqua, yellow, violet), in that fixed order.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

BLUE, ORANGE, AQUA, YELLOW, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titlesize": 10, "axes.titleweight": "bold", "figure.facecolor": "white", "axes.facecolor": "white",
})


def tidy(ax, grid_axis="x"):
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def stacked_barh(ax, names, parts, colors, labels, total_fmt="{:,.0f}"):
    y = np.arange(len(names))[::-1]
    left = np.zeros(len(names))
    for values, color, label in zip(parts, colors, labels):
        values = np.asarray(values, dtype=float)
        ax.barh(y, values, left=left, color=color, height=0.62, label=label, edgecolor="white", linewidth=1.5)
        left += values
    for yy, total in zip(y, left):
        ax.text(total, yy, "  " + total_fmt.format(total), va="center", fontsize=8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlim(0, left.max() * 1.25)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:g}k" if v >= 1000 else f"{v:g}"))
    tidy(ax)


def fig_area_45nm(d, out):
    rows = d["area_45nm"]["rows"]
    names = [r["name"] for r in rows]
    logic = [r["logic"] for r in rows]
    macros = [r["macros"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
    stacked_barh(axes[0], names, [logic, macros], [BLUE, ORANGE], ["logic (Nangate45 std cells)", "SRAM macros (OpenRAM, FreePDK45)"])
    axes[0].set_title("Transmitter area, 45 nm: every configuration")
    axes[0].set_xlabel("µm²")
    axes[0].legend(loc="lower right", fontsize=8, frameon=False)
    sel = [k for k, r in enumerate(rows) if r.get("zoom")]
    stacked_barh(axes[1], [names[k] for k in sel], [[logic[k] for k in sel], [macros[k] for k in sel]], [BLUE, ORANGE], ["", ""])
    axes[1].set_title("The smallest three, enlarged")
    axes[1].set_xlabel("µm²")
    fig.tight_layout()
    fig.savefig(out / "tx_final_area_45nm.png", dpi=130)
    plt.close(fig)


def fig_area_gf180(d, out):
    g = d["area_gf180"]
    names = [c["name"] for c in g["columns"]]
    cats = [("efuse", "eFuse blocks (AdvA, OTP)", BLUE), ("sram", "SRAM 64 × 8 (GF180MCU PDK)", ORANGE),
            ("logic", "logic (combinational, flip-flops, inverters, buffers)", AQUA),
            ("repair_clock", "timing-repair buffers + clock trees", YELLOW),
            ("physical", "taps, end caps, antenna diodes, tie", VIOLET)]
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    stacked_barh(ax, names, [[c[k] for c in g["columns"]] for k, _, _ in cats], [c for _, _, c in cats], [l for _, l, _ in cats])
    ax.set_title("Transmitter layout in GF180MCU-D (LibreLane, signoff clean): placed cells + macros")
    ax.set_xlabel("µm² (die 760 × 760 µm in both)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.28), ncol=2, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "tx_final_area_gf180.png", dpi=130)
    plt.close(fig)


def fig_fpga(d, out):
    rows = d["fpga"]["tx"]
    names = [r["name"] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, key, title in zip(axes, ("luts", "ffs", "ramb18"), ("LUTs (incl. LUTRAM)", "flip-flops", "RAMB18 (block RAM halves)")):
        values = [r[key] for r in rows]
        y = np.arange(len(rows))[::-1]
        ax.barh(y, values, color=BLUE, height=0.62, edgecolor="white", linewidth=1.5)
        for yy, v in zip(y, values):
            ax.text(v, yy, f"  {v:g}", va="center", fontsize=8, color=INK)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlim(0, max(values) * 1.3 if max(values) else 1)
        ax.set_title(title)
        tidy(ax)
    fig.suptitle("btle_tx on the xc7z020 (Vivado 2026.1, routed): the transmitter alone", fontsize=10, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "tx_final_fpga.png", dpi=130)
    plt.close(fig)


def fig_ber(d, out):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
    for ax, ppm in zip(axes, ("50", "-30")):
        b = d["ber"][ppm]
        ax.semilogy(b["snr"], b["upstream"], "+-", color=BLUE, markersize=10, linewidth=2,
                    label="upstream: Python TX (test_btle_ber.py, unmodified)")
        ax.semilogy(b["snr"], b["min_rtl"], "x--", color=ORANGE, markersize=8, linewidth=2,
                    label="ble-tx-min: RTL TX (Icarus)")
        ax.axhline(1e-3, color=INK2, linewidth=1, linestyle=":")
        ax.text(b["snr"][0], 1.15e-3, "BER 0.1 % (Core spec, -70 dBm)", fontsize=7, color=INK2)
        ax.set_title(f"BER, clock error {ppm} ppm")
        ax.set_xlabel("SNR (dB)")
        ax.set_ylabel("BER")
        tidy(ax, "both")
        ax.legend(loc="upper right", fontsize=7.5, frameon=False)
    fig.suptitle("39-byte ADV PDUs, upstream's channel and receiver (python/btlelib.py of upstream-baseline)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "tx_final_ber.png", dpi=130)
    plt.close(fig)


def fig_activity(d, out):
    a = d["activity"]
    scen = a["scenarios"]
    series = [(n, a["delta_pct"][n], c) for n, c in zip(a["order"], (BLUE, ORANGE, AQUA))]
    x = np.arange(len(scen))
    w = 0.26
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    for k, (name, values, color) in enumerate(series):
        bars = ax.bar(x + (k - 1) * w, values, width=w - 0.02, color=color, label=name, edgecolor="white", linewidth=1)
        for xx, v in zip(x + (k - 1) * w, values):
            ax.text(xx, v - 0.15, f"{v:.1f}", ha="center", va="top", fontsize=7, color=INK)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(scen)
    ax.set_ylabel("Δ data + clock switched capacitance\nagainst corrected master (%)")
    ax.set_ylim(min(min(s[1]) for s in series) * 1.22, 0.8)
    ax.set_title("Switching activity of the whole controller (gate level, Nangate45, 100 000 clocks per scenario)")
    tidy(ax, "y")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "tx_final_activity.png", dpi=130)
    plt.close(fig)


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    fig_area_45nm(data, out)
    fig_area_gf180(data, out)
    fig_fpga(data, out)
    fig_ber(data, out)
    fig_activity(data, out)
    print("figures written to", out)


if __name__ == "__main__":
    main()
