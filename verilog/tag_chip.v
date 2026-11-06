// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// tag_core as a chip would have it (ble-tx-poc): the top of the ASIC flows (area, GF180 layout), with the
// pins of the tag and nothing else: the sensor bus, the radio's samples, AdvA's production port. No ADC
// (ADC_EN = 0) and no MTP macro in the open PDK, so those ports are tied here. BUS_DIV = 1: clk is the
// 32.768 kHz clock between packets, and no divider is laid out; the switch to 16 MHz for the packet is
// not designed yet (tag_core.v), and the flows time clk at 16 MHz, the harder case.

`timescale 1ns / 1ps
module tag_chip #
(
  parameter integer CFG_SRC = 0,           // passed to tag_core: 0 EEPROM, 1 OTP
  parameter integer ADV_ADDRESS_OTP = 0,   // passed to tag_core
  parameter integer SENSOR_BYTES = 1,
  parameter integer BCH_T = 8
) (
  input  wire clk,
  input  wire rst,

  input  wire scl_i,
  input  wire sda_i,
  input  wire miso_i,
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

// the outputs of tag_core that a chip does not bring out: only for the FPGA's status registers and debug
wire unused_adc_start, unused_mtp_read, unused_phy_bit, unused_phy_bit_valid, unused_phy_bit_valid_last;
wire unused_upsample, unused_upsample_valid, unused_upsample_valid_last, unused_gauss_valid, unused_gauss_valid_last;
wire unused_event_done, unused_sensor_failed, unused_profile_ok, unused_adv_address_read, unused_tx_add, unused_test_mode;
wire [5:0] unused_mtp_address, unused_channel;
wire signed [15:0] unused_gauss;
wire [(8*SENSOR_BYTES-1):0] unused_sensor;
wire [47:0] unused_adv_address_sent;
wire [15:0] unused_interval;
wire [3:0] unused_state_status;

tag_core #(
  .CFG_SRC(CFG_SRC),
  .SENSOR_BYTES(SENSOR_BYTES),
  .BCH_T(BCH_T),
  .ADC_EN(0),
  .BUS_DIV(1),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP)
) tag_core_i (
  .clk(clk),
  .rst(rst),
  .scl_i(scl_i),
  .sda_i(sda_i),
  .miso_i(miso_i),
  .scl_oe(scl_oe),
  .sda_oe(sda_oe),
  .cs_n(cs_n),
  .adc_start(unused_adc_start),
  .adc_done(1'b0),
  .adc_data(12'd0),
  .mtp_read(unused_mtp_read),
  .mtp_address(unused_mtp_address),
  .mtp_data(8'd0),
  .mtp_valid(1'b0),
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
  .event_done(unused_event_done),
  .sensor(unused_sensor),
  .sensor_failed(unused_sensor_failed),
  .profile_ok(unused_profile_ok),
  .adv_address_read(unused_adv_address_read),
  .tx_add(unused_tx_add),
  .adv_address_sent(unused_adv_address_sent),
  .channel(unused_channel),
  .interval(unused_interval),
  .test_mode(unused_test_mode),
  .state_status(unused_state_status)
);

endmodule
