#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Controller-level lockstep (tb_ctl_lockstep.v): the upstream btle_controller
# (a git revision, default upstream-baseline; every module renamed *_ref)
# against the working-tree btle_controller of branch ble-tx-table with
# GAUSS_TABLE=1, driven through the AXI-lite registers. Adapted from ble-opt:
# nothing is removed on this branch, so every output and every register is
# compared.
#
#   1. Mutation check: four wrong variants must each be caught: three wrong
#      tables (a tap, a group index, a sign), and one change to the IQ-capture
#      half flag, which shows that the outputs ble-opt excludes are compared here.
#   2. Lockstep: for each packet of the Python model (examples 0, 1, 2) and
#      each seed, no difference on any output or register read.
#
# Usage (WSL/Linux, repository root):
#   scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label> [seeds] [packets] [ref-rev]
# Output: results/validation/<label>/ctl_lockstep/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_ctl_lockstep.sh <label> [seeds] [packets] [ref-rev]}
seeds=${2:-5}
packets=${3:-6}
ref_rev=${4:-upstream-baseline}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
PY=${PY:-$HOME/venvs/btle/bin/python}
export PATH=$OSS_CAD/bin:$PATH
export MPLBACKEND=Agg

repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/validation/ctl_lockstep
out=$repo/results/validation/$label/ctl_lockstep
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_ctl.XXXXXX)

# reference: every upstream module renamed *_ref (RAM models included)
mkdir -p "$work/ref"
git -C "$repo" archive "$ref_rev" verilog | tar -x -C "$work/ref" --strip-components=1
names=$(grep -hoE '^[[:space:]]*module[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "$work"/ref/*.v | awk '{print $2}' | sort -u)
expr=""; for n in $names; do expr="$expr s/\\b$n\\b/${n}_ref/g;"; done
for f in "$work"/ref/*.v; do sed -E -i "$expr" "$f"; done
sel() {  # design files of a verilog directory
  (cd "$1" && ls *.v | grep -v '_tb\.v$' | grep -v '^btle_controller_wrapper' \
     | grep -vE '^sdpram_two_clk_xilinx' | sed "s|^|$1/|")
}
ref_files=$(sel "$work/ref")

build() {  # $1 = binary, $2 = dut verilog directory
  iverilog -g2012 -o "$1" "$here/tb_ctl_lockstep.v" $ref_files $(sel "$2") 2> "$1.compile.log" \
    || { cat "$1.compile.log" >&2; return 1; }
}

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ref_rev=$ref_rev ($(git -C "$repo" rev-parse "$ref_rev^{commit}"))"
  echo "dut=working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
  echo "dut configuration: GAUSS_TABLE=1 (nothing removed: every output and register compared)"
  echo "iverilog=$(iverilog -V 2>&1 | head -1)"
  echo "seeds_per_example=$seeds packets_per_seed=$packets"
} > "$out/provenance.txt"

for ex in 0 1 2; do
  mkdir -p "$work/vec$ex/verilog"
  git -C "$repo" archive "$ref_rev" python | tar -x -C "$work/vec$ex"
  (cd "$work/vec$ex/python" && $PY test_vector_for_btle_verilog.py "$ex" 20 20 0) > "$out/gen_ex$ex.log" 2>&1
done

# ---- 1. mutation check ----
mut_ok=1
mutate() {  # $1 = name, $2 = file, $3 = sed expression, or "perl:<expression>" for a multi-line edit
  local m=$work/mut_$1
  mkdir -p "$m"; cp "$repo"/verilog/*.v "$m/"
  case $3 in perl:*) perl -0pi -e "${3#perl:}" "$m/$2";; *) sed -E -i "$3" "$m/$2";; esac
  cmp -s "$repo/verilog/$2" "$m/$2" && { echo "mutation $1 did not change $2" >&2; exit 1; }
  build "$m/sim" "$m" || { echo "mutation $1: does not compile" | tee -a "$out/mutation.txt"; mut_ok=0; return; }
  if (cd "$work/vec2/verilog" && vvp -n "$m/sim" +seed=1 +packets=6) > "$out/mutation_$1.log" 2>&1 \
       && grep -q 'CTL LOCKSTEP PASS' "$out/mutation_$1.log"; then
    echo "mutation $1: NOT DETECTED" | tee -a "$out/mutation.txt"; mut_ok=0
  else
    echo "mutation $1: detected ($(grep -m1 MISMATCH "$out/mutation_$1.log"))" | tee -a "$out/mutation.txt"
  fi
}
# one table tap wrong (24 -> 23)
mutate wrong_table_tap gauss_filter.v "s/\{16'd24, 16'd22,/{16'd23, 16'd22,/"
# table group B indexed one position off
mutate group_off_by_one gauss_filter.v 's/table_b\[bit_upsample_store\[10:5\]\]/table_b[bit_upsample_store[11:6]]/'
# a zero bit adds the tap instead of subtracting it
mutate wrong_sign gauss_filter.v 's/\? table_tap\(first_pos\+k\) : -table_tap\(first_pos\+k\)/? table_tap(first_pos+k) : table_tap(first_pos+k)/'
# IQ-capture half flag loses its mid-buffer point (ll_itrpt2: excluded on ble-opt, compared here)
mutate capture_half_flag auxiliary_daemon.v 's/\(bram_addr_b == 0 \|\| bram_addr_b == \(BRAM_DEPTH\/2\)\)/(bram_addr_b == 0)/'

# ---- 2. lockstep ----
build "$work/sim" "$repo/verilog"
n_pass=0; n_fail=0
printf 'example\tseed\tresult\tstatistics\n' > "$out/summary.tsv"
for ex in 0 1 2; do
  for s in $(seq 1 "$seeds"); do
    log=$out/ex${ex}_seed$s.log
    (cd "$work/vec$ex/verilog" && vvp -n "$work/sim" +seed=$s +packets=$packets) > "$log" 2>&1 || true
    if grep -q 'CTL LOCKSTEP PASS' "$log"; then res=PASS; n_pass=$((n_pass+1)); else res=FAIL; n_fail=$((n_fail+1)); fi
    printf '%s\t%s\t%s\t%s\n' "$ex" "$s" "$res" "$(grep -m1 'ctl lockstep: cycles' "$log" | sed 's/ctl lockstep: //')" >> "$out/summary.tsv"
  done
done
gzip -9 "$out"/*.log
{
  echo "mutations: $(grep -c detected "$out/mutation.txt")/4 detected"
  echo "lockstep runs: $((n_pass+n_fail)) pass=$n_pass fail=$n_fail"
  awk -F'\t' 'NR>1 {split($4,a," "); c+=a[2]; cmp+=a[4]; irq+=a[6]; ok+=a[8]; tx+=a[10]; rd+=a[12]}
              END {printf "compared: cycles %d compared %d rx_irqs %d rx_crc_ok %d tx_packets %d axi_reads %d\n", c, cmp, irq, ok, tx, rd}' "$out/summary.tsv"
  if [ $mut_ok -eq 1 ] && [ $n_fail -eq 0 ]; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; fi
} | tee "$out/result.txt"
rm -rf "$work"
[ $mut_ok -eq 1 ] && [ $n_fail -eq 0 ]
