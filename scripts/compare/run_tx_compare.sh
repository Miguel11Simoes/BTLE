#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# TX area of the Gaussian filter options, measured in ONE run with the area
# flow of every branch (scripts/area/run_area.sh: Yosys, Nangate45, RAMs as
# blackboxed macros). RX is not measured.
#
#   name               revision            parameters     Gaussian filter
#   master             upstream-baseline   -              upstream FIR: 17 terms, 9 runtime taps
#   ble-tx-fir2        ble-tx-fir2         -              folded (symmetric) FIR: 8 pairs + centre, 9 runtime taps
#   ble-tx-table       ble-tx-table        GAUSS_TABLE=1  distributed-arithmetic tables as constants (ROM in logic)
#   ble-tx-table-reg   ble-tx-table-reg    GAUSS_TABLE=1  the same tables in flip-flops, rebuilt from runtime taps
#   ble-tx-table-sram  ble-tx-table-sram   GAUSS_TABLE=1  the same tables in SRAM, rebuilt from runtime taps
#
# Tops: gauss_filter, gfsk_modulation and btle_tx (the whole transmitter), and
# the table sub-modules where the branch has them (gauss_table_builder,
# gauss_table_reg, gauss_table_sram). The SRAM banks are blackboxed by the
# flow; their area is read from the OpenRAM run committed on
# ble-tx-table-sram (results/area/$OPENRAM_LABEL/, scripts/area/run_openram.sh).
#
# Usage (WSL/Linux, repository root of any branch that carries this script):
#   scripts/compare/run_tx_compare.sh <label>
# Env: OPENRAM_LABEL (default openram-gauss)
# Output: results/area/<label>/<name>/ and results/compare/<label>/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_tx_compare.sh <label>}
OPENRAM_LABEL=${OPENRAM_LABEL:-openram-gauss}
repo=$(git rev-parse --show-toplevel)
out=$repo/results/compare/$label
for d in "$out" "$repo/results/area/$label"; do
  [ -e "$d" ] && { echo "$d exists; choose a new label" >&2; exit 1; }
done
mkdir -p "$out"

branch_ref() {  # local branch, else origin/<name>
  if git -C "$repo" rev-parse --verify -q "refs/heads/$1" > /dev/null; then echo "$1"
  elif git -C "$repo" rev-parse --verify -q "refs/remotes/origin/$1" > /dev/null; then echo "origin/$1"
  else echo "no branch $1 (local or origin)" >&2; return 1; fi
}

configs="master|upstream-baseline|
ble-tx-fir2|$(branch_ref ble-tx-fir2)|
ble-tx-table|$(branch_ref ble-tx-table)|GAUSS_TABLE=1
ble-tx-table-reg|$(branch_ref ble-tx-table-reg)|GAUSS_TABLE=1
ble-tx-table-sram|$(branch_ref ble-tx-table-sram)|GAUSS_TABLE=1"
sram_rev=$(branch_ref ble-tx-table-sram)

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "harness=$(git -C "$repo" rev-parse HEAD) (branch $(git -C "$repo" rev-parse --abbrev-ref HEAD)), dirty files under scripts/: $(git -C "$repo" status --porcelain -- scripts | wc -l)"
  echo "configurations (name, revision, commit, verilog/ tree, parameters):"
  while IFS='|' read -r n r p; do
    printf '  %s\t%s\t%s\t%s\t%s\n' "$n" "$r" "$(git -C "$repo" rev-parse "$r^{commit}")" \
      "$(git -C "$repo" rev-parse "$r:verilog")" "${p:-<none: defaults>}"
  done <<< "$configs"
  echo "openram=$sram_rev:results/area/$OPENRAM_LABEL/summary.md (commit $(git -C "$repo" rev-parse "$sram_rev^{commit}"))"
} > "$out/provenance.txt"
cat "$out/provenance.txt"
git -C "$repo" show "$sram_rev:results/area/$OPENRAM_LABEL/summary.md" > "$out/openram_summary.md"

status=0
pids=()
while IFS='|' read -r n r p; do
  tops="gauss_filter gfsk_modulation btle_tx"
  for m in gauss_table_builder gauss_table_reg gauss_table_sram; do
    git -C "$repo" show "$r:verilog/gauss_filter.v" | grep -qE "^[[:space:]]*module[[:space:]]+$m\b" && tops="$tops $m"
  done
  ( RTL_REV="$r" AREA_PARAMS="$p" bash "$repo/scripts/area/run_area.sh" "$label/$n" $tops ) \
    > "$out/area_$n.log" 2>&1 & pids+=($!)
done <<< "$configs"
for p in "${pids[@]}"; do wait "$p" || status=1; done

python3 "$repo/scripts/compare/summarize_tx.py" "$repo" "$label" > "$out/summary.md" || status=1
gzip -9 "$out"/*.log
echo "RESULT: $([ $status -eq 0 ] && echo PASS || echo FAIL)" | tee -a "$out/summary.md"
exit $status
