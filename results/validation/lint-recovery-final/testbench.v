`timescale 1ns/1ps
module lint_recovery_tb;
reg clk=0, rst=1;
always #5 clk=~clk;
wire [7:0] araddr=0;
wire arvalid=0,rready=0,arready,rvalid;
wire [31:0] rdata;wire [1:0] rresp;

btle_rx_core  rx(.clk(clk),.rst(rst),.i(16'd0),.q(16'd0),.iq_valid(1'b0),
 .unique_bit_sequence(32'hD6BE898E),.channel_number(6'd37),.crc_state_init_bit(24'h555555));
  btle_ll ll(.bb_clk(clk),.bb_rst(rst),.axi_aclk(clk),.axi_aresetn(!rst),
    .ref_1pps(1'b0),.uart_rx(1'b1),.tx_iq_valid_last(1'b0),
    .rx_hit_flag(1'b0),.rx_decode_run(1'b0),.rx_decode_end(1'b0),.rx_crc_ok(1'b0),
    .rx_payload_length(8'd0),.rx_pdu_octet_mem_data(8'd0),
    .bram_addr_b_half_flag(1'b0),.bram_addr_b(32'd0),
    .rx_i_signal(16'd0),.rx_q_signal(16'd0),.rx_iq_valid(1'b0),
    .i_abs_add_q_abs(17'd0),.agc_lock_change(1'b0),.agc_lock_state(1'b0),.rf_gain(7'd0),
    .simulation_en(1'b0),.simulation_rx_ram_read_en(1'b0),
    .axi_awaddr(8'd0),.axi_awprot(3'd0),.axi_awvalid(1'b0),
    .axi_wdata(32'd0),.axi_wstrb(4'd0),.axi_wvalid(1'b0),.axi_bready(1'b1),
    .axi_araddr(araddr),.axi_arprot(3'd0),.axi_arvalid(arvalid),.axi_arready(arready),
    .axi_rdata(rdata),.axi_rresp(rresp),.axi_rvalid(rvalid),.axi_rready(rready));
initial begin #10000;$fatal(1,"recovery watchdog");end
initial begin
 repeat(8) @(negedge clk);rst=0;
 repeat(8) @(negedge clk);
 force ll.ll_state=3'd7;
 force rx.phy_rx_state=2'd3;
 rx.octet_valid=1;rx.decode_end=1;rx.crc_ok=1;rx.payload_length_valid=1;
 
 @(negedge clk);
 release ll.ll_state;release rx.phy_rx_state;
 
 @(posedge clk);#1;
 if(ll.ll_state !== 3'd0) $fatal(1,"LL illegal state did not recover");
 if(rx.phy_rx_state !== 2'd0 || rx.octet_valid !== 0 || rx.decode_end !== 0 || rx.crc_ok !== 0 || rx.payload_length_valid !== 0)
   $fatal(1,"RX illegal state did not recover safely");
 
 $display("RECOVERY PASS: 2 illegal state encodings recovered without valid outputs");$finish;
end
endmodule
