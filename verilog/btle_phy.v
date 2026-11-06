// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE parameter passed to btle_tx (default 0 = original). See CHANGES.md.
// Modified 2026-10-16 by Miguel Simões: ADV_ADDRESS, ADV_DATA_FLOPS and ADV_ADDRESS_OTP passed to btle_tx; the OTP programming port tied off. See CHANGES.md.
// Modified 2026-11-04 by Miguel Simões: the senseworks tag: no receiver (the RX ports kept, their
// outputs 0); TX_ADD, COMPANY_ID and BCH_T passed to btle_tx, ADV_DATA_FLOPS gone. See CHANGES.md.
// Modified 2026-11-06 by Miguel Simões: ble-tx-poc: tag_core (the tag's acquisition and btle_tx) in
// place of btle_tx: the TX inputs from the Link Layer are kept for the controller's interface, unused;
// the sensor bus and the tag's state are new ports. See CHANGES.md and docs/Senseworks/TX_POC.md.

// iverilog -o btle_phy btle_phy.v tag_core.v tag_bus.v tag_capture.v scramble_core.v crc24_core.v btle_tx.v crc24.v scramble.v gfsk_modulation.v bit_repeat_upsample.v gauss_filter.v vco.v

`timescale 1ns / 1ps
module btle_phy #
(
  parameter integer CRC_STATE_BIT_WIDTH = 24,
  parameter integer CHANNEL_NUMBER_BIT_WIDTH = 6,
  parameter integer GAUSS_FILTER_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8,

  parameter integer GFSK_DEMODULATION_BIT_WIDTH = 16,
  parameter integer LEN_UNIQUE_BIT_SEQUENCE = 32,
  parameter integer NUM_BIT_PAYLOAD_LENGTH = 8, // 8 bit in the core spec 6.2
  parameter integer CFG_SRC = 0, // passed to tag_core
  parameter integer SENSOR_BYTES = 1, // passed to tag_core
  parameter integer ADC_EN = 0, // passed to tag_core
  parameter integer ADC_BITS = 12, // passed to tag_core
  parameter integer BUS_DIV = 250, // passed to tag_core
  parameter [47:0] ADV_ADDRESS = 48'hC10203040506, // passed to tag_core
  parameter integer ADV_ADDRESS_OTP = 0, // passed to tag_core
  parameter integer TX_ADD = 1, // passed to tag_core
  parameter [15:0] COMPANY_ID = 16'hFFFF, // passed to tag_core
  parameter integer BCH_T = 8 // passed to tag_core
) (
  input wire clk,
  input wire rst,

  // for tx: the Link Layer's registers, not used: tag_core drives btle_tx
  input wire [3:0] tx_gauss_filter_tap_index, // only need to set 0~8, 9~16 will be mirror of 0~7
  input wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tx_gauss_filter_tap_value,

  input wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] tx_cos_table_write_address,
  input wire signed [(IQ_BIT_WIDTH-1) : 0] tx_cos_table_write_data,
  input wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] tx_sin_table_write_address,
  input wire signed [(IQ_BIT_WIDTH-1) : 0] tx_sin_table_write_data,

  input wire [7:0]  tx_preamble,

  input wire [31:0] tx_access_address,
  input wire [(CRC_STATE_BIT_WIDTH-1) : 0] tx_crc_state_init_bit,
  input wire tx_crc_state_init_bit_load,
  input wire [(CHANNEL_NUMBER_BIT_WIDTH-1) : 0] tx_channel_number,
  input wire tx_channel_number_load,

  input wire [7:0] tx_pdu_octet_mem_data,
  input wire [NUM_BIT_PAYLOAD_LENGTH:0] tx_pdu_octet_mem_addr,

  input wire tx_start,

  output wire signed [(IQ_BIT_WIDTH-1) : 0] tx_i_signal,
  output wire signed [(IQ_BIT_WIDTH-1) : 0] tx_q_signal,
  output wire tx_iq_valid,
  output wire tx_iq_valid_last,

  // for tx debug purpose
  output wire tx_phy_bit,
  output wire tx_phy_bit_valid,
  output wire tx_phy_bit_valid_last,

  output wire tx_bit_upsample,
  output wire tx_bit_upsample_valid,
  output wire tx_bit_upsample_valid_last,

  output wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tx_bit_upsample_gauss_filter,
  output wire tx_bit_upsample_gauss_filter_valid,
  output wire tx_bit_upsample_gauss_filter_valid_last,

  // the tag: its sensor bus (tag_bus.v), an ADC with ADC_EN = 1, and its state
  input  wire tag_scl_i,
  input  wire tag_sda_i,
  input  wire tag_miso_i,
  output wire tag_scl_oe,
  output wire tag_sda_oe,
  output wire tag_cs_n,
  output wire tag_adc_start,
  input  wire tag_adc_done,
  input  wire [(ADC_BITS-1):0] tag_adc_data,
  output wire tag_event_done,
  output wire [(8*SENSOR_BYTES-1):0] tag_sensor,
  output wire tag_sensor_failed,
  output wire tag_profile_ok,
  output wire tag_adv_address_read,
  output wire tag_tx_add,
  output wire [47:0] tag_adv_address,
  output wire [(CHANNEL_NUMBER_BIT_WIDTH-1) : 0] tag_channel,
  output wire [15:0] tag_interval,
  output wire tag_test_mode,
  output wire [3:0] tag_state,

  // for rx
  input wire [(LEN_UNIQUE_BIT_SEQUENCE-1) : 0]  rx_unique_bit_sequence,
  input wire [(CHANNEL_NUMBER_BIT_WIDTH-1) : 0] rx_channel_number,
  input wire [(CRC_STATE_BIT_WIDTH-1) : 0]      rx_crc_state_init_bit,

  input wire  signed [(GFSK_DEMODULATION_BIT_WIDTH-1) : 0] rx_i_signal,
  input wire  signed [(GFSK_DEMODULATION_BIT_WIDTH-1) : 0] rx_q_signal,
  input wire  rx_iq_valid,

  output wire  rx_hit_flag,
  output wire  rx_decode_run,
  output wire  rx_decode_end,
  output wire  rx_crc_ok,
  output wire  [2:0] rx_best_phase,
  output wire  [(NUM_BIT_PAYLOAD_LENGTH-1):0] rx_payload_length,

  input  wire  [NUM_BIT_PAYLOAD_LENGTH:0] rx_pdu_octet_mem_addr,
  output wire  [7:0] rx_pdu_octet_mem_data
);

wire unused_adv_address_otp_ready; // the OTP's ready, not used by this controller (see below)
wire unused_mtp_read;              // no MTP macro on the FPGA (see below)
wire [5:0] unused_mtp_address;

tag_core # (
  .CFG_SRC(CFG_SRC),
  .SENSOR_BYTES(SENSOR_BYTES),
  .BCH_T(BCH_T),
  .ADC_EN(ADC_EN),
  .ADC_BITS(ADC_BITS),
  .BUS_DIV(BUS_DIV),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .ADV_ADDRESS(ADV_ADDRESS),
  .TX_ADD(TX_ADD),
  .COMPANY_ID(COMPANY_ID)
) tag_core_i (
  .clk(clk),
  .rst(rst),

  .scl_i(tag_scl_i),
  .sda_i(tag_sda_i),
  .miso_i(tag_miso_i),
  .scl_oe(tag_scl_oe),
  .sda_oe(tag_sda_oe),
  .cs_n(tag_cs_n),

  .adc_start(tag_adc_start),
  .adc_done(tag_adc_done),
  .adc_data(tag_adc_data),

  // CFG_SRC = 2 is for an ASIC with an MTP macro; here tied off
  .mtp_read(unused_mtp_read),
  .mtp_address(unused_mtp_address),
  .mtp_data(8'd0),
  .mtp_valid(1'b0),

  // AdvA OTP (ADV_ADDRESS_OTP = 1): programmed in production through a chip-level test port,
  // which this controller does not have: tied off here.
  .adv_address_otp_prog(48'd0),
  .adv_address_otp_ready(unused_adv_address_otp_ready),

  .i(tx_i_signal),
  .q(tx_q_signal),
  .iq_valid(tx_iq_valid),
  .iq_valid_last(tx_iq_valid_last),

  // for debug purpose
  .phy_bit(tx_phy_bit),
  .phy_bit_valid(tx_phy_bit_valid),
  .phy_bit_valid_last(tx_phy_bit_valid_last),

  .bit_upsample(tx_bit_upsample),
  .bit_upsample_valid(tx_bit_upsample_valid),
  .bit_upsample_valid_last(tx_bit_upsample_valid_last),

  .bit_upsample_gauss_filter(tx_bit_upsample_gauss_filter),
  .bit_upsample_gauss_filter_valid(tx_bit_upsample_gauss_filter_valid),
  .bit_upsample_gauss_filter_valid_last(tx_bit_upsample_gauss_filter_valid_last),

  .event_done(tag_event_done),
  .sensor(tag_sensor),
  .sensor_failed(tag_sensor_failed),
  .profile_ok(tag_profile_ok),
  .adv_address_read(tag_adv_address_read),
  .tx_add(tag_tx_add),
  .adv_address_sent(tag_adv_address),
  .channel(tag_channel),
  .interval(tag_interval),
  .test_mode(tag_test_mode),
  .state_status(tag_state)
);

// The tag is driven by tag_core: the Link Layer's TX registers go nowhere. The ports stay for the controller's
// interface, as the receiver's do.
wire unused_tx_inputs = &{1'b0, tx_gauss_filter_tap_index, tx_gauss_filter_tap_value, tx_cos_table_write_address,
  tx_cos_table_write_data, tx_sin_table_write_address, tx_sin_table_write_data, tx_preamble, tx_access_address,
  tx_crc_state_init_bit, tx_crc_state_init_bit_load, tx_channel_number, tx_channel_number_load,
  tx_pdu_octet_mem_data, tx_pdu_octet_mem_addr, tx_start};

// No receiver (the senseworks tag, a Broadcaster with a transmitter only): the RX ports are kept for
// the controller's interface, their outputs constant 0 (nothing is ever received), their inputs unused.
assign rx_hit_flag = 1'b0;
assign rx_decode_run = 1'b0;
assign rx_decode_end = 1'b0;
assign rx_crc_ok = 1'b0;
assign rx_best_phase = 3'd0;
assign rx_payload_length = {NUM_BIT_PAYLOAD_LENGTH{1'b0}};
assign rx_pdu_octet_mem_data = 8'd0;
wire unused_rx_inputs = &{1'b0, rx_unique_bit_sequence, rx_channel_number, rx_crc_state_init_bit,
  rx_i_signal, rx_q_signal, rx_iq_valid, rx_pdu_octet_mem_addr};

endmodule

