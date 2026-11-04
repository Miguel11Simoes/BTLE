// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// The senseworks tag through the controller's AXI-lite registers (baremetal_phy_intf_mode = 0, the
// path the boards use), with the sequence of the tag mode of firmware/btle_ll.c:
//   setup      : Gaussian taps (reg 1), preamble 0xAA (reg 4), access address 0x8E89BED6 (reg 5),
//                CRC init 0x555555 (reg 6)
//   per event  : the sensor's two bytes through the pair (reg 8, PDU addresses 12 and 13); then for
//                channels 37, 38, 39: the channel (reg 7), tx_start pulsed (reg 9: 1, then 0), the
//                end of the packet awaited
// For every packet it writes the samples of btle_phy's output (bb_clk, when tx_iq_valid) and of the
// controller's output to the RF transceiver (tx_iq_signal_ext, rf_clk, when tx_iq_valid_ext) to
// phy_iq.txt and ext_iq.txt ("packet I Q" per line); tests/test_tag_controller.py compares them
// with the Python model. It fails if a pulse of reg 9 gives no packet or more than one.
// Parameters (defines): T (BCH_T), G (GAUSS_TABLE), EVENTS (the number of sensor readings).

`timescale 1ns / 1ps
module tag_controller_tb;

localparam integer RF_IQ_BIT_WIDTH = 64;

reg bb_clk = 1, rf_clk = 0;
always #((1000.0/16.0)/2.0) bb_clk = !bb_clk;
always #((1000.0/8.0)/2.0)  rf_clk = !rf_clk;
reg bb_rst = 1, rf_rst = 1, aresetn = 0;

reg  [7:0] awaddr = 0, araddr = 0;
reg  awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
reg  [31:0] wdata = 0;

wire [15:0] ll_gpio; wire it0, it1, it2, it3, it4, it5, it6, it7;
wire [31:0] bram_rd; wire uart_tx; wire [RF_IQ_BIT_WIDTH-1:0] tx_iq; wire tx_v, tx_vl;
wire awready, wready, bvalid, arready, rvalid; wire [1:0] bresp, rresp; wire [31:0] rdata;
wire x0, x1, x2, x3, x4, x5, x6, x7; wire signed [15:0] gauss; wire r0, r1, r2, r3; wire [2:0] bp;
wire [7:0] len, pdu;

btle_controller #(.GAUSS_TABLE(`G), .BCH_T(`T)) u_dut (
  .rf_clk(rf_clk), .rf_rst(rf_rst), .bb_clk(bb_clk), .bb_rst(bb_rst), .gpio(8'd0),
  .ll_gpio(ll_gpio), .ll_itrpt0(it0), .ll_itrpt1(it1), .ll_itrpt2(it2), .ll_itrpt3(it3),
  .ll_itrpt4(it4), .ll_itrpt5(it5), .ll_itrpt6(it6), .ll_itrpt7(it7),
  .bram_addr_a(17'd0), .bram_clk_a(bb_clk), .bram_wrdata_a(32'd0), .bram_rddata_a(bram_rd),
  .bram_en_a(1'b0), .bram_rst_a(1'b0), .bram_we_a(1'b0),
  .uart_rx(1'b1), .uart_tx(uart_tx), .rf_gpio(8'd0),
  .tx_iq_signal_ext(tx_iq), .tx_iq_valid_ext(tx_v), .tx_iq_valid_last_ext(tx_vl),
  .rx_iq_signal_ext({RF_IQ_BIT_WIDTH{1'b0}}), .rx_iq_valid_ext(1'b1),
  .s00_axi_aclk(bb_clk), .s00_axi_aresetn(aresetn),
  .s00_axi_awaddr(awaddr), .s00_axi_awprot(3'd0), .s00_axi_awvalid(awvalid), .s00_axi_awready(awready),
  .s00_axi_wdata(wdata), .s00_axi_wstrb(4'hF), .s00_axi_wvalid(wvalid), .s00_axi_wready(wready),
  .s00_axi_bresp(bresp), .s00_axi_bvalid(bvalid), .s00_axi_bready(bready),
  .s00_axi_araddr(araddr), .s00_axi_arprot(3'd0), .s00_axi_arvalid(arvalid), .s00_axi_arready(arready),
  .s00_axi_rdata(rdata), .s00_axi_rresp(rresp), .s00_axi_rvalid(rvalid), .s00_axi_rready(rready),
  .baremetal_phy_intf_mode(1'b0),
  .ext_tx_gauss_filter_tap_index(4'd15), .ext_tx_gauss_filter_tap_value(16'd0),
  .ext_tx_cos_table_write_address(11'd0), .ext_tx_cos_table_write_data(8'd0),
  .ext_tx_sin_table_write_address(11'd0), .ext_tx_sin_table_write_data(8'd0),
  .ext_tx_preamble(8'd0), .ext_tx_access_address(32'd0), .ext_tx_crc_state_init_bit(24'd0),
  .ext_tx_crc_state_init_bit_load(1'b0), .ext_tx_channel_number(6'd0), .ext_tx_channel_number_load(1'b0),
  .ext_tx_pdu_octet_mem_data(8'd0), .ext_tx_pdu_octet_mem_addr(9'd0), .ext_tx_start(1'b0),
  .ext_tx_phy_bit(x0), .ext_tx_phy_bit_valid(x1), .ext_tx_phy_bit_valid_last(x2),
  .ext_tx_bit_upsample(x3), .ext_tx_bit_upsample_valid(x4), .ext_tx_bit_upsample_valid_last(x5),
  .ext_tx_bit_upsample_gauss_filter(gauss), .ext_tx_bit_upsample_gauss_filter_valid(x6),
  .ext_tx_bit_upsample_gauss_filter_valid_last(x7),
  .ext_rx_unique_bit_sequence(32'd0), .ext_rx_channel_number(6'd0), .ext_rx_crc_state_init_bit(24'd0),
  .ext_rx_hit_flag(r0), .ext_rx_decode_run(r1), .ext_rx_decode_end(r2), .ext_rx_crc_ok(r3),
  .ext_rx_best_phase(bp), .ext_rx_payload_length(len), .ext_rx_pdu_octet_mem_addr(9'd0),
  .ext_rx_pdu_octet_mem_data(pdu)
);

initial begin #2000000000; $fatal(1, "watchdog timeout"); end

task idle(input integer n); integer t; begin for (t=0; t<n; t=t+1) @(posedge bb_clk); end endtask

task axi_write(input [5:0] reg_idx, input [31:0] value);
  begin
    #1 awaddr = {reg_idx, 2'b00}; wdata = value; awvalid = 1; wvalid = 1;
    @(posedge bb_clk); while (!(awready && wready)) @(posedge bb_clk);
    #1 awvalid = 0; wvalid = 0; bready = 1;
    @(posedge bb_clk); while (!bvalid) @(posedge bb_clk);
    #1 bready = 0;
  end
endtask

// the samples of every packet
wire phy_v = u_dut.btle_phy_i.tx_iq_valid;
wire phy_vl = u_dut.btle_phy_i.tx_iq_valid_last;
wire signed [7:0] phy_i = u_dut.btle_phy_i.tx_i_signal;
wire signed [7:0] phy_q = u_dut.btle_phy_i.tx_q_signal;
integer fd_phy, fd_ext, fd_bits, fd_gauss, packet = 0, packets_ended = 0, phy_samples = 0, ext_samples = 0;
reg capture = 0;
always @(posedge bb_clk) begin
  if (!bb_rst && (phy_v === 1'bx || (phy_v && (^{phy_i, phy_q}) === 1'bx))) $fatal(1, "UNKNOWN TX sample");
  if (phy_v) begin
    if (!capture) $fatal(1, "a TX sample outside a pulse's packet (packet %0d)", packet);
    $fdisplay(fd_phy, "%0d %0d %0d", packet, phy_i, phy_q);
    phy_samples = phy_samples + 1;
  end
  if (phy_vl) packets_ended = packets_ended + 1;
  // the bits sent and the Gaussian filter's output (independent of the VCO's phase, which carries
  // over from one packet to the next)
  if (u_dut.btle_phy_i.tx_phy_bit_valid)
    $fdisplay(fd_bits, "%0d %0d", packet, u_dut.btle_phy_i.tx_phy_bit);
  if (u_dut.btle_phy_i.tx_bit_upsample_gauss_filter_valid)
    $fdisplay(fd_gauss, "%0d %0d", packet, u_dut.btle_phy_i.tx_bit_upsample_gauss_filter);
end
always @(posedge rf_clk) begin
  if (tx_v) begin
    if (!capture) $fatal(1, "an RF sample outside a pulse's packet (packet %0d)", packet);
    $fdisplay(fd_ext, "%0d %0d %0d", packet, $signed(tx_iq[15:0]), $signed(tx_iq[31:16]));
    ext_samples = ext_samples + 1;
  end
end

reg [7:0] sensors [0:2*`EVENTS-1];
integer taps [0:8];
integer e, c, k, ended;
initial begin
  $readmemh("sensors.hex", sensors);
  $readmemh("taps.hex", taps);
  fd_phy = $fopen("phy_iq.txt", "w");
  fd_ext = $fopen("ext_iq.txt", "w");
  fd_bits = $fopen("phy_bits.txt", "w");
  fd_gauss = $fopen("gauss.txt", "w");
  idle(20);
  aresetn = 1; bb_rst = 0; rf_rst = 0;
  idle(20);
  axi_write(0, 32'h8000);                          // reset the counters, as btle_ll.c does
  axi_write(0, 32'h0);
  for (k = 0; k < 9; k = k + 1) axi_write(1, (k << 16) | (taps[k] & 16'hffff));
  axi_write(1, 15 << 16);
  axi_write(4, 32'haa);
  axi_write(5, 32'h8e89bed6);
  axi_write(6, 32'h555555);
  for (e = 0; e < `EVENTS; e = e + 1) begin
    axi_write(8, (12 << 16) | sensors[2*e]);
    axi_write(8, (13 << 16) | sensors[2*e+1]);
    for (c = 37; c <= 39; c = c + 1) begin
      axi_write(7, c);
      idle(4);
      capture = 1;
      ended = packets_ended;
      axi_write(9, 1);
      axi_write(9, 0);
      while (packets_ended == ended) @(posedge bb_clk);
      idle(16);                                    // the last RF samples
      capture = 0;
      idle(8000);                                  // 500 us: no second packet may start
      packet = packet + 1;
    end
  end
  $fclose(fd_phy);
  $fclose(fd_ext);
  $fclose(fd_bits);
  $fclose(fd_gauss);
  if (packets_ended != 3 * `EVENTS) $fatal(1, "%0d packets ended, expected %0d", packets_ended, 3 * `EVENTS);
  $display("PASS: %0d packets, %0d PHY samples, %0d RF samples", packet, phy_samples, ext_samples);
  $finish;
end

endmodule
