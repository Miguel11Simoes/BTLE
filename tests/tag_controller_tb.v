// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// The tag of ble-tx-poc-tmp100 in the controller (the boards' path): btle_controller with the TMP100 on its I2C bus. Off
// until the one write of the firmware, the rate (register 7); no packet before it. Through the AXI-lite registers
// the test then only reads the tag's state (registers 42 to 46, after each packet), and writes what the firmware of the
// earlier branches wrote to send a packet (registers 4 to 6, 8 and 9), which must now change nothing.
// For every packet it writes the samples of btle_phy's output (bb_clk, when tx_iq_valid) and of the controller's
// output to the RF transceiver (tx_iq_signal_ext, rf_clk, when tx_iq_valid_ext) to phy_iq.txt and ext_iq.txt
// ("packet I Q" per line), and the registers to status.txt; tests/test_tag_controller.py checks them.
// Defines: T (BCH_T), TICK_DIV (TAG_TICK_DIV), EVENTS (the packets), CH (TAG_CHANNEL), RATE (the rate written).

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

tri1 scl, sda;
wire scl_oe, sda_oe;
assign scl = scl_oe ? 1'b0 : 1'bz;
assign sda = sda_oe ? 1'b0 : 1'bz;
tmp100_model tmp100_i (.scl(scl), .sda(sda), .present(1'b1));

btle_controller #(.BCH_T(`T), .TAG_TICK_DIV(`TICK_DIV), .TAG_CHANNEL(`CH)) u_dut (
  .rf_clk(rf_clk), .rf_rst(rf_rst), .bb_clk(bb_clk), .bb_rst(bb_rst), .gpio(8'd0),
  .ll_gpio(ll_gpio), .ll_itrpt0(it0), .ll_itrpt1(it1), .ll_itrpt2(it2), .ll_itrpt3(it3),
  .ll_itrpt4(it4), .ll_itrpt5(it5), .ll_itrpt6(it6), .ll_itrpt7(it7),
  .bram_addr_a(17'd0), .bram_clk_a(bb_clk), .bram_wrdata_a(32'd0), .bram_rddata_a(bram_rd),
  .bram_en_a(1'b0), .bram_rst_a(1'b0), .bram_we_a(1'b0),
  .uart_rx(1'b1), .uart_tx(uart_tx),
  .tag_sda_i(sda), .tag_scl_oe(scl_oe), .tag_sda_oe(sda_oe),
  .rf_gpio(8'd0),
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

integer fd_phy, fd_ext, fd_bits, fd_gauss, fd_status, packet = 0, packets_ended = 0, phy_samples = 0, ext_samples = 0;

initial begin #40000000000; $display("MISMATCH watchdog: %0d packets", packets_ended); $fatal(1, "watchdog timeout"); end

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

reg [31:0] read_value;
task axi_read(input [5:0] reg_idx);
  begin
    #1 araddr = {reg_idx, 2'b00}; arvalid = 1;
    @(posedge bb_clk); while (!arready) @(posedge bb_clk);
    #1 arvalid = 0; rready = 1;
    @(posedge bb_clk); while (!rvalid) @(posedge bb_clk);
    read_value = rdata;
    #1 rready = 0;
  end
endtask

// the samples of every packet
wire phy_v = u_dut.btle_phy_i.tx_iq_valid;
wire phy_vl = u_dut.btle_phy_i.tx_iq_valid_last;
wire signed [7:0] phy_i = u_dut.btle_phy_i.tx_i_signal;
wire signed [7:0] phy_q = u_dut.btle_phy_i.tx_q_signal;
always @(posedge bb_clk) begin
  if (!bb_rst && (phy_v === 1'bx || (phy_v && (^{phy_i, phy_q}) === 1'bx))) begin
    $display("MISMATCH unknown TX sample");
    $fatal(1, "unknown");
  end
  if (phy_v) begin
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
    $fdisplay(fd_ext, "%0d %0d %0d", packet, $signed(tx_iq[15:0]), $signed(tx_iq[31:16]));
    ext_samples = ext_samples + 1;
  end
end

integer ended, reg_idx;
initial begin
  fd_phy = $fopen("phy_iq.txt", "w");
  fd_ext = $fopen("ext_iq.txt", "w");
  fd_bits = $fopen("phy_bits.txt", "w");
  fd_gauss = $fopen("gauss.txt", "w");
  fd_status = $fopen("status.txt", "w");
  idle(20);
  aresetn = 1; bb_rst = 0; rf_rst = 0;
  idle(20);
  // off: no packet, nothing on the bus, for longer than a period
  idle(`TICK_DIV * 40000);
  if (packets_ended != 0 || phy_samples != 0) begin
    $display("MISMATCH %0d packets with the rate at 0", packets_ended);
    $fatal(1, "off");
  end
  // what the firmware of the earlier branches wrote to send a packet: no effect now
  axi_write(4, 32'h55);
  axi_write(5, 32'h12345678);
  axi_write(6, 32'h0);
  axi_write(8, (12 << 16) | 8'h5A);
  axi_write(9, 1);
  axi_write(9, 0);
  idle(`TICK_DIV * 100);
  if (packets_ended != 0 || phy_samples != 0) begin
    $display("MISMATCH %0d packets after the old writes", packets_ended);
    $fatal(1, "off");
  end
  axi_write(7, `RATE);                             // the firmware's one write: the tag starts
  while (packet < `EVENTS) begin
    ended = packets_ended;
    while (packets_ended == ended) @(posedge bb_clk);
    idle(16);                                      // the last RF samples
    idle(64);                                      // the counters through the clock crossing
    $fwrite(fd_status, "%0d", packet);
    for (reg_idx = 42; reg_idx <= 46; reg_idx = reg_idx + 1) begin
      axi_read(reg_idx);
      $fwrite(fd_status, " %08x", read_value);
    end
    $fwrite(fd_status, "\n");
    if (packet == 1) begin
      axi_write(9, 1);                             // a pulse of the old tx_start between two packets
      axi_write(9, 0);
    end
    packet = packet + 1;
  end
  $fclose(fd_phy);
  $fclose(fd_ext);
  $fclose(fd_bits);
  $fclose(fd_gauss);
  $fclose(fd_status);
  $display("PASS: %0d packets, %0d PHY samples, %0d RF samples", packet, phy_samples, ext_samples);
  $finish;
end

endmodule
