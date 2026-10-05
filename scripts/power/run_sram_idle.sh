#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The static power of the packet buffer's macro while deselected, holding what the
# RTL leaves in it (sram_leakage.py --data). A deselected OpenRAM macro leaves its
# bitlines floating and its sense amplifiers connected to the selected column of
# each bit: a column whose cells hold both values settles between the rails, and
# that bit's sense amplifier keeps drawing a crossover current. So the static power
# of a buffer that idles depends on its words and on the address at its input.
#
# The words and inputs come from a run of run_sram_energy.sh: sram_count_models.v
# prints, at the end of each scenario, the buffer's words and its macro's address
# and data inputs (PDUMEM, PDUIN). Words never written are unknown in RTL; a memory
# holds what it powered up with, until written. Each case is measured with them at
# 0 (a buffer cleared after power-up) and random (two seeds, as after power-up).
#
# Usage (WSL/Linux, repository root):
#   scripts/power/run_sram_idle.sh <label> <sram-energy label> <configuration> <scenario ...>
# Env: OPENRAM_PY  python with OpenRAM (default ~/venvs/openram/bin/python)
#      FILLS       the fills of the unknown words (default "zero seed:1 seed:2")
# Output: results/power/<label>/ (refuses to overwrite): idle.json, summary.md,
#         provenance.txt, and per case the words, ngspice's measures, the stimulus

set -euo pipefail
label=${1:?usage: run_sram_idle.sh <label> <sram-energy label> <configuration> <scenario ...>}
energy=${2:?}; conf=${3:?}; shift 3
scenarios=("$@")
[ ${#scenarios[@]} -gt 0 ] || { echo "no scenario" >&2; exit 1; }
fills=(${FILLS:-zero seed:1 seed:2})
PY=${OPENRAM_PY:-$HOME/venvs/openram/bin/python}
repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/power
src=$repo/results/power/$energy/$conf
[ -d "$src" ] || { echo "no $src" >&2; exit 1; }
out=$repo/results/power/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_sramidle.XXXXXX)

# the words and inputs of each scenario (the configuration's buffer, u_dut)
macro=""
for s in "${scenarios[@]}"; do
  log=$src/run_$s.log; [ -f "$log" ] || log=$log.gz
  [ -f "$log" ] || { echo "no log of scenario $s in $src" >&2; exit 1; }
  text=$(zcat -f "$log")
  mem=$(grep '^PDUMEM tb_activity\.u_dut\.' <<< "$text" | head -n 1 | cut -d' ' -f3-)
  inp=$(grep '^PDUIN tb_activity\.u_dut\.' <<< "$text" | head -n 1)
  [ -n "$mem" ] && [ -n "$inp" ] || { echo "$s: no PDUMEM/PDUIN of u_dut in $log (sram_count_models.v of this branch)" >&2; exit 1; }
  echo "$mem" | tr ' ' '\n' > "$out/$s.words"
  n=$(wc -l < "$out/$s.words")
  m=sram_1rw_8x$n
  [ -z "$macro" ] || [ "$macro" = "$m" ] || { echo "the scenarios give different buffers" >&2; exit 1; }
  macro=$m
  read -r _ _ _ a _ d <<< "$inp"
  [[ $a =~ ^[0-9]+$ && $d =~ ^[0-9]+$ ]] || { echo "$s: unknown inputs ($inp)" >&2; exit 1; }
  echo "$a $d" > "$out/$s.inputs"
done

unset OPENRAM_HOME
P=$("$PY" -c "import os, importlib.util; print(os.path.dirname(importlib.util.find_spec('openram').origin))")
export OPENRAM_TECH=$P/technology
NGSPICE=$P/miniconda/bin/ngspice
MODELS=$OPENRAM_TECH/freepdk45/models/tran_models/models_nom
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git -C "$repo" rev-parse HEAD)"
  echo "words and inputs: results/power/$energy/$conf, scenarios ${scenarios[*]} (PDUMEM, PDUIN)"
  echo "macro=$macro, OpenRAM's netlist (netlist_only, every bitcell); ngspice of OpenRAM's conda"
  echo "measure=sram_leakage.py --data: deselected, the given address and data inputs, one clock pulse at 1-2 ns,"
  echo "        every data cell started at its bit, 5 us; fills of the unknown words: ${fills[*]}"
} > "$out/provenance.txt"

d=$work/net; mkdir -p "$d"
cat > "$d/cfg.py" <<EOF
word_size = 8
num_words = ${macro##*x}
num_rw_ports = 1
num_r_ports = 0
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
output_name = "$macro"
EOF
(cd "$d" && timeout 3600 "$PY" "$P/sram_compiler.py" cfg.py) > "$out/$macro.openram.log" 2>&1 \
  && [ -s "$d/out/$macro.sp" ] || { echo "OpenRAM failed (see $macro.openram.log)" >&2; exit 1; }

pids=(); cases=()
for s in "${scenarios[@]}"; do
  read -r a dd < "$out/$s.inputs"
  for f in "${fills[@]}"; do
    c=$s.${f/:/}; cases+=("$c")
    ( timeout 43200 python3 "$here/sram_leakage.py" "$d/out/$macro.sp" "$macro" "$work/$c" "$NGSPICE" "$MODELS" \
        --data "$out/$s.words" --addr "$a" --din "$dd" --fill "$f" > "$work/$c.json" 2> "$out/$c.log" \
      && echo "$c: done" || echo "$c: FAILED (see $c.log)" ) &
    pids+=($!)
  done
done
status=0
for p in "${pids[@]}"; do wait "$p" || status=1; done
for c in "${cases[@]}"; do
  for f in stim.sp measures.txt; do [ -f "$work/$c/leakage_$f" ] && cp "$work/$c/leakage_$f" "$out/$c.leakage_$f"; done
done

python3 - "$work" "$out" "$macro" "${cases[@]}" <<'PYEOF' || status=1
import json, sys
from pathlib import Path
work, out, macro, cases = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4:]
data = {}
for c in cases:
    f = work / f'{c}.json'
    if f.exists() and f.read_text().strip():
        data[c] = json.loads(f.read_text().strip().splitlines()[-1])
(out / 'idle.json').write_text(json.dumps(data, indent=1) + '\n')
with open(out / 'summary.md', 'w') as s:
    s.write(f'# The packet buffer deselected, with the words the RTL leaves in it ({macro}, FreePDK45, ngspice)\n\n')
    s.write('Static power once the macro has settled (sram_leakage.py --data, 4.5-5 us). The unknown words (never\n'
            'written) at 0 or random; the column that the address selects, per bit: how many of its cells hold 1, and\n'
            'its sense amplifier\'s input at 5 us (between 0.3 and 0.7 V: a crossover current).\n\n')
    s.write('| Case | Address | Data in | Unknown words | Ones in the selected columns | Sense-amplifier inputs at 5 us (V) | Static power (uW) |\n')
    s.write('|---|---:|---:|---:|---|---|---:|\n')
    for c, d in data.items():
        sa = [d['probes_V'].get(f'sa{b}_5000ns') for b in range(len(d['ones']))]
        s.write(f"| {c} | {d['addr']} | {d['din']} | {d['unknown']} | {' '.join(map(str, d['ones']))} of {d['cells']} | "
                + ' '.join('-' if x is None else f'{x:.2f}' for x in sa) + f" | **{1000 * d['leakage_mW']:.1f}** |\n")
    missing = [c for c in cases if c not in data]
    if missing:
        s.write(f"\nNot measured: {', '.join(missing)}\n")
print((out / 'summary.md').read_text())
sys.exit(1 if missing or any(d['spread'] > 0.02 for d in data.values()) else 0)
PYEOF
gzip -9 "$out"/*.log "$out"/*.leakage_stim.sp 2>/dev/null || true   # the decks hold every cell: 0.4 MB each
rm -rf "$work"
exit $status
