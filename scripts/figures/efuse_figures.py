#!/usr/bin/env python3
"""The figures of the AdvA OTP block (GF180MCU eFuse), from the files in results/otp/gf180-efuse/.

Author: Miguel Simões

Run from the repository root in WSL:

  python3 scripts/figures/efuse_figures.py xyce   OUT_DIR   # efuse_xyce.png (NumPy, Matplotlib)
  python3 scripts/figures/efuse_figures.py layout OUT_DIR   # efuse_async_mem_1x8.png (the klayout module)

xyce: the compiler's own Xyce runs on the block's extracted netlist (results/otp/gf180-efuse/run/,
`./efuse.py 1 8 --async-efuse --digital-wrapper=async`, provenance.txt): xyce_async_write_0
programs PROG[0], [2], [4] and [6] (the current through each fuse while it blows), xyce_async_read_0
senses the block with those four fuses blown (blown.map) after a reset.
layout: the block's GDS (macros/efuse_array_async_1x8/efuse_async_mem_1x8/), KLayout's default layer colours on black,
fitted, 1000 x 1000 px. KLayout 0.30.4 as in the compiler's nix-shell (pip: klayout==0.30.4.post1).
"""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OTP = ROOT / "results/otp/gf180-efuse"


def read_csv(run: str) -> dict:
    import numpy as np
    with gzip.open(OTP / "run" / run / "xyce.csv.gz", "rt") as f:
        names = f.readline().strip().split(",")
        data = np.loadtxt(f, delimiter=",", ndmin=2)
    return {n: data[:, k] for k, n in enumerate(names)}


def fig_xyce(out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    w, r = read_csv("xyce_async_write_0"), read_csv("xyce_async_read_0")
    fig, axs = plt.subplots(3, 1, figsize=(8.8, 8.25))

    ax = axs[0]
    t = w["TIME"] * 1e9
    ax.plot(t, w["V(RESET_N)"], "k", label="RESET_N")
    for k in (0, 2, 4, 6):
        ax.plot(t, w[f"V(PROG[{k}])"], label=f"PROG[{k}]")
    ax.set_ylabel("V")
    ax.set_title("eFuse block efuse_async_mem_1x8 (GF180MCU), Xyce on the extracted netlist: programming")

    ax = axs[1]
    for n in [n for n in w if n.startswith("I(")]:
        ax.plot(t, abs(w[n]) * 1e3, label=n.split(":")[1])
    ax.set_ylabel("fuse current (mA)")
    ax.set_title("current through the fuses while PROG is high (blowing)")
    ax.legend(loc="upper left", fontsize=7, ncol=2)

    ax = axs[2]
    t = r["TIME"] * 1e9
    ax.plot(t, r["V(RESET_N)"], "k", lw=2, label="RESET_N")
    for k in range(8):
        ax.plot(t, r[f"V(OUT[{k}])"], label=f"OUT[{k}]")
    ax.set_ylabel("V")
    ax.set_xlabel("time (ns, simulation time-scaled)")
    ax.set_title("sensing after reset: blown fuses read 1 (OUT), intact ones 0")
    ax.legend(loc="upper left", fontsize=7, ncol=3)

    axs[0].legend(loc="upper left", fontsize=8)
    for ax in axs:
        ax.grid(True)
    plt.tight_layout()
    plt.savefig(out_dir / "efuse_xyce.png", dpi=100)
    plt.close()
    print("saved", out_dir / "efuse_xyce.png")


def fig_layout(out_dir: Path) -> None:
    import klayout.lay as lay

    gds = OTP / "macros/efuse_array_async_1x8/efuse_async_mem_1x8/efuse_async_mem_1x8.gds"
    v = lay.LayoutView()
    v.load_layout(str(gds), True)
    v.max_hier()
    v.zoom_fit()
    v.set_config("background-color", "#000000")
    v.set_config("grid-visible", "false")
    v.save_image(str(out_dir / "efuse_async_mem_1x8.png"), 1000, 1000)
    print("saved", out_dir / "efuse_async_mem_1x8.png")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("figure", choices=("xyce", "layout"))
    p.add_argument("out_dir", type=Path)
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    fig_xyce(a.out_dir) if a.figure == "xyce" else fig_layout(a.out_dir)


if __name__ == "__main__":
    main()
