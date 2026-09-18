#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Per-module area of the BLE baseband: standard cells (Nangate45) + SRAM bits.
#
# Method (same as MS-0-S1-YOSYS in snitch_cluster_tese):
#   - sdpram_one_clk / sdpram_two_clk are read as blackboxes (-lib): SRAMs are
#     macros, never mapped as flip-flops. Their bits are counted separately.
#   - logic: synth -flatten -> dfflibmap -> abc -liberty -> stat -liberty.
#   - every run records the toolchain, liberty hash and git commit.
#
# Usage (inside WSL/Linux, from the repository root):
#   scripts/area/run_area.sh <label> [top ...]
# Environment:
#   OSS_CAD  OSS CAD Suite root  (default ~/eda/oss-cad-suite-20260907)
#   LIBERTY  liberty file        (default ~/eda/NangateOpenCellLibrary_typical.lib)
# Output: results/area/<label>/  (refuses to overwrite an existing label)

set -euo pipefail

label=${1:?usage: run_area.sh <label> [top ...]}
shift || true

OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
LIBERTY=${LIBERTY:-$HOME/eda/NangateOpenCellLibrary_typical.lib}
YOSYS=$OSS_CAD/bin/yosys
ABC=$OSS_CAD/bin/yosys-abc

repo=$(git rev-parse --show-toplevel)
rtl=$repo/verilog
out=$repo/results/area/$label

# Bottom-up, so a failure points at the smallest module that breaks.
default_tops=(
  crc24 scramble bit_repeat_upsample gauss_filter vco gfsk_modulation btle_tx
  gfsk_demodulation search_unique_bit_sequence btle_rx_core btle_rx btle_phy
  clock_domain_conversion_iq auxiliary_daemon btle_ll btle_controller
)
if [ $# -gt 0 ]; then tops=("$@"); else tops=("${default_tops[@]}"); fi

[ -x "$YOSYS" ] || { echo "yosys not found at $YOSYS" >&2; exit 1; }
[ -f "$LIBERTY" ] || { echo "liberty not found at $LIBERTY" >&2; exit 1; }
[ -e "$out" ] && { echo "$out exists; choose a new label, never overwrite" >&2; exit 1; }
mkdir -p "$out"

# RTL set: every non-testbench file, minus the RAM models (read as blackboxes)
# and the Xilinx-only RAM wrapper (only used under `ifdef XILINX_XPM).
mapfile -t logic_files < <(cd "$rtl" && ls *.v | grep -v '_tb\.v$' \
  | grep -vx -e sdpram_one_clk.v -e sdpram_two_clk.v -e sdpram_two_clk_xilinx.v)
ram_files=(sdpram_one_clk.v sdpram_two_clk.v)

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git -C "$repo" rev-parse HEAD)"
  echo "git_dirty=$(git -C "$repo" status --porcelain -- verilog | wc -l)"
  echo "yosys=$("$YOSYS" -V)"
  echo "liberty=$(basename "$LIBERTY")"
  echo "liberty_sha256=$(sha256sum "$LIBERTY" | cut -d' ' -f1)"
  echo "rtl_files=${logic_files[*]}"
  echo "ram_blackboxes=${ram_files[*]}"
} > "$out/provenance.txt"

status=0
for top in "${tops[@]}"; do
  d=$out/$top
  mkdir -p "$d"
  {
    echo "read_verilog -lib ${ram_files[*]}"
    echo "read_verilog ${logic_files[*]}"
    echo "hierarchy -check -top $top"
    echo "synth -flatten -top $top"
    echo "check -assert"
    echo "dfflibmap -liberty $LIBERTY"
    echo "abc -exe $ABC -liberty $LIBERTY"
    echo "opt_clean -purge"
    echo "read_liberty -lib $LIBERTY"
    echo "tee -o $d/stat.json stat -json -liberty $LIBERTY"
    echo "tee -o $d/stat.txt stat -liberty $LIBERTY"
    echo "write_json $d/netlist.json"
  } > "$d/stage.ys"
  if (cd "$rtl" && "$YOSYS" -q -T -l "$d/yosys.log" -s "$d/stage.ys" > /dev/null 2>&1); then
    echo "[area] $top: PASS"
  else
    echo "[area] $top: FAIL (see $d/yosys.log)"
    status=1
  fi
done

python3 "$repo/scripts/area/summarize_area.py" "$out" | tee "$out/summary.md"

# Netlists are large and reproducible: keep their hashes, not the files, in git.
# Logs are the evidence: keep them, compressed.
(cd "$out" && sha256sum */netlist.json > netlist.sha256 && gzip -9 */yosys.log)
exit $status
