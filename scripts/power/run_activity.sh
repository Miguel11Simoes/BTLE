#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Post-synthesis switching activity: upstream btle_controller (defaults) vs a
# branch in its configuration (on ble-opt: the reduced configuration), on
# identical workloads.
#
#   1. gate-level netlists (synth_gate_netlist.sh; Nangate45, RAMs as macros)
#   2. Nangate cell simulation models generated from the liberty
#   3. one Verilator simulation with BOTH netlists (tb_activity.v), per scenario,
#      writing SAIF; outputs compared on every clock (gate-level lockstep)
#   4. a setup-only run, subtracted net by net (saif_activity.py)
#   5. summary tables (summarize_activity.py)
#
# This is activity and a pin-capacitance proxy, NOT power: no wires, no clock
# tree, no parasitics, no STA.
#
# Usage (WSL/Linux, repository root):
#   scripts/power/run_activity.sh <label> [window-cycles] [seed] [ref-rev]
# Env:
#   DUT_REV     measure the verilog/ of this git revision instead of the working tree
#   DUT_PARAMS  the dut configuration (default: every reduction its btle_controller
#               declares, switched on; see scripts/branch_config.sh)
#   VEC_DIR     take the test vectors from this directory instead of generating them
#               (python/test_vector_for_btle_verilog.py 0 20 20 0). The generator's
#               noise is not seeded, so two runs see the same stimulus only if they
#               share one vector set; the sha256 of the set is kept in vectors.sha256.
# What is compared follows from the configuration: with both A1 and A2
# (ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1) the three removed outputs are skipped and
# removed registers must read 0; with neither, everything is compared
# (tb_activity.v, FULL_COMPARE). Only one of the two is not supported.
# Output: results/power/<label>/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_activity.sh <label> [window] [seed] [ref-rev]}
window=${2:-100000}
seed=${3:-1}
ref_rev=${4:-upstream-baseline}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
LIBERTY=${LIBERTY:-$HOME/eda/NangateOpenCellLibrary_typical.lib}
PY=${PY:-$HOME/venvs/btle/bin/python}
export PATH=$OSS_CAD/bin:$PATH
export MPLBACKEND=Agg
DUT_REV=${DUT_REV:-}
VEC_DIR=${VEC_DIR:-}
scenarios=(rx tx mixed idle idle0)

repo=$(git rev-parse --show-toplevel)
source "$repo/scripts/validation/result_guard.sh"
positive_counts "$window" "$seed"
here=$repo/scripts/power
out=$repo/results/power/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_act.XXXXXX)

# 1. netlists
mkdir -p "$work/ref"
git -C "$repo" archive "$ref_rev" verilog | tar -x -C "$work/ref"
if [ -n "$DUT_REV" ]; then
  mkdir -p "$work/dut"
  git -C "$repo" archive "$DUT_REV" verilog | tar -x -C "$work/dut"
  dut_rtl=$work/dut/verilog
  dut_desc="$DUT_REV ($(git -C "$repo" rev-parse "$DUT_REV^{commit}"), verilog tree $(git -C "$repo" rev-parse "$DUT_REV:verilog"))"
else
  dut_rtl=$repo/verilog
  dut_desc="working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
fi
DUT_PARAMS=${DUT_PARAMS-$(bash "$repo/scripts/branch_config.sh" "$dut_rtl")}
has() { case " $DUT_PARAMS " in *" $1 "*) return 0;; *) return 1;; esac; }
if has ENABLE_IQ_CAPTURE=0 && has LL_MINIMAL=1; then
  compare=reduced; tb_define=""
elif has ENABLE_IQ_CAPTURE=0 || has LL_MINIMAL=1; then
  echo "DUT_PARAMS: A1 without A2 (or the reverse) is not supported by tb_activity.v" >&2; exit 1
else
  compare=full; tb_define="-DFULL_COMPARE"
fi
bash "$here/synth_gate_netlist.sh" "$work/ref/verilog" "$work/ref_gl.v" _ref > /dev/null
bash "$here/synth_gate_netlist.sh" "$dut_rtl" "$work/dut_gl.v" "" $DUT_PARAMS > /dev/null
cp "$work/ref_gl.v.stat" "$out/netlist_ref.stat"; cp "$work/dut_gl.v.stat" "$out/netlist_dut.stat"
sha256sum "$work/ref_gl.v" "$work/dut_gl.v" | sed "s|$work/||" > "$out/netlists.sha256"

# 2. cell models
yosys -q -p "read_liberty -ignore_miss_func $LIBERTY; write_verilog -noattr $work/nangate_cells.v"

# 3. simulator
verilator --binary --timing --trace-saif --trace-underscore -Wno-fatal -Wno-lint -Wno-style $tb_define \
  --top tb_activity -O2 --x-assign fast --x-initial fast -j "$(nproc)" --Mdir "$work/obj" -o sim \
  "$here/tb_activity.v" "$work/ref_gl.v" "$work/dut_gl.v" "$work/nangate_cells.v" \
  "$repo/verilog/sdpram_one_clk.v" "$repo/verilog/sdpram_two_clk.v" > "$work/verilator.log" 2>&1 \
  || { tail -30 "$work/verilator.log"; exit 1; }

# vectors: example 0 of the Python model (ADV packet, channel 37), 20 dB, 20 ppm
mkdir -p "$work/vec/verilog"
if [ -n "$VEC_DIR" ]; then
  cp "$VEC_DIR"/*.txt "$work/vec/verilog/"
  echo "vectors taken from VEC_DIR=$VEC_DIR" > "$out/gen_vectors.log"
else
  git -C "$repo" archive "$ref_rev" python | tar -x -C "$work/vec"
  (cd "$work/vec/python" && $PY test_vector_for_btle_verilog.py 0 20 20 0) > "$out/gen_vectors.log" 2>&1
fi
(cd "$work/vec/verilog" && sha256sum *.txt) > "$out/vectors.sha256"

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ref=$ref_rev ($(git -C "$repo" rev-parse "$ref_rev^{commit}")), default parameters"
  echo "dut=$dut_desc, ${DUT_PARAMS:-default parameters}"
  echo "compare=$compare (full: every output and register; reduced: the three removed outputs skipped, removed registers read 0)"
  echo "window_cycles=$window (bb_clk 16 MHz) seed=$seed scenarios=${scenarios[*]}"
  echo "vectors=${VEC_DIR:+VEC_DIR }$(sha256sum "$out/vectors.sha256" | cut -c1-16) (sha256 of vectors.sha256)"
  echo "yosys=$(yosys -V)"
  echo "verilator=$(verilator --version)"
  echo "liberty=$(basename "$LIBERTY") sha256=$(sha256sum "$LIBERTY" | cut -d' ' -f1)"
} > "$out/provenance.txt"

# 4. runs: the setup reference and every scenario, in parallel
cd "$work/vec/verilog"
declare -A sim_pids sim_codes
"$work/obj/sim" +scenario=setup +saif="$work/setup.saif" +seed=$seed > "$out/run_setup.log" 2>&1 &
sim_pids[setup]=$!
for s in "${scenarios[@]}"; do
  "$work/obj/sim" +scenario=$s +window=$window +saif="$work/$s.saif" +seed=$seed > "$out/run_$s.log" 2>&1 &
  sim_pids[$s]=$!
done
status=0
printf '{' > "$out/exit_codes.json"
separator=""
for s in setup "${scenarios[@]}"; do
  sim_codes[$s]=0
  wait "${sim_pids[$s]}" || sim_codes[$s]=$?
  printf '%s"%s":%d' "$separator" "$s" "${sim_codes[$s]}" >> "$out/exit_codes.json"
  separator=,
  sim_pass "${sim_codes[$s]}" "$out/run_$s.log" 'ACTIVITY RUN PASS' || status=1
done
printf '}\n' >> "$out/exit_codes.json"
if ! sim_pass "${sim_codes[setup]}" "$out/run_setup.log" 'ACTIVITY RUN PASS'; then
  echo 'RESULT: FAIL (setup simulation failed)' > "$out/summary.md"
  exit 1
fi
for s in "${scenarios[@]}"; do
  if sim_pass "${sim_codes[$s]}" "$out/run_$s.log" 'ACTIVITY RUN PASS'; then
    echo "$s: $(grep -m1 'activity: scenario .* cycles (' "$out/run_$s.log" | sed 's/activity: //')" | tee -a "$out/runs.txt"
    $PY "$here/saif_activity.py" "$work/$s.saif" "$work/setup.saif" "$work/ref_gl.v" "$work/dut_gl.v" \
      "$LIBERTY" "$window" "$s" "$out/$s.json" | tee -a "$out/analysis.txt"
  else
    echo "$s: RUN FAILED (see run_$s.log)" | tee -a "$out/runs.txt"; status=1
  fi
done

# 5. summary
$PY "$here/summarize_activity.py" "$out" > "$out/summary.md" || status=1
gzip -9 "$out"/*.log
rm -rf "$work"
exit $status
