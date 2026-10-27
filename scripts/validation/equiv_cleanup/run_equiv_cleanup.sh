#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The synthesis-warning cleanup of ble-tx-min is the same circuit: btle_tx and btle_controller of the
# working tree against those of <base rev> (the RTL before the cleanup), in each configuration of CONFIGS
# (default: the branch's defaults; GAUSS_TABLE = 1, AdvData in the memory; GAUSS_TABLE = 1 with AdvData in
# flip-flops; GAUSS_TABLE = 1 with the AdvA OTP), Yosys equivalence (equiv_make, equiv_simple -seq 5,
# equiv_induct -seq 5, equiv_status -assert), the RAM models and the eFuse block as blackboxes; and the
# one block the cleanup replaced, the link layer's TX UART, by its own proof (SBY, k-induction). The
# receiver branches' harness (ble-rx-micro), with the configurations.
#
# The memories that are not blackboxes (btle_gauss_tail's 9 runtime taps) are mapped to registers
# (memory, not memory -nomap): equiv_induct has no model of a memory cell.
#
# The base side gets two preparations, each justified on its own:
#   - the .rst() connections of its RAM-model instances (sdpram_one_clk, sdpram_two_clk) removed: the
#     models never read rst (their source), and the cleanup removed the port; both sides then use the
#     working tree's models as blackboxes;
#   - its TX UART instance (btle_ll's uart_frame_tx_i) replaced by the cleanup's constant outputs
#     (uart_tx = 1, tx_done = 0): its frame and enable are slv_reg47, tied to 0, and the SBY proof below
#     shows that uart_frame_tx, from reset with frame_en = 0, holds uart_tx = 1 and tx_done = 0 on every
#     clock, unbounded.
#
# A configuration is name:PARAM=VALUE,...: each PARAM's default set to VALUE in every file of both sides that
# declares it (`hierarchy -chparam` asserts in Yosys 0.68 on these designs).
#
# Usage (WSL/Linux, repository root): scripts/validation/equiv_cleanup/run_equiv_cleanup.sh <label> <base rev>
# Output: results/validation/<label>/equiv_cleanup/ (refuses to overwrite): result.txt, the Yosys logs
set -euo pipefail
CONFIGS=${CONFIGS:-"defaults: table:GAUSS_TABLE=1 flops:GAUSS_TABLE=1,ADV_DATA_FLOPS=1 otp:GAUSS_TABLE=1,ADV_ADDRESS_OTP=1"}
label=${1:?usage: run_equiv_cleanup.sh <label> <base rev>}
base=${2:?the revision before the cleanup}
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
export PATH=$OSS_CAD/bin:$PATH
repo=$(git rev-parse --show-toplevel)
out=$repo/results/validation/$label/equiv_cleanup
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_equiv_cleanup.XXXXXX)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/gold" "$work/gate"
git -C "$repo" archive "$base" verilog | tar -x -C "$work/gold"
cp -r "$repo/verilog" "$work/gate/"

python3 - "$work/gold/verilog" <<'PY'
import os, re, sys
V = sys.argv[1]
inst = re.compile(r'(\bsdpram_(?:one|two)_clk\s*#?\s*\((?:[^;]*?)\)\s*\w+\s*\()(.*?)(\n\);)', re.S)
n_rst = 0
for f in sorted(os.listdir(V)):
    if not f.endswith('.v') or f.endswith('_tb.v') or f.startswith('sdpram_'):
        continue
    p = os.path.join(V, f); t = open(p).read(); k = [0]
    def fix(m):
        body, n = re.subn(r'\n[ \t]*\.rst\([^()]*(?:\([^()]*\))?[^()]*\),[ \t]*(?://[^\n]*)?', '', m.group(2))
        k[0] += n
        return m.group(1) + body + m.group(3)
    t2 = inst.sub(fix, t)
    if k[0]:
        open(p, 'w').write(t2); n_rst += k[0]
p = os.path.join(V, 'btle_ll.v'); t = open(p).read()
m = re.search(r'uart_frame_tx #\(\n  \.CLK_FREQUENCE\(CLK_FREQUENCE\),\n  \.BAUD_RATE\(BAUD_RATE\),\n  \.PARITY\(PARITY\),\n  \.FRAME_WD\(FRAME_WD\)\n\) uart_frame_tx_i \(\n  \.clk\(axi_aclk\),\n  \.rst_n\(axi_aresetn\),\n  \.frame_en\(frame_en\),\n  \.data_frame\(data_frame\),\n  \.tx_done\(tx_done\),\n  \.uart_tx\(uart_tx\)\n\);\n', t)
if not m:
    sys.exit('base: btle_ll.v has no uart_frame_tx_i of the expected form')
t = t[:m.start()] + "reg uart_tx_idle;\nalways @ (posedge axi_aclk) uart_tx_idle <= 1'b1;\nassign uart_tx = uart_tx_idle;\nassign tx_done = 1'b0;\n" + t[m.end():]
open(p, 'w').write(t)
print('base side: %d .rst() connections of RAM-model instances removed; the TX UART instance replaced' % n_rst)
PY

# the eFuse block (ADV_ADDRESS_OTP = 1), a macro: a blackbox, its ports those of tests/efuse_async_mem_1x8_model.v
cat > "$work/efuse_async_mem_1x8_bb.v" <<'EOF'
module efuse_async_mem_1x8 (output ready, input reset_n, output [7:0] out, input [7:0] prog);
endmodule
EOF
lib="$work/gate/verilog/sdpram_one_clk.v $work/gate/verilog/sdpram_two_clk.v $work/efuse_async_mem_1x8_bb.v"
# set_defaults <dir> <PARAM=VALUE,...>: the parameter defaults of one configuration, in a copy
set_defaults() {
  local d=$1 kv
  for kv in ${2//,/ }; do
    local n=$(grep -lE "parameter integer ${kv%%=*} = [0-9]+" "$d"/verilog/*.v | wc -l)
    [ "$n" -gt 0 ] || { echo "${kv%%=*}: declared nowhere" >&2; exit 1; }
    sed -E -i "s/(parameter integer ${kv%%=*} = )[0-9]+/\1${kv#*=}/" "$d"/verilog/*.v
  done
}
files() { ls "$1"/verilog/*.v | grep -v '_tb\.v$\|/sdpram_\|_xilinx\.v$\|btle_controller_wrapper' | tr '\n' ' '; }
rc=0
prove() {  # $1 = top, $2 = configuration name, $3 = its parameters; the copies in $work/c/gold, $work/c/gate
  rm -rf "$work/c"; mkdir -p "$work/c"; cp -r "$work/gold" "$work/gate" "$work/c/"
  [ -z "$3" ] || { set_defaults "$work/c/gold" "$3"; set_defaults "$work/c/gate" "$3"; }
  local n=$1-$2
  cat > "$work/$n.ys" <<EOF
read_verilog -lib $lib
read_verilog $(files "$work/c/gold")
hierarchy -check -top $1
proc; async2sync; flatten; opt_clean; memory; opt_clean
rename $1 gold
design -stash gold
read_verilog -lib $lib
read_verilog $(files "$work/c/gate")
hierarchy -check -top $1
proc; async2sync; flatten; opt_clean; memory; opt_clean
rename $1 gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
EOF
  if yosys -q -l "$work/$n.log" "$work/$n.ys" > /dev/null 2>&1; then
    echo "$1, $2 (${3:-the defaults}): EQUIVALENT ($(grep -o 'Found [0-9]* \$equiv cells' "$work/$n.log" | tail -1); $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' "$work/$n.log" | tail -1))" | tee -a "$out/result.txt"
  else
    echo "$1, $2 (${3:-the defaults}): NOT PROVEN" | tee -a "$out/result.txt"; rc=1
  fi
  gzip -9c "$work/$n.log" > "$out/$n.log.gz"
}
for c in $CONFIGS; do
  for top in btle_tx btle_controller; do prove $top "${c%%:*}" "${c#*:}"; done
done

# the TX UART: from reset with frame_en = 0, uart_tx = 1 and tx_done = 0 on every clock
mkdir -p "$work/uart"; cp "$work/gold/verilog/uart_frame_tx.v" "$work/gold/verilog/tx_clk_gen.v" "$work/uart/"
python3 - "$work/uart/uart_frame_tx.v" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read(); i = t.rindex('endmodule')
inv = """`ifdef FORMAL
// the invariant (this copy only): out of reset, IDLE, the line idle, no tx_done
always @(*) if (rst_n) begin
  assert (cstate == IDLE);
  assert (uart_tx == 1'b1);
  assert (tx_done == 1'b0);
end
`endif
"""
open(p, 'w').write(t[:i] + inv + t[i:])
PY
cat > "$work/uart/uart_hold.sv" <<'EOF'
module uart_hold (input clk);
  reg [3:0] n = 0;
  wire rst_n = (n != 0);            // reset in the first clock
  always @(posedge clk) if (n != 15) n <= n + 1;
  wire tx_done, uart_tx;
  uart_frame_tx #(.CLK_FREQUENCE(100_000_000), .BAUD_RATE(115200), .PARITY("NONE"), .FRAME_WD(8)) dut (
    .clk(clk), .rst_n(rst_n), .frame_en(1'b0), .data_frame(8'd0), .tx_done(tx_done), .uart_tx(uart_tx));
endmodule
EOF
cat > "$work/uart/uart_hold.sby" <<'EOF'
[options]
mode prove
depth 4
[engines]
smtbmc bitwuzla
[script]
read -formal uart_frame_tx.v tx_clk_gen.v uart_hold.sv
prep -top uart_hold
async2sync
[files]
uart_frame_tx.v
tx_clk_gen.v
uart_hold.sv
EOF
if (cd "$work/uart" && sby -f uart_hold.sby > sby.log 2>&1); then
  echo "uart_frame_tx, frame_en = 0 from reset: PASS (uart_tx = 1, tx_done = 0, cstate = IDLE on every clock; k-induction)" | tee -a "$out/result.txt"
else
  echo "uart_frame_tx, frame_en = 0 from reset: FAIL" | tee -a "$out/result.txt"; rc=1
fi
cp "$work/uart/sby.log" "$out/uart_sby.log"
{
  echo "label=$label base=$base ($(git -C "$repo" rev-parse "$base^{commit}")) gate=working tree at $(git -C "$repo" rev-parse HEAD), dirty verilog files: $(git -C "$repo" status --porcelain -- verilog | wc -l)"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "yosys=$(yosys -V)"
} > "$out/provenance.txt"
[ $rc = 0 ] && echo "RESULT: PASS" | tee -a "$out/result.txt" || { echo "RESULT: FAIL" | tee -a "$out/result.txt"; exit 1; }
