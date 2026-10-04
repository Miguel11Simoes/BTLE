#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Proves that, with DEFAULT parameters, the modified modules are equivalent to
# the same modules at a reference revision (default: the commit before the
# parameterised area reductions). This is what guarantees that the Vivado
# flow for the boards, which uses the defaults, sees an unchanged design.
#
# Method (per module): Yosys equivalence checking. Both versions are
# elaborated and flattened; the RAM models are the real ones, mapped to
# flip-flops on both sides (IQ-capture RAM reduced in size, see below);
# asynchronous resets are modelled as synchronous (async2sync) on both sides;
# equiv_make pairs signals by name, equiv_simple + equiv_induct prove every
# pair, and equiv_status -assert fails if any pair is unproven.
#
# Usage (WSL/Linux, repository root):
#   scripts/validation/equiv_defaults/run_equiv_defaults.sh <label> <ref-rev> [module ...]
# Output: results/validation/<label>/equiv_defaults/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_equiv_defaults.sh <label> <ref-rev> [module ...]}
ref_rev=${2:?give the reference revision}
shift 2
mods=("$@"); [ ${#mods[@]} -eq 0 ] && mods=(auxiliary_daemon gauss_filter gfsk_modulation btle_tx btle_ll btle_phy btle_controller)
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
export PATH=$OSS_CAD/bin:$PATH

repo=$(git rev-parse --show-toplevel)
source "$repo/scripts/validation/result_guard.sh"
out=$repo/results/validation/$label/equiv_defaults
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_equiv.XXXXXX)
mkdir -p "$work/gold" "$work/gate"
git -C "$repo" archive "$ref_rev" verilog | tar -x -C "$work/gold" --strip-components=1
cp "$repo"/verilog/*.v "$work/gate/"

# gold: every module renamed <name>_gold
# (the RAM models keep their names: they are the same blackbox on both sides)
names=$(grep -hoE '^[[:space:]]*module[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "$work"/gold/*.v \
        | awk '{print $2}' | sort -u | grep -vE '^sdpram_')
expr=""; for n in $names; do expr="$expr s/\\b$n\\b/${n}_gold/g;"; done
for f in "$work"/gold/*.v; do sed -E -i "$expr" "$f"; done

files() {  # $1 = dir, excluding testbenches, RAM models, the Xilinx-only RAM wrapper and
            # btle_controller_wrapper.v (it does not elaborate upstream: issue U12)
  (cd "$1" && ls *.v | grep -v '_tb\.v$' | grep -v '^btle_controller_wrapper\.v$' \
     | grep -vE '^sdpram_(one_clk|two_clk|two_clk_xilinx)(_gold)?\.v$' | sed "s|^|$1/|")
}
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ref_rev=$ref_rev ($(git -C "$repo" rev-parse "$ref_rev^{commit}"))"
  echo "gate=working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
  echo "yosys=$(yosys -V)"
} > "$out/provenance.txt"

# Instances that the parameterisation moved into a generate block get a
# "<block>." prefix. They are renamed back before flattening, so that every
# flattened signal (memory contents included) pairs with its gold twin.
#   <module>|<instance in the new RTL>|<instance name in the gold RTL>
renames='auxiliary_daemon|gen_iq_capture.sdpram_two_clk_auxiliary_daemon_i|sdpram_two_clk_auxiliary_daemon_i
btle_ll|gen_cross_axi_to_bb_full.clk_cross_bus_s_axi_to_bb_i|clk_cross_bus_s_axi_to_bb_i
btle_ll|gen_cross_bb_to_axi_full.clk_cross_bus_bb_to_s_axi_i|clk_cross_bus_bb_to_s_axi_i
btle_ll|gen_uart.uart_frame_tx_i|uart_frame_tx_i
btle_ll|gen_uart.uart_frame_rx_i|uart_frame_rx_i'

status=0
for m in "${mods[@]}"; do
  # The 1 Mbit IQ-capture RAM is too large to map to flip-flops; for the two
  # modules that contain it, BRAM_DEPTH is set to 64 on BOTH sides (only the
  # RAM size and the address-counter width change, not the logic compared).
  small=""
  case $m in auxiliary_daemon|btle_controller) small="chparam -set BRAM_DEPTH 64 ${m}_gold $m";; esac
  prelude="read_verilog $work/gate/sdpram_one_clk.v $work/gate/sdpram_two_clk.v
read_verilog $(files "$work/gold" | tr '\n' ' ')
read_verilog $(files "$work/gate" | tr '\n' ' ')
$small
hierarchy -check
proc"
  # pass 1: list the elaborated modules (parameterised variants included)
  printf '%s\ntee -q -o %s ls\n' "$prelude" "$work/$m.mods" > "$work/$m.list.ys"
  (cd "$work" && yosys -q -s "$m.list.ys") > "$work/$m.list.log" 2>&1 || { echo "elaboration failed: $m" >&2; exit 1; }; cp "$work/$m.list.log" "$work/$m.mods" "$out/" 2>/dev/null || true
  ren=""
  while IFS='|' read -r base inst gold_inst; do
    # only where the new RTL really has that generate block (a branch without
    # the reduction keeps the instance at its original name: nothing to rename)
    grep -qw "${inst%%.*}" "$work/gate/$base.v" || continue
    for mod in $(grep -oE '[^[:space:]]+' "$work/$m.mods" 2>/dev/null | grep -E "(^|\\\\)$base\$"); do
      ren="$ren
cd $mod
rename \\$inst \\$gold_inst
cd .."
    done
  done <<< "$renames"
  cat > "$work/$m.ys" <<EOF
$prelude
$ren
flatten ${m}_gold $m
memory
async2sync
opt_clean
equiv_make ${m}_gold $m equiv
hierarchy -top equiv
opt_clean
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
EOF
  if (cd "$work" && timeout 3600 yosys -q -l "$out/$m.log" -s "$m.ys") > /dev/null 2>&1 && grep -q "Equivalence successfully proven" "$out/$m.log" && grep -qE 'Found [1-9][0-9]* \$equiv cells' "$out/$m.log"; then
    echo "$m: EQUIVALENT ($(grep -oE 'Found [0-9]+ \$equiv cells' "$out/$m.log" | tail -1))" | tee -a "$out/result.txt"
  else
    echo "$m: NOT PROVEN ($(grep -m1 -E 'ERROR|unproven' "$out/$m.log"))" | tee -a "$out/result.txt"; status=1
  fi
done
gzip -9 "$out"/*.log
[ $status -eq 0 ] && echo "RESULT: PASS" | tee -a "$out/result.txt" || echo "RESULT: FAIL" | tee -a "$out/result.txt"
rm -rf "$work"
exit $status
