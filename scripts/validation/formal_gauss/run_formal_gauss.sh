#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Formal equivalence of the Gaussian table (B2) with the upstream FIR, plus a
# non-vacuity check: three mutants of the table must each make the proof fail.
#
# Usage (WSL/Linux, repository root):
#   scripts/validation/formal_gauss/run_formal_gauss.sh <label> [ref-rev]
# Output: results/validation/<label>/formal_gauss/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_formal_gauss.sh <label> [ref-rev]}
ref_rev=${2:-upstream-baseline}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
export PATH=$OSS_CAD/bin:$PATH

repo=$(git rev-parse --show-toplevel)
source "$repo/scripts/validation/result_guard.sh"
here=$repo/scripts/validation/formal_gauss
out=$repo/results/validation/$label/formal_gauss
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_fgauss.XXXXXX)

git -C "$repo" show "$ref_rev:verilog/gauss_filter.v" \
  | sed -E 's/\bgauss_filter\b/gauss_filter_ref/g' > "$work/gauss_filter_ref.v"
cp "$repo/verilog/gauss_filter.v" "$here/gauss_miter.sv" "$here/gauss_equiv.sby" "$work/"
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ref_rev=$ref_rev ($(git -C "$repo" rev-parse "$ref_rev^{commit}"))"
  echo "dut=working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
  echo "yosys=$(yosys -V)"
} > "$out/provenance.txt"

status=0
mutant() {  # $1 = name, $2 = sed expression on gauss_filter.v
  local m=$work/mut_$1 r
  mkdir -p "$m"; cp "$work"/*.v "$work"/*.sv "$work"/*.sby "$m/"
  sed -E -i "$2" "$m/gauss_filter.v"
  cmp -s "$work/gauss_filter.v" "$m/gauss_filter.v" && { echo "mutant $1 did not change the file" >&2; exit 1; }
  sby_rc=0
  (cd "$m" && timeout 1800 sby -f gauss_equiv.sby) > "$out/mutant_$1.log" 2>&1 || sby_rc=$?
  r=$(cat "$m/gauss_equiv/status" 2>/dev/null || echo ERROR)
  if ! sby_pass "$sby_rc" "$m/gauss_equiv/status" && ! sby_fail "$sby_rc" "$m/gauss_equiv/status"; then r=ERROR; fi
  echo "mutant $1: ${r%% *}" | tee -a "$out/mutants.txt"
  [ "${r%% *}" == FAIL ] || status=1
}
# mirror taps around the wrong centre
mutant wrong_mirror 's/t = \(pos <= 8\) \? pos : \(16 - pos\);/t = (pos <= 8) ? pos : (15 - pos);/'
# a tap paired with the wrong window position (ble-tx-pdu: the filter's formulation of 2026-10-04)
mutant pair_off_by_one 's/w\[16-e\]/w[15-e]/'
# the sum of the taps added instead of subtracted
mutant wrong_offset_sign 's/\(half_sum <<< 1\) - tap_total\(0\)/(half_sum <<< 1) + tap_total(0)/'

sby_rc=0

(cd "$work" && timeout 3600 sby -f gauss_equiv.sby) > "$out/prove.log" 2>&1 || sby_rc=$?
res=$(cat "$work/gauss_equiv/status" 2>/dev/null || echo ERROR)
if ! sby_pass "$sby_rc" "$work/gauss_equiv/status" && ! sby_fail "$sby_rc" "$work/gauss_equiv/status"; then res=ERROR; fi
echo "prove: $res" | tee -a "$out/result.txt"
[ "${res%% *}" == PASS ] || status=1
cp "$work/gauss_equiv/logfile.txt" "$out/prove_sby_logfile.txt" 2>/dev/null || true
gzip -9 "$out"/*.log "$out"/*_sby_logfile.txt 2>/dev/null || true
[ $status -eq 0 ] && echo "RESULT: PASS" | tee -a "$out/result.txt" || echo "RESULT: FAIL" | tee -a "$out/result.txt"
rm -rf "$work"
exit $status
