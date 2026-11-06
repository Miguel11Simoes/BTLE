// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// The chip of ble-tx-poc-tmp100, the top of the ASIC flows (area, GF180 layout): tag_chip_rate.v with the period fixed at
// 1 s, no pins for it: their pads cost far more than the logic (docs/Senseworks/TX_POC_TMP100.md).

`timescale 1ns / 1ps
module tag_chip #
(
  parameter integer ADV_ADDRESS_OTP = 0,   // passed to tag_fsm
  parameter integer BCH_T = 8
) (
  input  wire clk,
  input  wire rst,

  input  wire sda_i,
  output wire scl_oe,
  output wire sda_oe,

  input  wire [47:0] adv_address_otp_prog,
  output wire adv_address_otp_ready,

  output wire signed [7:0] i,
  output wire signed [7:0] q,
  output wire iq_valid,
  output wire iq_valid_last
);

tag_chip_rate #(
  .RATE_PINS(0),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .BCH_T(BCH_T)
) tag_chip_rate_i (
  .clk(clk),
  .rst(rst),
  .rate(3'd4),
  .sda_i(sda_i),
  .scl_oe(scl_oe),
  .sda_oe(sda_oe),
  .adv_address_otp_prog(adv_address_otp_prog),
  .adv_address_otp_ready(adv_address_otp_ready),
  .i(i),
  .q(q),
  .iq_valid(iq_valid),
  .iq_valid_last(iq_valid_last)
);

endmodule
