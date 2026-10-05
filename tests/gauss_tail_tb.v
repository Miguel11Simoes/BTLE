`timescale 1ns/1ps
module tail_tb;
  reg clk=0; always #5 clk=~clk;
  reg rst=1, source_bit=0, source_valid=0, source_last=0;
  reg [3:0] tap_index=0;
  reg signed [15:0] tap_value=0;
  wire fb,fv,fl,rv,rl,valid,last;
  wire signed [15:0] raw,value;
  btle_gauss_tail adapter(clk,rst,tap_index,tap_value,source_bit,source_valid,source_last,fb,fv,fl,raw,rv,rl,value,valid,last);
  gauss_filter fir(clk,rst,tap_index,tap_value,fb,fv,fl,raw,rv,rl);
  integer n=1, received=0, observed=0, checks=0, j,k,c,trial;
  integer history[0:16];
  reg signed [15:0] taps[0:8];
  reg signed [15:0] expected=0;
  reg expected_valid=0;
  reg [31:0] random_state=32'h2ae437;
  always @(posedge clk) begin
    if (rst) begin
      received=0; observed=0; expected_valid=0;
      for(j=0;j<17;j=j+1) history[j]=-1;
      for(j=0;j<9;j=j+1) taps[j]=0;
    end else begin
      expected_valid=fv;
      if(fv) begin
        for(j=16;j>0;j=j-1) history[j]=history[j-1];
        history[0]=(received<n) ? (fb ? 1 : -1) : 0;
        expected=0;
        for(j=0;j<17;j=j+1) expected=expected+history[j]*$signed(taps[j<=8 ? j : 16-j]);
        received=received+1;
      end
      if(tap_index<9) taps[tap_index]=tap_value;
    end
  end
  always @(negedge clk) begin
    if(!rst) begin
      if(valid !== expected_valid) $fatal(1,"MISMATCH tail valid");
      if(valid) begin
        if(value !== expected) $fatal(1,"MISMATCH tail sample %0d got %0d expected %0d",observed,value,expected);
        if(last !== (observed==n+15)) $fatal(1,"MISMATCH tail end marker at %0d",observed);
        observed=observed+1;checks=checks+1;
      end
    end
  end
  initial begin
    for(trial=0;trial<32;trial=trial+1) begin
      @(negedge clk); #1;rst=1;source_valid=0;source_last=0;n=trial+1;
      repeat(3) @(negedge clk);
      #1;rst=0;
      for(c=0;c<2*n+90;c=c+1) begin
        @(negedge clk);#1;
        random_state=(random_state<<1) ^ (random_state[31] ? 32'h04c11db7 : 0);
        tap_index=c%9;tap_value=random_state[15:0];
        source_valid=(c>=20 && c<20+2*n && (c%2)==0);
        source_last=(c==20+2*(n-1));source_bit=random_state[20];
      end
      @(negedge clk);#1;
      if(observed!==n+16) $fatal(1,"MISMATCH tail sample count %0d expected %0d",observed,n+16);
    end
    $display("TAIL PASS: %0d packet samples, dynamic signed taps including wraparound, 32 lengths",checks);
    $finish;
  end
endmodule
