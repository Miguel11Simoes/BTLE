#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The validation of a senseworks tag branch (ble-tx-tag-*), every check in one run, its logs kept:
#   bch          scripts/senseworks/tag_bch.py --self-test: the code's properties, encoder and decoder
#   galois       scripts/senseworks/check_bch_galois.py: against the galois library (GALOIS_PY, an
#                interpreter that has galois; skipped, and said so, without one)
#   equivalence  tests/test_tx_tag.py --mutants: against ble-tx-min's btle_tx, every output on every clock
#   packets      tests/test_tx_tag_packet.py: the waveforms against upstream's model, loopback, the code
#   scapy        scripts/senseworks/check_tag_scapy.py on those packets (SCAPY_PY, an interpreter with scapy)
#   controller   tests/test_tag_controller.py: through the registers, as the firmware writes them
#   lint         scripts/validation/run_lint.py (Verilator 5.020 in /usr/bin, as the audit)
#
# Usage (WSL/Linux, repository root): scripts/senseworks/run_tag_validation.sh <label>
# Output: results/validation/<label>/ (refuses to overwrite): one log per check, summary.txt.
set -uo pipefail
label=${1:?usage: run_tag_validation.sh <label>}
repo=$(git rev-parse --show-toplevel)
out=$repo/results/validation/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
PY=${PY:-$HOME/venvs/btle/bin/python}
GALOIS_PY=${GALOIS_PY:-$HOME/venvs/bchref/bin/python}
SCAPY_PY=${SCAPY_PY:-$GALOIS_PY}
export PATH=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}/bin:$PATH
cd "$repo"
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "commit=$(git rev-parse HEAD) dirty=$(git status --porcelain -- verilog tests scripts | wc -l)"
  echo "branch=$(git rev-parse --abbrev-ref HEAD)"
  echo "python=$($PY --version 2>&1) iverilog=$(iverilog -V 2>&1 | head -1)"
  echo "verilator=$(/usr/bin/verilator --version 2>&1)"
} > "$out/provenance.txt"

status=0
check() {   # check <name> <command...>: its log, its last line in summary.txt
  local name=$1; shift
  if "$@" > "$out/$name.log" 2>&1; then r=PASS; else r=FAIL; status=1; fi
  printf '%-12s %s: %s\n' "$name" "$r" "$(grep -v '^\s*$' "$out/$name.log" | tail -1)" | tee -a "$out/summary.txt"
}
check bch "$PY" scripts/senseworks/tag_bch.py --self-test --trials 2000
if "$GALOIS_PY" -c "import galois" 2>/dev/null; then
  check galois env NUMBA_NUM_THREADS=2 "$GALOIS_PY" -u scripts/senseworks/check_bch_galois.py --trials 60
else
  echo "galois       SKIPPED: no interpreter with galois (GALOIS_PY)" | tee -a "$out/summary.txt"
fi
check equivalence "$PY" tests/test_tx_tag.py --mutants
check packets "$PY" tests/test_tx_tag_packet.py --output "$out/packets.json"
if "$SCAPY_PY" -c "import scapy" 2>/dev/null; then
  check scapy "$SCAPY_PY" scripts/senseworks/check_tag_scapy.py "$out/packets.json"
else
  echo "scapy        SKIPPED: no interpreter with scapy (SCAPY_PY)" | tee -a "$out/summary.txt"
fi
check controller "$PY" tests/test_tag_controller.py --events 3
check lint env PATH=/usr/bin:$PATH python3 scripts/validation/run_lint.py --output "$out/lint"
gzip -9 "$out"/*.log
exit $status
