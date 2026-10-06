"""Inject illegal controller/RX/CRC state encodings and require safe recovery."""
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    cad = Path(os.environ.get('OSS_CAD', str(Path.home()/'eda/oss-cad-suite-20260907')))/'bin'
    crc_has_state = 'case(crc_state)' in (ROOT/'verilog/crc24.v').read_text()
    extra = '#(.EXTERNAL_DEMOD(0))' if 'parameter integer EXTERNAL_DEMOD' in (ROOT/'verilog/btle_rx_core.v').read_text() else ''
    ll = (ROOT/'tests/reserved_registers_tb.v').read_text().split('  btle_ll dut(')[1].split(');')[0]
    ll = '  btle_ll ll('+ll.replace('bb_clk)', 'clk)').replace('axi_clk)', 'clk)')+');'
    tb = """`timescale 1ns/1ps
module lint_recovery_tb;
reg clk=0, rst=1;
always #5 clk=~clk;
wire [7:0] araddr=0;
wire arvalid=0,rready=0,arready,rvalid;
wire [31:0] rdata;wire [1:0] rresp;
CRC_INSTANCE
btle_rx_core RX_PARAMS rx(.clk(clk),.rst(rst),.i(16'd0),.q(16'd0),.iq_valid(1'b0),
 .unique_bit_sequence(32'hD6BE898E),.channel_number(6'd37),.crc_state_init_bit(24'h555555));
LL_INSTANCE
initial begin #10000;$fatal(1,"recovery watchdog");end
initial begin
 repeat(8) @(negedge clk);rst=0;
 repeat(8) @(negedge clk);
 force ll.ll_state=3'd7;
 force rx.phy_rx_state=2'd3;
 rx.octet_valid=1;rx.decode_end=1;rx.crc_ok=1;rx.payload_length_valid=1;
 CRC_FORCE
 @(negedge clk);
 release ll.ll_state;release rx.phy_rx_state;
 CRC_RELEASE
 @(posedge clk);#1;
 if(ll.ll_state !== 3'd0) $fatal(1,"LL illegal state did not recover");
 if(rx.phy_rx_state !== 2'd0 || rx.octet_valid !== 0 || rx.decode_end !== 0 || rx.crc_ok !== 0 || rx.payload_length_valid !== 0)
   $fatal(1,"RX illegal state did not recover safely");
 CRC_CHECK
 $display("RECOVERY PASS: CHECK_COUNT illegal state encodings recovered without valid outputs");$finish;
end
endmodule
"""
    inst = "crc24 crc(.clk(clk),.rst(rst),.crc_state_init_bit(24'h555555),.crc_state_init_bit_load(1'b0),.info_bit(1'b0),.info_bit_valid(1'b0),.info_bit_valid_last(1'b0));" if crc_has_state else ''
    replaces = {'CRC_INSTANCE': inst, 'RX_PARAMS': extra, 'LL_INSTANCE': ll,
      'CRC_FORCE': "force crc.crc_state=2'd3;crc.info_bit_after_crc24_valid=1;crc.info_bit_after_crc24_valid_last=1;" if crc_has_state else '',
      'CRC_RELEASE': 'release crc.crc_state;' if crc_has_state else '',
      'CRC_CHECK': 'if(crc.crc_state !== 0 || crc.info_bit_after_crc24_valid !== 0 || crc.info_bit_after_crc24_valid_last !== 0) $fatal(1,"CRC illegal state did not recover safely");' if crc_has_state else '',
      'CHECK_COUNT': str(3 if crc_has_state else 2)}
    for key, value in replaces.items():
        tb = tb.replace(key, value)
    (a.output/'testbench.v').write_text(tb)
    with tempfile.TemporaryDirectory(prefix='btle-state-recovery-') as temp:
        binary = Path(temp)/'sim'
        files = [str(f) for f in sorted((ROOT/'verilog').glob('*.v')) if not f.name.endswith('_tb.v') and f.name not in ('btle_controller_wrapper.v', 'sdpram_two_clk_xilinx.v')]
        build = subprocess.run([str(cad/'iverilog'), '-g2012', '-s', 'lint_recovery_tb', '-o', str(binary), str(a.output/'testbench.v'), *files], capture_output=True, text=True, timeout=60)
        (a.output/'compile.log').write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError('recovery compile failed: '+build.stderr)
        run = subprocess.run([str(cad/'vvp'), '-n', str(binary)], capture_output=True, text=True, timeout=30)
        output = run.stdout+run.stderr
        (a.output/'run.log').write_text(output)
        verdict = f"RECOVERY PASS: {3 if crc_has_state else 2} illegal state encodings recovered without valid outputs"
        ok = run.returncode == 0 and output.splitlines().count(verdict) == 1 and not re.search('FATAL|ERROR', output)
        (a.output/'result.json').write_text(json.dumps(dict(status='PASS' if ok else 'FAIL', exit=run.returncode, states=3 if crc_has_state else 2), indent=2)+'\n')
        if not ok:
            raise RuntimeError(output)
        print(verdict)


if __name__ == '__main__':
    main()
