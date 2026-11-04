#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Static timing of the mapped netlists (Nangate45), upstream vs a branch in its
# configuration, with the same synthesis flow as the area runs.
#
#   1. synth -flatten, dfflibmap, abc -liberty  (as scripts/area/run_area.sh)
#   2. write_blif, then cut the flip-flops and the RAM macros, so what is left
#      is the register-to-register combinational logic (cut_flops_blif.py)
#   3. ABC: order the network, legalise fanout and size the gates
#      (buffer/upsize/dnsize — Yosys leaves no buffer trees), then "stime":
#      worst path delay and the path itself
#   4. period = clock-to-Q + path + setup (worst library values,
#      seq_constraints.py); slack against the target clock
#
# Pre-layout and ideal: no wire RC, no clock tree, no skew/jitter, no OCV, no
# hold checks, no timing for the RAM macros (paths are cut at their pins).
#
# Usage (WSL/Linux, repository root):
#   scripts/timing/run_sta.sh <label> [clock-ns] [ref-rev]
# Env:
#   DUT_REV     time the verilog/ of this git revision instead of the working tree
#   DUT_PARAMS  the dut configuration (default: every reduction its btle_controller
#               declares, switched on; see scripts/branch_config.sh)
#   STA_SET     full (default: the controllers, btle_rx, and each changed block the
#               dut has) | controller (the two controllers only) | tx (the controllers
#               and btle_tx, the reference's with GAUSS_TABLE=1: the senseworks tag)
# Output: results/timing/<label>/ (refuses to overwrite)

set -euo pipefail
label=${1:?usage: run_sta.sh <label> [clock-ns] [ref-rev]}
clk_ns=${2:-62.5}          # 16 MHz baseband clock
ref_rev=${3:-upstream-baseline}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
LIBERTY=${LIBERTY:-$HOME/eda/NangateOpenCellLibrary_typical.lib}
PY=${PY:-$HOME/venvs/btle/bin/python}
export PATH=$OSS_CAD/bin:$PATH
DUT_REV=${DUT_REV:-}
STA_SET=${STA_SET:-full}

repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/timing
out=$repo/results/timing/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_sta.XXXXXX)
mkdir -p "$work/ref"
git -C "$repo" archive "$ref_rev" verilog | tar -x -C "$work/ref"
if [ -n "$DUT_REV" ]; then
  mkdir -p "$work/dut"
  git -C "$repo" archive "$DUT_REV" verilog | tar -x -C "$work/dut"
  dut_rtl=$work/dut/verilog
  dut_desc="$DUT_REV ($(git -C "$repo" rev-parse "$DUT_REV^{commit}"), verilog tree $(git -C "$repo" rev-parse "$DUT_REV:verilog"))"
else
  dut_rtl=$repo/verilog
  dut_desc="working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
fi
DUT_PARAMS=${DUT_PARAMS-$(bash "$repo/scripts/branch_config.sh" "$dut_rtl")}
has() { case " $DUT_PARAMS " in *" $1 "*) return 0;; *) return 1;; esac; }

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ref=$ref_rev ($(git -C "$repo" rev-parse "$ref_rev^{commit}")), default parameters"
  echo "dut=$dut_desc, ${DUT_PARAMS:-default parameters}"
  echo "sta_set=$STA_SET"
  echo "target_clock_ns=$clk_ns"
  echo "yosys=$(yosys -V)"
  echo "abc=$(yosys-abc -c version 2>&1 | head -1)"
  echo "liberty=$(basename "$LIBERTY") sha256=$(sha256sum "$LIBERTY" | cut -d' ' -f1)"
} > "$out/provenance.txt"

# design <name> <rtl dir> <top> [params...]
design() {
  local name=$1 rtl=$2 top=$3; shift 3
  local chp=""; for kv in "$@"; do chp="$chp -chparam ${kv%%=*} ${kv#*=}"; done
  local files
  files=$(cd "$rtl" && ls *.v | grep -v '_tb\.v$' | grep -v '^btle_controller_wrapper' \
          | grep -vx -e sdpram_one_clk.v -e sdpram_two_clk.v -e sdpram_two_clk_xilinx.v \
          | sed "s|^|$rtl/|" | tr '\n' ' ')
  yosys -q -l "$work/$name.yosys.log" -p "
read_verilog -lib $rtl/sdpram_one_clk.v $rtl/sdpram_two_clk.v
read_verilog $files
hierarchy -check -top $top$chp
synth -flatten -top $top
dfflibmap -liberty $LIBERTY
abc -liberty $LIBERTY
opt_clean -purge
write_blif $work/$name.blif
tee -o $out/$name.stat stat -liberty $LIBERTY
"
  $PY "$here/cut_flops_blif.py" "$work/$name.blif" "$work/$name.cut.blif" \
      "$out/$name.cut.txt" "$work/$name.map" "$LIBERTY" >> "$out/$name.cut.txt"
  # topo: ABC needs the nodes ordered before timing.
  # buffer/upsize/dnsize: the Yosys+ABC netlist has no buffer trees, so single
  # nets drive hundreds of loads far past the library's max capacitance, and
  # the unbuffered delay is meaningless. This legalises fanout (max 16) and
  # sizes the gates, as a real flow does. Both delays are reported.
  yosys-abc -c "read_lib -w $LIBERTY; read_blif $work/$name.cut.blif; topo; stime;
                buffer -N 16 -p; upsize; dnsize; print_stats; stime -p" \
      > "$work/$name.stime.txt" 2>&1
  sed -i 's/\x1b\[[0-9;]*m//g' "$work/$name.stime.txt"
  [ "$(grep -cE 'Delay =[[:space:]]*[0-9.]+ ps' "$work/$name.stime.txt")" -ge 2 ] && grep -q "^Start-point = " "$work/$name.stime.txt" || { echo "incomplete ABC timing result: $name" >&2; exit 1; }
  grep -E '^(WireLoad|Path|Start-point)|i/o =' "$work/$name.stime.txt" > "$out/$name.stime.txt"
  # translate the reported path and its end points back to the design's names
  $PY - "$out/$name.stime.txt" "$work/$name.map" > "$out/$name.path.txt" <<'EOF'
import re, sys
txt = open(sys.argv[1]).read()
names = dict(l.split(None, 1) for l in open(sys.argv[2]) if l.strip())
ports = dict(l.split(None, 1) for l in open(sys.argv[2] + '.io') if l.strip())
def port(m):
    return ports.get(f'{m.group(1)}{int(m.group(2))}', m.group(0)).strip()
txt = re.sub(r'\b(pi|po)0*(\d+)\b', port, txt)
print(re.sub(r'\bn(\d+)\b', lambda m: names.get(m.group(0), m.group(0)).strip(), txt))
EOF
  { printf '%s\t' "$name"
    sed -n 's/^Start-point = //p' "$out/$name.path.txt" | tail -1; } >> "$out/endpoints.txt"
  local raw delay flops
  raw=$(grep -oE 'Delay =\s*[0-9.]+ ps' "$out/$name.stime.txt" | head -1 | grep -oE '[0-9.]+')
  delay=$(grep -oE 'Delay =\s*[0-9.]+ ps' "$out/$name.stime.txt" | tail -1 | grep -oE '[0-9.]+')
  flops=$(grep -oE '^  (S?DFF\S*|TLAT\S*): [0-9]+' "$out/$name.cut.txt" | awk -F': ' '{print $1}' | sed 's/^  //' | sort -u | tr '\n' ' ')
  $PY "$here/seq_constraints.py" "$LIBERTY" $flops > "$out/$name.seq.txt"
  local seq_ns
  seq_ns=$(grep sequential_overhead_ns "$out/$name.seq.txt" | awk '{print $2}')
  $PY - "$name" "$raw" "$delay" "$seq_ns" "$clk_ns" >> "$out/summary.tsv" <<'EOF'
import sys
name, raw_ps, delay_ps, seq_ns, clk_ns = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
comb = delay_ps / 1000.0
period = comb + seq_ns
print(f"{name}\t{raw_ps/1000.0:.3f}\t{comb:.3f}\t{seq_ns:.3f}\t{period:.3f}\t{clk_ns - period:.3f}\t{1000.0/period:.1f}")
EOF
  echo "$name -> $(sed -n "s/^Start-point = //p" "$out/$name.path.txt" | tail -1)"
  echo "$name: comb $(echo "$delay" | awk '{printf "%.3f", $1/1000}') ns + seq $seq_ns ns"
}

printf 'design\tunbuffered_ns\tcomb_path_ns\tseq_overhead_ns\tmin_period_ns\tslack_at_target_ns\tfmax_MHz\n' > "$out/summary.tsv"
design ref_controller       "$work/ref/verilog" btle_controller
design dut_controller       "$dut_rtl"          btle_controller $DUT_PARAMS
if [ "$STA_SET" = full ]; then
  design ref_btle_rx          "$work/ref/verilog" btle_rx
  design dut_btle_rx          "$dut_rtl"          btle_rx
  if has LL_MINIMAL=1; then
    design ref_btle_ll          "$work/ref/verilog" btle_ll
    design dut_btle_ll          "$dut_rtl"          btle_ll LL_MINIMAL=1
  fi
  if has GAUSS_TABLE=1; then
    design ref_gauss_filter     "$work/ref/verilog" gauss_filter
    design dut_gauss_filter     "$dut_rtl"          gauss_filter GAUSS_TABLE=1
  fi
  if [ -f "$dut_rtl/gfsk_demodulation_shared.v" ]; then
    design ref_gfsk_demod       "$work/ref/verilog" gfsk_demodulation
    design dut_gfsk_demod_shared "$dut_rtl"         gfsk_demodulation_shared
  fi
elif [ "$STA_SET" = tx ]; then   # the senseworks tag (ble-tx-tag-*): no receiver; the transmitter itself
  design ref_btle_tx          "$work/ref/verilog" btle_tx GAUSS_TABLE=1
  design dut_btle_tx          "$dut_rtl"          btle_tx $DUT_PARAMS
fi

column -t -s $'\t' "$out/summary.tsv" | tee "$out/summary.txt"
gzip -9 "$out"/*.path.txt
rm -rf "$work"
