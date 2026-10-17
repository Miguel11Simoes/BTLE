#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Accesses and energy of the transmitter's SRAMs: the btle_controller of each
# named configuration against upstream's, on the workloads of tb_activity.v.
# The activity flow (run_activity.sh) leaves the RAMs out: they are macros, not
# cells. Here they are counted.
#
#   1. per configuration, one RTL simulation (Icarus) per scenario with both
#      designs, built as the controller lockstep builds them (upstream's modules
#      renamed *_ref), every RAM model replaced by one that counts its accesses
#      (sram_count_models.v); tb_activity.v compares the outputs on every clock
#   2. a setup-only run, subtracted: the counts of the window alone
#   3. summarize_sram_energy.py: the clocks, writes and reads times the energies
#      of the OpenRAM macro of each memory, characterized with SPICE
#      (run_sram_char.sh, run_sram_leakage.sh, summarize_sram_char.py --leakage:
#      every clock the energy of a deselected clock, every access its energy
#      relative to one), and, apart, the macros' settled leakage
#
#   name          RTL (git archive)   configuration (scripts/branch_config.sh)
#   master        upstream-baseline   defaults
#   <branch>      <branch>            every reduction its btle_controller declares
#
# The upstream design is in every simulation (u_ref): its counts must come out
# the same in all of them, and the "master" configuration's dut counts equal to
# them; the summary checks both.
#
# Usage (WSL/Linux, repository root):
#   scripts/power/run_sram_energy.sh <label> [name ...]
# Env: WINDOW (default 100000 bb_clk cycles), SEED (default 1),
#      VEC_DIR  the test vectors (default: generated once, example 0, 20 dB, 20 ppm,
#               kept in vectors.tar.gz)
#      SRAM_CHAR  the characterized macros (default results/power/sram-char)
# Output: results/power/<label>/ (refuses to overwrite)

set -euo pipefail
ref_rev=${REF_REV:-6589489b71704d0ff5d8eae499a6522ade0ac680}
label=${1:?usage: run_sram_energy.sh <label> [name ...]}
shift
names=("$@"); [ ${#names[@]} -eq 0 ] && names=(master)
window=${WINDOW:-100000}
seed=${SEED:-1}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
PY=${PY:-$HOME/venvs/btle/bin/python}
export PATH=$OSS_CAD/bin:$PATH
export MPLBACKEND=Agg
scenarios=(rx tx mixed idle idle0)

repo=$(git rev-parse --show-toplevel)
source "$repo/scripts/validation/result_guard.sh"
positive_counts "$window" "$seed"
here=$repo/scripts/power
char=${SRAM_CHAR:-$repo/results/power/sram-char}
[ -f "$char/char.json" ] || { echo "no $char/char.json (run scripts/power/run_sram_char.sh)" >&2; exit 1; }
out=$repo/results/power/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_sram.XXXXXX)

branch_ref() {  # branch name -> local branch, else origin/<name>
  if git -C "$repo" rev-parse --verify -q "refs/heads/$1" > /dev/null; then echo "$1"
  elif git -C "$repo" rev-parse --verify -q "refs/remotes/origin/$1" > /dev/null; then echo "origin/$1"
  else echo "no branch $1 (local or origin)" >&2; return 1; fi
}
rev_of() { if [ "$1" = master ]; then echo "$ref_rev"; else branch_ref "$1"; fi; }
sel() {  # design files of a verilog directory, without the RAM models
  (cd "$1" && ls *.v | grep -v '_tb\.v$' | grep -v '^btle_controller_wrapper' \
     | grep -vE '^sdpram_two_clk_xilinx|^sdpram_(one|two)_clk\.v$' | sed "s|^|$1/|")
}
COUNTED='sdpram_one_clk|sdpram_two_clk|pdu_buffer_ram|sin_table_ram'

# vectors: one set for every configuration
vec=$work/vec
mkdir -p "$vec/verilog"
if [ -n "${VEC_DIR:-}" ]; then
  cp "$VEC_DIR"/*.txt "$vec/verilog/"
  echo "vectors taken from VEC_DIR=$VEC_DIR" > "$out/gen_vectors.log"
else
  git -C "$repo" archive "$ref_rev" python | tar -x -C "$vec"
  (cd "$vec/python" && "$PY" test_vector_for_btle_verilog.py 0 20 20 0) > "$out/gen_vectors.log" 2>&1
fi
(cd "$vec/verilog" && sha256sum *.txt) > "$out/vectors.sha256"
tar -C "$vec/verilog" -czf "$out/vectors.tar.gz" $(cd "$vec/verilog" && ls *.txt)

# reference: upstream, every module renamed *_ref, the counting models too
mkdir -p "$work/ref"
git -C "$repo" archive "$ref_rev" verilog | tar -x -C "$work/ref" --strip-components=1
ref_names=$(grep -hoE '^[[:space:]]*module[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "$work"/ref/*.v | awk '{print $2}' | sort -u)
expr=""; for n in $ref_names; do expr="$expr s/\\b$n\\b/${n}_ref/g;"; done
for f in "$work"/ref/*.v; do sed -E -i "$expr" "$f"; done
sed -E "s/^module ($COUNTED)\\b/module \\1_ref/" "$here/sram_count_models.v" > "$work/count_ref.v"
cp "$here/sram_count_models.v" "$work/count_dut.v"

declare -A rev params
no_vco=""  # configurations whose vco.v instantiates no memory (fixed tables): their dut counts no VCO memory
for n in "${names[@]}"; do
  rev[$n]=$(rev_of "$n")
  d=$work/dut_$n
  mkdir -p "$d"
  git -C "$repo" archive "${rev[$n]}" verilog | tar -x -C "$d" --strip-components=1
  params[$n]=$(bash "$repo/scripts/branch_config.sh" "$d")
  grep -qE "^[[:space:]]*($COUNTED)[[:space:]]*(#|\()" "$d/vco.v" || no_vco="$no_vco $n"
  # the counting models replace the repository's definitions
  for f in "$d"/*.v; do sed -E -i "s/^module ($COUNTED)\\b/module \\1_unused/" "$f"; done
  # the testbench: no SAIF, the dut in its configuration, the window ends 1 ns after its last edge
  inst=""
  for kv in ${params[$n]}; do inst="$inst${inst:+, }.${kv%%=*}(${kv#*=})"; done
  tb=$work/tb_$n.v
  sed -e '/\$dumpfile(saif_name);/d' -e '/\$dumpvars(0, u_ref);/d' -e '/\$dumpvars(0, u_dut);/d' \
      -e "s/^btle_controller u_dut (/btle_controller ${inst:+#($inst) }u_dut (/" \
      -e 's/repeat (window) @(posedge bb_clk);/repeat (window) @(posedge bb_clk); #1;/' \
      "$here/tb_activity.v" > "$tb"
  { grep -qF "btle_controller ${inst:+#($inst) }u_dut (" "$tb" && ! grep -qE 'dumpfile|dumpvars' "$tb" \
      && grep -qF 'repeat (window) @(posedge bb_clk); #1;' "$tb"; } \
    || { echo "$n: the testbench was not adapted" >&2; exit 1; }
  case " ${params[$n]} " in
    *" ENABLE_IQ_CAPTURE=0 "*" LL_MINIMAL=1 "*) define="";;
    *" ENABLE_IQ_CAPTURE=0 "*|*" LL_MINIMAL=1 "*) echo "$n: A1 without A2 is not supported" >&2; exit 1;;
    *) define="-DFULL_COMPARE";;
  esac
  iverilog -g2012 -s tb_activity $define -o "$work/sim_$n" "$tb" \
    $(sel "$work/ref") "$work/count_ref.v" $(sel "$d") "$work/count_dut.v" > "$work/build_$n.log" 2>&1 \
    || { cat "$work/build_$n.log" >&2; exit 1; }
done

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "harness=$(git -C "$repo" rev-parse HEAD) (branch $(git -C "$repo" rev-parse --abbrev-ref HEAD)), dirty files under scripts/: $(git -C "$repo" status --porcelain -- scripts | wc -l)"
  echo "ref=$ref_rev ($(git -C "$repo" rev-parse "${ref_rev}^{commit}")), default parameters, in every simulation"
  echo "configurations (name, measured revision, commit, verilog/ tree, parameters):"
  for n in "${names[@]}"; do
    printf '  %s\t%s\t%s\t%s\t%s\n' "$n" "${rev[$n]}" "$(git -C "$repo" rev-parse "${rev[$n]}^{commit}")" \
      "$(git -C "$repo" rev-parse "${rev[$n]}:verilog")" "${params[$n]:-<none: defaults>}"
  done
  echo "window_cycles=$window (bb_clk = s00_axi_aclk = 16 MHz, rf_clk 8 MHz) seed=$seed scenarios=${scenarios[*]}"
  echo "vectors=${VEC_DIR:+VEC_DIR }$(sha256sum "$out/vectors.sha256" | cut -c1-16) (sha256 of vectors.sha256)"
  echo "iverilog=$(iverilog -V 2>&1 | head -1)"
  echo "configurations whose vco.v instantiates no memory:${no_vco:- none}"
  echo "sram characterization=$char ($(sha256sum "$char/char.json" | cut -c1-16) sha256 of char.json)"
} > "$out/provenance.txt"
cat "$out/provenance.txt"

# runs: every configuration, the setup reference and every scenario, in parallel
cd "$vec/verilog"
declare -A pid
for n in "${names[@]}"; do
  mkdir -p "$out/$n"
  for s in setup "${scenarios[@]}"; do
    vvp -n "$work/sim_$n" +scenario=$s +window=$window +seed=$seed > "$out/$n/run_$s.log" 2>&1 &
    pid[$n.$s]=$!
  done
done
status=0
: > "$out/runs.txt"
for n in "${names[@]}"; do
  for s in setup "${scenarios[@]}"; do
    code=0; wait "${pid[$n.$s]}" || code=$?
    if sim_pass "$code" "$out/$n/run_$s.log" 'ACTIVITY RUN PASS'; then
      line="$n $s: $(grep -m1 'activity: scenario .* cycles (' "$out/$n/run_$s.log" | sed 's/activity: //')"
    else
      line="$n $s: RUN FAILED (exit $code, see $n/run_$s.log)"; status=1
    fi
    echo "$line" | tee -a "$out/runs.txt"
    grep '^SRAMCOUNT ' "$out/$n/run_$s.log" > "$out/$n/counts_$s.txt" || true
  done
done

NO_VCO_MEMORY="$no_vco" "$PY" "$here/summarize_sram_energy.py" "$out" "$char/char.json" "$window" "${names[@]}" > "$out/summary.md" || status=1
gzip -9 "$out"/*.log "$out"/*/*.log
rm -rf "$work"
echo "RESULT: $([ $status -eq 0 ] && echo PASS || echo FAIL)" | tee -a "$out/summary.md"
exit $status
