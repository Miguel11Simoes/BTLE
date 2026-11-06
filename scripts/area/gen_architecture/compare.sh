#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The comparison of docs/Senseworks/TX_POC_GEN.md section 6: the same four profiles and the same pins, by run_area.sh's
# recipe (Yosys + ABC, Nangate45), on tag_chip (a table of slots run by one counter, the branch's design) and on the sketch
# tag_chip_sequencer.v (a sequencer FSM with a program per sensor and one bit engine for I2C and SPI, only synthesized).
#
# Usage (WSL/Linux, repository root): scripts/area/gen_architecture/compare.sh <output file>
set -euo pipefail
out=${1:?usage: compare.sh <output file>}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
LIBERTY=${LIBERTY:-$HOME/eda/NangateOpenCellLibrary_typical.lib}
repo=$(git rev-parse --show-toplevel)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mapfile -t files < <(cd "$repo/verilog" && ls *.v | grep -v '_tb\.v$' | grep -vx -e sdpram_one_clk.v -e sdpram_two_clk.v -e sdpram_two_clk_xilinx.v)
{
  echo "commit=$(git -C "$repo" rev-parse HEAD) dirty=$(git -C "$repo" status --porcelain -- verilog scripts/area | wc -l)"
  for top in tag_chip tag_chip_sequencer; do
    cat > "$work/$top.ys" <<EOF
read_verilog -lib sdpram_one_clk.v sdpram_two_clk.v
read_verilog ${files[*]} $repo/scripts/area/gen_architecture/tag_chip_sequencer.v
hierarchy -check -top $top
synth -flatten -top $top
check -assert
dfflibmap -liberty $LIBERTY
abc -exe $OSS_CAD/bin/yosys-abc -liberty $LIBERTY
opt_clean -purge
read_liberty -lib $LIBERTY
tee -o $work/$top.stat stat -liberty $LIBERTY
EOF
    (cd "$repo/verilog" && "$OSS_CAD/bin/yosys" -q -l "$work/$top.log" -s "$work/$top.ys" > /dev/null 2>&1)
    area=$(grep 'Chip area' "$work/$top.stat" | tail -1 | awk '{print $NF}')
    ff=$(grep -E 'DFF[A-Z]*_X' "$work/$top.stat" | awk '{s+=$1} END {print s+0}')
    printf '%s\tarea %.1f um2\tflip-flops %s\n' "$top" "$area" "$ff"
  done
} | tee "$out"
