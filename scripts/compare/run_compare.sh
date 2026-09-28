#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Cross-branch comparison: area, static timing and switching activity of the
# btle_controller of every branch, each in its own configuration, measured in
# ONE run with the same flows, tools, liberty and stimuli.
#
#   name          RTL (git archive)   configuration (scripts/branch_config.sh)
#   master        upstream-baseline   defaults; master and risc-v-ble have this verilog/ tree
#   ble-tx-table  ble-tx-table        GAUSS_TABLE=1                                   (B2)
#   ble-rx-dm     ble-rx-dm           defaults; the shared demodulator is in the RTL  (B1)
#   ble-opt       ble-opt             ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1  (B1 A1 A2 B2)
#
# Per configuration, with the existing harnesses:
#   area      scripts/area/run_area.sh, all 16 tops           -> results/area/<label>/<name>/
#   timing    scripts/timing/run_sta.sh, the two controllers  -> results/timing/<label>/<name>/
#   activity  scripts/power/run_activity.sh, 5 scenarios, gate-level lockstep against
#             upstream                                        -> results/power/<label>/<name>/
# then scripts/compare/summarize_compare.py -> results/compare/<label>/ (summary.md, data.json).
#
# Every activity run gets the SAME test vectors: the Python generator's noise is
# not seeded, so vectors generated per run would give each configuration a
# different stimulus. They are generated once (example 0, 20 dB, 20 ppm) and
# kept in results/compare/<label>/vectors.tar.gz, so the run can be repeated
# exactly (VEC_DIR=<the extracted directory>).
#
# The upstream side of the timing and activity runs is then the same design on
# the same stimulus in every configuration, so its figures must come out
# identical in all runs, and the "master" configuration must show no difference
# at all. The summary checks both.
#
# Usage (WSL/Linux, repository root):
#   scripts/compare/run_compare.sh <label> [name ...]
# Env: VEC_DIR  reuse this vector set instead of generating one
# A name that is not a local branch is read from origin/<name> (as in a fresh clone).

set -euo pipefail
label=${1:?usage: run_compare.sh <label> [name ...]}
shift
names=("$@"); [ ${#names[@]} -eq 0 ] && names=(master ble-tx-table ble-rx-dm ble-opt)
PY=${PY:-$HOME/venvs/btle/bin/python}
export MPLBACKEND=Agg

repo=$(git rev-parse --show-toplevel)
out=$repo/results/compare/$label
for d in "$out" "$repo/results/area/$label" "$repo/results/timing/$label" "$repo/results/power/$label"; do
  [ -e "$d" ] && { echo "$d exists; choose a new label" >&2; exit 1; }
done
mkdir -p "$out"

branch_ref() {  # branch name -> local branch, else origin/<name>
  if git -C "$repo" rev-parse --verify -q "refs/heads/$1" > /dev/null; then echo "$1"
  elif git -C "$repo" rev-parse --verify -q "refs/remotes/origin/$1" > /dev/null; then echo "origin/$1"
  else echo "no branch $1 (local or origin)" >&2; return 1; fi
}
rev_of() {  # configuration name -> the revision whose verilog/ is measured
  if [ "$1" = master ]; then echo upstream-baseline; else branch_ref "$1"; fi
}
params_of() {  # revision -> its configuration
  local tmp p
  tmp=$(mktemp -d /tmp/btle_cmp.XXXXXX)
  git -C "$repo" archive "$1" verilog | tar -x -C "$tmp"
  p=$(bash "$repo/scripts/branch_config.sh" "$tmp/verilog")
  rm -rf "$tmp"
  echo "$p"
}

declare -A rev params
for n in "${names[@]}"; do
  rev[$n]=$(rev_of "$n")
  params[$n]=$(params_of "${rev[$n]}")
done

# one vector set for every activity run
vec=$(mktemp -d /tmp/btle_cmpvec.XXXXXX)
if [ -n "${VEC_DIR:-}" ]; then
  mkdir -p "$vec/verilog"; cp "$VEC_DIR"/*.txt "$vec/verilog/"
  echo "vectors taken from VEC_DIR=$VEC_DIR" > "$out/gen_vectors.log"
else
  mkdir -p "$vec/verilog"
  git -C "$repo" archive upstream-baseline python | tar -x -C "$vec"
  (cd "$vec/python" && "$PY" test_vector_for_btle_verilog.py 0 20 20 0) > "$out/gen_vectors.log" 2>&1
fi
(cd "$vec/verilog" && sha256sum *.txt) > "$out/vectors.sha256"
tar -C "$vec/verilog" -czf "$out/vectors.tar.gz" $(cd "$vec/verilog" && ls *.txt)

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "harness=$(git -C "$repo" rev-parse HEAD) (branch $(git -C "$repo" rev-parse --abbrev-ref HEAD)), dirty files under scripts/: $(git -C "$repo" status --porcelain -- scripts | wc -l)"
  echo "configurations (name, measured revision, commit, verilog/ tree, parameters):"
  for n in "${names[@]}"; do
    printf '  %s\t%s\t%s\t%s\t%s\n' "$n" "${rev[$n]}" "$(git -C "$repo" rev-parse "${rev[$n]}^{commit}")" \
      "$(git -C "$repo" rev-parse "${rev[$n]}:verilog")" "${params[$n]:-<none: defaults>}"
  done
  echo "activity vectors: example 0, 20 dB, 20 ppm, one set for every configuration; vectors.tar.gz, sha256 of vectors.sha256 $(sha256sum "$out/vectors.sha256" | cut -c1-16)"
  echo "branches with the upstream verilog/ tree ($(git -C "$repo" rev-parse upstream-baseline:verilog)):"
  for b in master risc-v-ble; do
    if r=$(branch_ref "$b" 2> /dev/null); then
      t=$(git -C "$repo" rev-parse "$r:verilog")
      [ "$t" = "$(git -C "$repo" rev-parse upstream-baseline:verilog)" ] && same=yes || same=NO
      printf '  %s\t%s\t%s\tsame_as_upstream=%s\n' "$b" "$r" "$t" "$same"
    fi
  done
} > "$out/provenance.txt"
cat "$out/provenance.txt"

status=0
# area and timing: short, all configurations in parallel
pids=()
for n in "${names[@]}"; do
  ( RTL_REV="${rev[$n]}" AREA_PARAMS="${params[$n]}" bash "$repo/scripts/area/run_area.sh" "$label/$n" ) \
    > "$out/area_$n.log" 2>&1 & pids+=($!)
  ( DUT_REV="${rev[$n]}" DUT_PARAMS="${params[$n]}" STA_SET=controller bash "$repo/scripts/timing/run_sta.sh" "$label/$n" ) \
    > "$out/timing_$n.log" 2>&1 & pids+=($!)
done
for p in "${pids[@]}"; do wait "$p" || status=1; done
echo "area and timing done (status $status)"

# activity: one configuration at a time (each already runs its 6 simulations in parallel)
for n in "${names[@]}"; do
  ( DUT_REV="${rev[$n]}" DUT_PARAMS="${params[$n]}" VEC_DIR="$vec/verilog" \
      bash "$repo/scripts/power/run_activity.sh" "$label/$n" ) > "$out/activity_$n.log" 2>&1 || status=1
  cmp -s "$out/vectors.sha256" "$repo/results/power/$label/$n/vectors.sha256" \
    || { echo "activity $n: not run on the shared vector set" >&2; status=1; }
  ok=0
  for s in rx tx mixed idle idle0; do
    zcat -f "$repo/results/power/$label/$n/run_$s.log"* 2> /dev/null | grep -q 'ACTIVITY RUN PASS' && ok=$((ok+1))
  done
  echo "activity $n done: $ok of 5 scenarios without a mismatch"
done

"$PY" "$repo/scripts/compare/summarize_compare.py" "$repo" "$label" "${names[@]}" > "$out/summary.md" || status=1
gzip -9 "$out"/*.log
rm -rf "$vec"
echo "RESULT: $([ $status -eq 0 ] && echo PASS || echo FAIL)" | tee -a "$out/summary.md"
exit $status
