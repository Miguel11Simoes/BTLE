// Contract test for the supported related 2:1 RF/baseband clocks.
`timescale 1ns/1ps
module tb_clock_domain_contract;
reg bb_clk=0, rf_clk=0, bb_rst=1, rf_rst=1;
always #5 bb_clk=~bb_clk;
integer phase_ps=1250;
initial begin
  if (!$value$plusargs("phase_ps=%d",phase_ps)) phase_ps=1250;
  #(phase_ps/1000.0);
  forever #10 rf_clk=~rf_clk;
end
reg [63:0] iq=0;
reg valid=0;
reg [7:0] gpio=0;
wire signed [15:0] ri,rq;
wire rv;
wire [7:0] bg;
wire [63:0] tiq;
wire tv,tl;
clock_domain_conversion_iq dut(.rf_clk(rf_clk),.rf_rst(rf_rst),.bb_clk(bb_clk),.bb_rst(bb_rst),
 .rf_gpio(gpio),.rx_iq_signal_ext(iq),.rx_iq_valid_ext(valid),.rx_i_signal(ri),.rx_q_signal(rq),.rx_iq_valid(rv),.bb_gpio(bg),
 .tx_i_signal(8'sd0),.tx_q_signal(8'sd0),.tx_iq_valid(1'b0),.tx_iq_valid_last(1'b0),
 .tx_iq_signal_ext(tiq),.tx_iq_valid_ext(tv),.tx_iq_valid_last_ext(tl));
integer mode=0, source_cycle=0, cycle=0, checked=0, accepted=0, quiet=0;
integer expected_valid;
reg [15:0] expected_i,expected_q;
always @(posedge bb_clk) begin
 if (bb_rst) cycle=0;
 else begin
  cycle=cycle+1;
  expected_valid=((cycle%2)==1) && valid;
  expected_i=iq[15:0];expected_q=iq[31:16];
  #1;
  if (rv !== (expected_valid!=0)) $fatal(1,"RX valid contract: cycle %0d ext %b got %b expected %b",cycle,valid,rv,(expected_valid!=0));
  if (rv && (ri !== expected_i || rq !== expected_q)) $fatal(1,"RX data contract: wrong I/Q sample");
  if (tv !== 1'b0 || tl !== 1'b0) $fatal(1,"inactive TX produced a valid output");
  checked=checked+1;
  if (rv) accepted=accepted+1;
  if (!valid) quiet=quiet+1;
 end
end
initial begin
 if (!$value$plusargs("mode=%d",mode)) mode=0;
 repeat(4) @(negedge bb_clk);
 valid=(mode==1);
 bb_rst=0;rf_rst=0;
 for(source_cycle=0;source_cycle<240;source_cycle=source_cycle+1) begin
  @(negedge rf_clk);
  valid <= (mode==1) || (mode==2 && ((source_cycle%17)<9));
  iq <= {32'd0,16'(source_cycle*37),16'(source_cycle*73)};
  gpio <= source_cycle;
  if(source_cycle==117) begin
   @(negedge bb_clk);bb_rst=1;rf_rst=1;
   repeat(3) @(negedge bb_clk);
   bb_rst=0;rf_rst=0;
  end
 end
 @(negedge bb_clk);
 if(checked<400 || (mode==0 && accepted!=0) || (mode!=0 && accepted<80) || (mode==2 && quiet<100)) $fatal(1,"insufficient contract coverage");
 $display("CLOCK CONTRACT PASS mode %0d phase_ps %0d checked %0d accepted %0d quiet %0d",mode,phase_ps,checked,accepted,quiet);
 $finish;
end
initial begin #100000; $fatal(1,"clock contract timeout");end
endmodule
