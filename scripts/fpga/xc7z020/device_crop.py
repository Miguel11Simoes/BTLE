#!/usr/bin/env python3
"""Crop the device out of device_view.ps1's capture of Vivado's maximized Device panel.

Author: Miguel Simões

  python3 scripts/fpga/xc7z020/device_crop.py <dir>/device_full.png results/fpga/xc7z020/<configuration>/device.png

The canvas is the longest run of mostly black rows, and across, the longest black run of its top row; the
device is the box of the lit pixels inside it (its outline, clock regions and cells), with a margin of 6
pixels.
"""

from __future__ import annotations

import sys

import numpy as np
from PIL import Image


def longest_run(mask):
    best, start = (0, 0), None
    for i, on in enumerate(list(mask) + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if i - start > best[1] - best[0]:
                best = (start, i)
            start = None
    return best


def main():
    im = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    level = im.max(axis=2).astype(int)
    dark = level < 30
    r0, r1 = longest_run(dark.mean(axis=1) > 0.5)
    c0, c1 = longest_run(dark[r0 + 4])   # zoom to fit leaves black above the device, edge to edge
    r0, r1, c0, c1 = r0 + 2, r1 - 2, c0 + 2, c1 - 2   # off the canvas's own border
    assert r1 - r0 > 300 and c1 - c0 > 300, "no Device canvas: is the Device panel maximized?"
    ys, xs = np.nonzero(level[r0:r1, c0:c1] > 40)
    pad = 6
    top, bottom = max(r0 + ys.min() - pad, 0), min(r0 + ys.max() + pad + 1, im.shape[0])
    left, right = max(c0 + xs.min() - pad, 0), min(c0 + xs.max() + pad + 1, im.shape[1])
    Image.fromarray(im[top:bottom, left:right]).save(sys.argv[2])
    print(f"{sys.argv[2]}: {right - left} x {bottom - top} px (canvas rows {r0}-{r1}, columns {c0}-{c1})")


if __name__ == "__main__":
    main()
