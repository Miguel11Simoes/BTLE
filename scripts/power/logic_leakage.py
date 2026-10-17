#!/usr/bin/env python3
"""Static leakage of the standard cells of a synthesized block: the liberty's cell_leakage_power of every cell.

Author: Miguel Simões

  python3 scripts/power/logic_leakage.py <liberty> <name>=<results/area/.../<top>/stat.json> ...

For each block, the cells of its Yosys `stat -json` (num_cells_by_type, after dfflibmap and abc, as
scripts/area/run_area.sh writes it) times each cell's cell_leakage_power in the liberty (Nangate45
typical: 1.10 V, 25 C, in the unit of leakage_power_unit). The state-independent leakage of the cell:
no state dependence (the liberty's `leakage_power` groups per input state are not used), no wires, no
SRAM macros (they are blackboxes in the netlist; scripts/power/run_sram_leakage.sh measures theirs).
Prints a Markdown table on stdout.
"""

import json
import re
import sys
from pathlib import Path


def cell_leakage(liberty: str) -> tuple[dict, str]:
    unit = re.search(r'leakage_power_unit\s*:\s*"?([0-9.]+\s*[a-zA-Z]+)"?', liberty)
    heads = [(m.start(), m.group(1)) for m in re.finditer(r'^\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', liberty, re.M)]
    leak = {}
    for k, (pos, name) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(liberty)
        m = re.search(r'^\s*cell_leakage_power\s*:\s*([0-9.eE+-]+)\s*;', liberty[pos:end], re.M)
        leak[name] = float(m.group(1)) if m else None
    return leak, unit.group(1).replace(" ", "") if unit else "?"


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    leak, unit = cell_leakage(Path(sys.argv[1]).read_text())
    if unit != "1nW":
        raise SystemExit(f"unexpected leakage_power_unit {unit}")
    print(f"Leakage of the standard cells (liberty `{Path(sys.argv[1]).name}`, cell_leakage_power, {unit}), "
          "SRAM macros excluded (blackboxes).\n")
    print("| Block | Cells | Leakage (µW) | of which flip-flops (µW) | Not priced (macros, `$print`) |")
    print("|---|---:|---:|---:|---|")
    for arg in sys.argv[2:]:
        name, path = arg.split("=", 1)
        st = json.loads(Path(path).read_text())
        mod = st["design"] if "design" in st else st["modules"][next(iter(st["modules"]))]
        types = mod["num_cells_by_type"]
        cells = {t: n for t, n in types.items() if leak.get(t) is not None}
        other = {t: n for t, n in types.items() if leak.get(t) is None}
        if any(not (t.startswith("$") or t.startswith("sdpram")) for t in other):
            raise SystemExit(f"{name}: cells without leakage in the liberty: {other}")
        total = sum(leak[t] * n for t, n in cells.items()) / 1000.0
        seq = sum(leak[t] * n for t, n in cells.items() if t.startswith(("DFF", "SDFF", "DLH", "DLL"))) / 1000.0
        print(f"| {name} | {sum(cells.values())} | {total:.2f} | {seq:.2f} | "
              f"{', '.join(f'{t} × {n}' for t, n in sorted(other.items())) or '—'} |")


if __name__ == "__main__":
    main()
