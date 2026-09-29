#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# SRAM macros generated with OpenRAM in FreePDK45, the process behind the
# Nangate45 library of the area flow, so that their area can be added to the
# std-cell area of a block. The area flow itself counts RAMs in bits only.
#
# A macro is named sram_<ports>_<word bits>x<words>[_m<mask bits>]:
#   ports  1rw    one read/write port
#          1rw1r  one read/write port and one read-only port, each with its
#                 own clock: the macro for the simple dual-port RAMs of the RTL
#                 (sdpram_one_clk, sdpram_two_clk), which write and read in the
#                 same cycle
#   _m<n>  a write mask of one bit per n bits of the word (OpenRAM write_size)
#
# Without macro names, the three banks of the Gaussian tables of branch
# ble-tx-table-sram (run openram-gauss), one 1RW port each, as
# gauss_table_sram uses them:
#   bank A  sram_1rw_32x32  32 words x 32 bits  (both entries of a group-A index)
#   bank B  sram_1rw_16x64  64 words x 16 bits
#   bank C  sram_1rw_16x32  32 words x 16 bits
# The RAMs of the transmitter (run openram-tx):
#   sram_1rw_8x2048 sram_1rw1r_8x2048  a full-wave COS or SIN table of vco.v
#   sram_1rw_8x512  sram_1rw1r_8x512   a quarter-wave table (ble-tx-sin4), and
#                                      the PDU buffer of btle_tx (512 x 8)
# The {cos, sin} table memory of ble-tx-sin8 (run openram-sin8):
#   sram_1rw_16x512_m8 sram_1rw1r_16x512_m8  a {cos, sin} word per quarter-wave
#                                            address, one table written at a time
#
# The layout is OpenRAM's default (supplies routed, pins on the perimeter).
# DRC/LVS are not run and the timing model is analytical: neither changes the
# layout, only the checks and the .lib numbers. The macro size is read from
# the LEF (SIZE x BY y).
#
# Usage (WSL/Linux, repository root): scripts/area/run_openram.sh <label> [macro ...]
# Env: OPENRAM_PY  python with OpenRAM (default ~/venvs/openram/bin/python:
#                  OpenRAM 1.2.48 from PyPI, numpy < 1.25, scipy < 1.12)
# Output: results/area/<label>/ (refuses to overwrite): summary.md, provenance,
#         and per macro the LEF, the .lib and the log (compressed); no GDS.

set -euo pipefail
label=${1:?usage: run_openram.sh <label> [macro ...]}
shift
macros=("$@"); [ ${#macros[@]} -eq 0 ] && macros=(sram_1rw_32x32 sram_1rw_16x64 sram_1rw_16x32)
for m in "${macros[@]}"; do
  [[ $m =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)(_m([0-9]+))?$ ]] || { echo "bad macro name $m" >&2; exit 1; }
done
PY=${OPENRAM_PY:-$HOME/venvs/openram/bin/python}
repo=$(git rev-parse --show-toplevel)
out=$repo/results/area/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_openram.XXXXXX)

unset OPENRAM_HOME
P=$("$PY" -c "import os, importlib.util; print(os.path.dirname(importlib.util.find_spec('openram').origin))")
export OPENRAM_TECH=$P/technology

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git -C "$repo" rev-parse HEAD)"
  echo "openram=$("$PY" -c 'import importlib.metadata as m; print(m.version("openram"))' 2>/dev/null || true) ($P)"
  echo "python=$("$PY" --version 2>&1) numpy=$("$PY" -c 'import numpy; print(numpy.__version__)')"
  echo "tech=freepdk45, nominal corner only, check_lvsdrc=False, analytical_delay=True, layout options default"
  echo "macros=${macros[*]}"
} > "$out/provenance.txt"

macro() {  # $1 = name sram_<ports>_<word bits>x<words>[_m<mask bits>]
  [[ $1 =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)(_m([0-9]+))?$ ]]
  local ports=${BASH_REMATCH[1]} ws=${BASH_REMATCH[2]} nw=${BASH_REMATCH[3]} mask=${BASH_REMATCH[5]}
  local d=$work/$1 nr=0 write_size=""
  [ "$ports" = 1rw1r ] && nr=1
  [ -n "$mask" ] && write_size="write_size = $mask"
  mkdir -p "$d"
  cat > "$d/cfg.py" <<EOF
word_size = $ws
num_words = $nw
$write_size
num_rw_ports = 1
num_r_ports = $nr
num_w_ports = 0
tech_name = "freepdk45"
nominal_corner_only = True
process_corners = ["TT"]
supply_voltages = [1.0]
temperatures = [25]
check_lvsdrc = False
analytical_delay = True
output_path = "$d/out"
output_name = "$1"
EOF
  if (cd "$d" && timeout 3600 "$PY" "$P/sram_compiler.py" cfg.py) > "$out/$1.log" 2>&1 \
       && [ -f "$d/out/$1.lef" ]; then
    cp "$d/out/$1.lef" "$d/out/$1_TT_1p0V_25C.lib" "$out/" 2>/dev/null || true
    read -r w h < <(sed -n 's/^ *SIZE \([0-9.]*\) BY \([0-9.]*\) ;.*/\1 \2/p' "$d/out/$1.lef" | head -1)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$ports" "$ws" "$nw" "$w" "$h" "$mask" >> "$work/sizes.tsv"
    echo "$1: ${w} x ${h} um"
  else
    echo "$1: FAILED (see $1.log)"; return 1
  fi
}

status=0
for m in "${macros[@]}"; do macro "$m" || status=1; done

python3 - "$work/sizes.tsv" "$label" > "$out/summary.md" <<'PYEOF'
import sys
rows = [l.split('\t') for l in open(sys.argv[1]).read().split('\n') if l.strip()]
print(f'# OpenRAM macros, FreePDK45 (run {sys.argv[2]})\n')
print('| Macro | Ports | Words x bits | Bits | Width (um) | Height (um) | Area (um2) | um2 per bit |')
print('|---|---|---|---:|---:|---:|---:|---:|')
for name, ports, ws, nw, w, h, mask in rows:
    bits, area = int(ws) * int(nw), float(w) * float(h)
    ports = ports.upper() + (f', {mask}-bit write mask' if mask else '')
    print(f'| `{name}` | {ports} | {nw} x {ws} | {bits} | {float(w):.3f} | {float(h):.3f} | {area:.1f} | {area/bits:.2f} |')
PYEOF
cat "$out/summary.md"
gzip -9 "$out"/*.log "$out"/*.lib 2>/dev/null || true
rm -rf "$work"
exit $status
