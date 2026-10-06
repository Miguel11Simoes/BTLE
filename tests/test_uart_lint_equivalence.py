"""Compare UART behavior with a pinned pre-lint revision, including async reset."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('uart_frame_rx', 'uart_frame_tx', 'rx_clk_gen', 'tx_clk_gen')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    cad = Path(os.environ.get('OSS_CAD', str(Path.home()/'eda/oss-cad-suite-20260907')))/'bin'
    rows = []
    hashes = {}
    with tempfile.TemporaryDirectory(prefix='btle-uart-lint-') as temp:
        work = Path(temp)
        files = []
        for name in NAMES:
            original = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{a.reference}:verilog/{name}.v']).decode()
            hashes[name] = dict(reference=hashlib.sha256(original.encode()).hexdigest(),
                               current=hashlib.sha256((ROOT/'verilog'/f'{name}.v').read_bytes()).hexdigest())
            for other in NAMES:
                original = re.sub(r'\b'+other+r'\b', other+'_ref', original)
            ref = work/(name+'_ref.v')
            ref.write_text(original)
            files += [str(ref), str(ROOT/'verilog'/f'{name}.v')]
        cases = [(width, 'NONE') for width in range(5, 10)] + [(width, parity) for width in (5, 8) for parity in ('ODD', 'EVEN')]
        for width, parity in cases:
            tb = work/'tb.v'
            tb.write_text('''`timescale 1ns/1ps
module tb;
localparam WIDTH=WIDTH_VALUE;
reg clk=0,rst_n=0,en=0;
reg [WIDTH-1:0] data=0;
reg [31:0] random_bits=32'h12345678;
always #5 clk=~clk;
wire tx,tx_ref,done,done_ref,rx_done,rx_done_ref,error,error_ref;
wire [WIDTH-1:0] frame,frame_ref;
uart_frame_tx #(.CLK_FREQUENCE(1000000),.BAUD_RATE(10000),.FRAME_WD(WIDTH),.PARITY("PARITY_VALUE")) t
 (.clk(clk),.rst_n(rst_n),.frame_en(en),.data_frame(data),.uart_tx(tx),.tx_done(done));
uart_frame_tx_ref #(.CLK_FREQUENCE(1000000),.BAUD_RATE(10000),.FRAME_WD(WIDTH),.PARITY("PARITY_VALUE")) tr
 (.clk(clk),.rst_n(rst_n),.frame_en(en),.data_frame(data),.uart_tx(tx_ref),.tx_done(done_ref));
uart_frame_rx #(.CLK_FREQUENCE(1000000),.BAUD_RATE(10000),.FRAME_WD(WIDTH),.PARITY("PARITY_VALUE")) r
 (.clk(clk),.rst_n(rst_n),.uart_rx(tx_ref),.rx_frame(frame),.rx_done(rx_done),.frame_error(error));
uart_frame_rx_ref #(.CLK_FREQUENCE(1000000),.BAUD_RATE(10000),.FRAME_WD(WIDTH),.PARITY("PARITY_VALUE")) rr
 (.clk(clk),.rst_n(rst_n),.uart_rx(tx_ref),.rx_frame(frame_ref),.rx_done(rx_done_ref),.frame_error(error_ref));
integer cycle,checks=0,transmits=0,receives=0,resets=0;
initial begin #500000;$fatal(1,"UART watchdog");end
initial begin
 repeat(4) @(negedge clk);rst_n=1;
 for(cycle=0;cycle<40000;cycle=cycle+1) begin
   @(negedge clk);
   if ((^{tx,done,frame,rx_done,error}) === 1'bx) $fatal(1,"UART unknown output");
   if ({tx,done,frame,rx_done,error} !== {tx_ref,done_ref,frame_ref,rx_done_ref,error_ref})
     $fatal(1,"UART mismatch cycle %0d",cycle);
   checks=checks+1;transmits=transmits+done;receives=receives+rx_done;
   random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
   en=(cycle%1500==20);data=random_bits[WIDTH-1:0];
   if(cycle==7000 || cycle==19000 || cycle==30000) begin
     #2;rst_n=0;en=0;#1;
     if({tx,done,frame,rx_done,error} !== {tx_ref,done_ref,frame_ref,rx_done_ref,error_ref})
       $fatal(1,"UART asynchronous reset mismatch");
     if(tx !== 1 || done !== 0 || rx_done !== 0) $fatal(1,"UART reset failed to assert asynchronously");
     @(negedge clk);#2;rst_n=1;resets=resets+1;
   end
 end
 if(checks!=40000 || transmits<10 || receives<5 || resets!=3) $fatal(1,"UART insufficient coverage");
 $display("UART PASS checks=%0d tx=%0d rx=%0d resets=%0d",checks,transmits,receives,resets);$finish;
end
endmodule
'''.replace('WIDTH_VALUE', str(width)).replace('PARITY_VALUE', parity))
            binary = work/'sim'
            build = subprocess.run([str(cad/'iverilog'), '-g2012', '-s', 'tb', '-o', str(binary), str(tb), *files], capture_output=True, text=True, timeout=30)
            if build.returncode:
                raise RuntimeError(build.stderr)
            run = subprocess.run([str(cad/'vvp'), '-n', str(binary)], capture_output=True, text=True, timeout=30)
            log = run.stdout+run.stderr
            (a.output/f'{width}-{parity}.log').write_text(log)
            verdicts = re.findall(r'^UART PASS checks=(\d+) tx=(\d+) rx=(\d+) resets=(\d+)$', log, re.M)
            if run.returncode or len(verdicts) != 1 or 'FATAL' in log or 'ERROR' in log:
                raise RuntimeError(log)
            checks, tx, rx, resets = map(int, verdicts[0])
            rows.append(dict(width=width, parity=parity, checks=checks, transmits=tx, receives=rx, resets=resets, status='PASS'))
    (a.output/'result.json').write_text(json.dumps(dict(status='PASS', reference=a.reference, source_sha256=hashes, cases=rows), indent=2)+'\n')
    print(f'PASS: {len(rows)} UART configurations, {sum(r["checks"] for r in rows)} checked cycles')


if __name__ == '__main__':
    main()
