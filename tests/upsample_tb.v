`timescale 1ns/1ps
module upsample_tb;
  reg clk=0,rst=1,bit_in=0,valid_in=0,last_in=0;
  always #5 clk=~clk;
  wire bit_out,valid_out,last_out;
  bit_repeat_upsample dut(clk,rst,bit_in,valid_in,last_in,bit_out,valid_out,last_out);
  reg expected_bit[0:65535],expected_last[0:65535];
  integer sent=0,seen=0,markers=0,tick=0,last_tick=-2;
  integer packet,n,b,k;
  always @(negedge clk) begin
    tick=tick+1;
    if(!rst && valid_out) begin
      if(seen>=sent || bit_out !== expected_bit[seen] || last_out !== expected_last[seen])
        $fatal(1,"upsample mismatch at sample %0d",seen);
      if(tick-last_tick<2) $fatal(1,"sample spacing violates VCO contract");
      last_tick=tick;seen=seen+1;
      if(last_out) markers=markers+1;
    end
  end
  initial begin #10000000;$fatal(1,"upsample watchdog");end
  initial begin
    repeat(4) @(posedge clk);#1 rst=0;
    for(packet=0;packet<64;packet=packet+1) begin
      repeat(packet%32) @(posedge clk);
      n=1+packet%7;
      for(b=0;b<n;b=b+1) begin
        @(posedge clk);#1;
        bit_in=(packet+b)%2;valid_in=1;last_in=(b==n-1);
        for(k=0;k<8;k=k+1) begin
          expected_bit[sent]=bit_in;expected_last[sent]=last_in && k==7;sent=sent+1;
        end
        @(posedge clk);#1 valid_in=0;last_in=0;
        repeat(14) @(posedge clk);
      end
      repeat(3) @(posedge clk);#1;
      if(seen!=sent || markers!=packet+1) $fatal(1,"packet not drained");
    end
    $display("UPSAMPLE PASS: 64 packets, %0d samples, gaps 0..31 clocks",seen);$finish;
  end
endmodule
