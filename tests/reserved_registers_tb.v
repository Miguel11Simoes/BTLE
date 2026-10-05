`timescale 1ns/1ps
module reserved_registers_tb;
  reg bb_clk=0, axi_clk=0, rst=1;
  always #5 bb_clk=~bb_clk;
  always #7 axi_clk=~axi_clk;
  reg [7:0] araddr=0;
  reg arvalid=0, rready=0;
  wire arready, rvalid;
  wire [31:0] rdata;
  wire [1:0] rresp;
  btle_ll dut(.bb_clk(bb_clk),.bb_rst(rst),.axi_aclk(axi_clk),.axi_aresetn(!rst),
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
  integer k,reads=0;
  task read_zero(input [5:0] index);
    begin
      @(negedge axi_clk);araddr={index,2'b00};arvalid=1;
      @(posedge axi_clk);while(arready !== 1'b1) @(posedge axi_clk);
      @(negedge axi_clk);arvalid=0;
      @(posedge axi_clk);while(rvalid !== 1'b1) @(posedge axi_clk);
      // Hold the response under backpressure and require known, stable zeros.
      repeat(3) begin
        if(rdata !== 32'd0 || rresp !== 2'd0 || rvalid !== 1'b1)
          $fatal(1,"reserved read %0d is not known zero: %h",index,rdata);
        @(posedge axi_clk);
      end
      @(negedge axi_clk);rready=1;
      @(negedge axi_clk);rready=0;reads=reads+1;
    end
  endtask
  initial begin #100000; $fatal(1,"reserved read watchdog"); end
  initial begin
    repeat(8) @(negedge axi_clk);rst=0;
    repeat(40) @(negedge axi_clk);
    for(k=42;k<=47;k=k+1) read_zero(k);
    read_zero(54);
    if(reads!=7) $fatal(1,"missing reserved reads");
    $display("READBACK PASS: 7 reserved registers, independent clocks, backpressure");$finish;
  end
endmodule
