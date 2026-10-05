#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The static leakage of SRAM macros, every bitcell holding 0, once each macro has
# settled (sram_leakage.py, which explains why): OpenRAM in FreePDK45 writes the
# netlist of each macro (the netlist of run_sram_char.sh, every bitcell; no
# characterization), and ngspice from OpenRAM's conda runs OpenRAM's own leakage
# measure on it for 5 us instead of 10 ns, after one deselected clock. OpenRAM's
# figure (run_sram_char.sh, the .lib's cell_leakage_power) is that of the first
# 10 ns after a power-up from 0 V, when the bitlines and the sense amplifiers'
# inputs, driven by nothing in a deselected macro, still sit between the rails and
# the sense amplifiers draw a crossover current. Where they settle depends on the
# data: with every cell at 0 they reach the rails; run_sram_idle.sh measures a
# macro holding given words.
#
# Macro names as in run_openram.sh: sram_<1rw|1rw1r>_<word bits>x<words>.
# Usage (WSL/Linux, repository root): scripts/power/run_sram_leakage.sh <label> <macro ...>
# Env: OPENRAM_PY  python with OpenRAM (default ~/venvs/openram/bin/python)
# Output: results/power/<label>/ (refuses to overwrite): leakage.json (read by
#         summarize_sram_char.py --leakage), summary.md, provenance.txt, and per macro
#         the stimulus, ngspice's measures and OpenRAM's log (compressed)

set -euo pipefail
label=${1:?usage: run_sram_leakage.sh <label> <macro ...>}
shift
macros=("$@")
[ ${#macros[@]} -gt 0 ] || { echo "no macro" >&2; exit 1; }
for m in "${macros[@]}"; do
  [[ $m =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)$ ]] || { echo "bad macro name $m" >&2; exit 1; }
done
PY=${OPENRAM_PY:-$HOME/venvs/openram/bin/python}
repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/power
out=$repo/results/power/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_sramleak.XXXXXX)

unset OPENRAM_HOME
P=$("$PY" -c "import os, importlib.util; print(os.path.dirname(importlib.util.find_spec('openram').origin))")
export OPENRAM_TECH=$P/technology
NGSPICE=$P/miniconda/bin/ngspice
MODELS=$OPENRAM_TECH/freepdk45/models/tran_models/models_nom

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git -C "$repo" rev-parse HEAD)"
  echo "openram=$("$PY" -c 'import importlib.metadata as m; print(m.version("openram"))' 2>/dev/null || true) ($P)"
  echo "simulator=ngspice of OpenRAM's conda: $("$NGSPICE" -v 2>/dev/null | grep -m1 -i 'revision' || true)"
  echo "tech=freepdk45, nominal corner only (TT, 1.0 V, 25 C), netlist_only=True (OpenRAM's whole netlist, every bitcell)"
  echo "measure=sram_leakage.py: OpenRAM's leakage run (UIC, every port deselected, address and data 0), every"
  echo "        bitcell at 0, one clock pulse at 1-2 ns, 5 us at a step of at most 1 ns; leakage = average supply"
  echo "        power over 4.5-5 us"
  echo "macros=${macros[*]}"
} > "$out/provenance.txt"

macro() {  # $1 = name
  [[ $1 =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)$ ]]
  local ports=${BASH_REMATCH[1]} ws=${BASH_REMATCH[2]} nw=${BASH_REMATCH[3]} d=$work/$1 nr=0
  [ "$ports" = 1rw1r ] && nr=1
  mkdir -p "$d"
  cat > "$d/cfg.py" <<EOF
word_size = $ws
num_words = $nw
num_rw_ports = 1
num_r_ports = $nr
num_w_ports = 0
tech_name = "freepdk45"
nominal_corner_only = True
process_corners = ["TT"]
supply_voltages = [1.0]
temperatures = [25]
check_lvsdrc = False
netlist_only = True
analytical_delay = True
output_path = "$d/out"
output_name = "$1"
EOF
  if (cd "$d" && timeout 3600 "$PY" "$P/sram_compiler.py" cfg.py) > "$out/$1.openram.log" 2>&1 \
       && [ -s "$d/out/$1.sp" ] \
       && timeout 43200 python3 "$here/sram_leakage.py" "$d/out/$1.sp" "$1" "$d/leak" "$NGSPICE" "$MODELS" \
            > "$d/result.json" 2> "$out/$1.log"; then
    echo "$1: done"
  else
    echo "$1: FAILED (see $1.openram.log, $1.log)"; return 1
  fi
}

pids=()
for m in "${macros[@]}"; do macro "$m" & pids+=($!); done
status=0
for p in "${pids[@]}"; do wait "$p" || status=1; done
for m in "${macros[@]}"; do
  for f in stim.sp measures.txt; do
    [ -f "$work/$m/leak/leakage_$f" ] && cp "$work/$m/leak/leakage_$f" "$out/$m.leakage_$f"
  done
done

python3 - "$work" "$out" "${macros[@]}" <<'PYEOF' || status=1
import json, sys
from pathlib import Path
work, out, macros = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
data = {}
for m in macros:
    f = work / m / 'result.json'
    if f.exists() and f.read_text().strip():
        data[m] = json.loads(f.read_text())
(out / 'leakage.json').write_text(json.dumps(data, indent=1) + '\n')
w = ['leak_5_10ns', 'leak_0p5_1us', 'leak_1_2us', 'leak_3_4us', 'leak_4_4p5us', 'leak_4p5_5us']
with open(out / 'summary.md', 'w') as s:
    s.write('# Static leakage of SRAM macros, FreePDK45, ngspice, every cell at 0, settled\n\n')
    s.write("OpenRAM's leakage run (UIC, every port deselected, average supply power) with every bitcell holding 0,\n"
            'after one deselected clock, for 5 us instead of 10 ns (scripts/power/sram_leakage.py). The leakage is\n'
            "the last window, 4.5-5 us; the first, 5-10 ns, is OpenRAM's own window.\n\n")
    s.write('| Macro | 5-10 ns (uW) | 0.5-1 us | 1-2 us | 3-4 us | 4-4.5 us | **Leakage, 4.5-5 us (uW)** |\n')
    s.write('|---|---:|---:|---:|---:|---:|---:|\n')
    for m, d in data.items():
        v = d['windows_mW']
        s.write(f"| `{m}` | " + ' | '.join(f"{1000 * v[k]:.2f}" for k in w[:-1]) + f" | **{1000 * v[w[-1]]:.2f}** |\n")
    s.write('\nThe selected column of each bit (address 0): its bitline and its sense amplifier\'s input (V), at\n'
            '10 ns, 1 us and 5 us:\n\n')
    s.write('| Macro | Bit | bitline | sense-amplifier input |\n|---|---:|---|---|\n')
    for m, d in data.items():
        b = 0
        while f'bl{b}_10ns' in d['probes_V']:
            f = lambda k: ' / '.join('-' if d['probes_V'].get(f'{k}{b}_{t}ns') is None
                                     else f"{d['probes_V'][f'{k}{b}_{t}ns']:.3f}" for t in (10, 1000, 5000))
            s.write(f"| `{m}` | {b} | {f('bl')} | {f('sa')} |\n")
            b += 1
    missing = [m for m in macros if m not in data]
    if missing:
        s.write(f"\nNot measured: {', '.join(missing)}\n")
print((out / 'summary.md').read_text())
sys.exit(1 if missing or any(d['spread'] > 0.02 for d in data.values()) else 0)
PYEOF
gzip -9 "$out"/*.log 2>/dev/null || true
rm -rf "$work"
exit $status
