// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// tag_fsm as a chip would have it (ble-tx-poc-gen): the top of the ASIC flows (area, GF180 layout), with the pins of the tag
// and nothing else: the rate and the sensor, tied on the flexible board; the bus; the radio's samples; AdvA's production
// port. TICK_DIV = 1: clk is the 32.768 kHz clock between packets, and no divider is laid out; the switch to 16 MHz for
// the packet is not designed yet, and the flows time clk at 16 MHz, the harder case.

`timescale 1ns / 1ps
module tag_chip #
(
  parameter integer ADV_ADDRESS_OTP = 0,   // passed to tag_fsm
  parameter integer BCH_T = 8
) (
  input  wire clk,
  input  wire rst,

  input  wire [2:0] rate,
  input  wire [1:0] sel,

  input  wire sda_i,
  output wire scl_oe,
  output wire sda_oe,
  output wire cs_n,

  input  wire [47:0] adv_address_otp_prog,
  output wire adv_address_otp_ready,

  output wire signed [7:0] i,
  output wire signed [7:0] q,
  output wire iq_valid,
  output wire iq_valid_last
);

// the outputs of tag_fsm that a chip does not bring out: only for the FPGA's status registers and debug
wire unused_phy_bit, unused_phy_bit_valid, unused_phy_bit_valid_last;
wire unused_upsample, unused_upsample_valid, unused_upsample_valid_last, unused_gauss_valid, unused_gauss_valid_last;
wire unused_tx_start;
wire signed [15:0] unused_gauss;
wire [15:0] unused_sensor;
wire [47:0] unused_adv_address_sent;

tag_fsm #(
  .TICK_DIV(1),
  .BCH_T(BCH_T),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP)
) tag_fsm_i (
  .clk(clk),
  .rst(rst),
  .rate(rate),
  .sel(sel),
  .test_mode(1'b0),
  .sda_i(sda_i),
  .scl_oe(scl_oe),
  .sda_oe(sda_oe),
  .cs_n(cs_n),
  .adv_address_otp_prog(adv_address_otp_prog),
  .adv_address_otp_ready(adv_address_otp_ready),
  .i(i),
  .q(q),
  .iq_valid(iq_valid),
  .iq_valid_last(iq_valid_last),
  .phy_bit(unused_phy_bit),
  .phy_bit_valid(unused_phy_bit_valid),
  .phy_bit_valid_last(unused_phy_bit_valid_last),
  .bit_upsample(unused_upsample),
  .bit_upsample_valid(unused_upsample_valid),
  .bit_upsample_valid_last(unused_upsample_valid_last),
  .bit_upsample_gauss_filter(unused_gauss),
  .bit_upsample_gauss_filter_valid(unused_gauss_valid),
  .bit_upsample_gauss_filter_valid_last(unused_gauss_valid_last),
  .tx_start(unused_tx_start),
  .sensor(unused_sensor),
  .adv_address_sent(unused_adv_address_sent)
);

endmodule
