// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE parameter passed to btle_tx (default 0 = original). See CHANGES.md.
// Modified 2026-10-16 by Miguel Simões: ADV_ADDRESS, ADV_DATA_FLOPS and ADV_ADDRESS_OTP passed to btle_tx; the OTP programming port tied off. See CHANGES.md.
// Modified 2026-11-04 by Miguel Simões: the senseworks tag: no receiver (the RX ports kept, their
// outputs 0); TX_ADD, COMPANY_ID and BCH_T passed to btle_tx, ADV_DATA_FLOPS gone. See CHANGES.md.

// iverilog -o btle_phy btle_phy.v scramble_core.v crc24_core.v btle_tx.v crc24.v scramble.v gfsk_modulation.v bit_repeat_upsample.v gauss_filter.v vco.v

`timescale 1ns / 1ps
module btle_phy #
(
  parameter integer CRC_STATE_BIT_WIDTH = 24,
  parameter integer CHANNEL_NUMBER_BIT_WIDTH = 6,
  parameter integer SAMPLE_PER_SYMBOL = 8,
  parameter integer GAUSS_FILTER_BIT_WIDTH = 16,
  parameter integer NUM_TAP_GAUSS_FILTER = 17,
  parameter integer VCO_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8,
  parameter integer GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT = 1,

  parameter integer GFSK_DEMODULATION_BIT_WIDTH = 16,
  parameter integer LEN_UNIQUE_BIT_SEQUENCE = 32,
  parameter integer NUM_BIT_PAYLOAD_LENGTH = 8, // 8 bit in the core spec 6.2
  parameter integer GAUSS_TABLE = 0, // passed to btle_tx
  parameter [47:0] ADV_ADDRESS = 48'hC10203040506, // passed to btle_tx: AdvA, fixed per chip
  parameter integer ADV_ADDRESS_OTP = 0, // passed to btle_tx
  parameter integer TX_ADD = 1, // passed to btle_tx: the tag's packet
  parameter [15:0] COMPANY_ID = 16'hFFFF, // passed to btle_tx
  parameter integer BCH_T = 8 // passed to btle_tx
) (
  input wire clk,
  input wire rst,

  input wire clkb,

  // for tx
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

btle_tx # (
  .NUM_BIT_PAYLOAD_LENGTH(NUM_BIT_PAYLOAD_LENGTH),
  .CRC_STATE_BIT_WIDTH(CRC_STATE_BIT_WIDTH),
  .CHANNEL_NUMBER_BIT_WIDTH(CHANNEL_NUMBER_BIT_WIDTH),
  .SAMPLE_PER_SYMBOL(SAMPLE_PER_SYMBOL),
  .GAUSS_FILTER_BIT_WIDTH(GAUSS_FILTER_BIT_WIDTH),
  .GAUSS_TABLE(GAUSS_TABLE),
  .ADV_ADDRESS(ADV_ADDRESS),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .TX_ADD(TX_ADD),
  .COMPANY_ID(COMPANY_ID),
  .BCH_T(BCH_T),
  .NUM_TAP_GAUSS_FILTER(NUM_TAP_GAUSS_FILTER),
  .VCO_BIT_WIDTH(VCO_BIT_WIDTH),
  .SIN_COS_ADDR_BIT_WIDTH(SIN_COS_ADDR_BIT_WIDTH),
  .IQ_BIT_WIDTH(IQ_BIT_WIDTH),
  .GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT(GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT)
) btle_tx_i (
  .clk(clk),
  .rst(rst),

  .clkb(clkb),

  .gauss_filter_tap_index(tx_gauss_filter_tap_index),
  .gauss_filter_tap_value(tx_gauss_filter_tap_value),

  .cos_table_write_address(tx_cos_table_write_address),
  .cos_table_write_data(tx_cos_table_write_data),
  .sin_table_write_address(tx_sin_table_write_address),
  .sin_table_write_data(tx_sin_table_write_data),
  
  .preamble(tx_preamble),

  .access_address(tx_access_address),
  .crc_state_init_bit(tx_crc_state_init_bit),
  .crc_state_init_bit_load(tx_crc_state_init_bit_load),
  .channel_number(tx_channel_number),
  .channel_number_load(tx_channel_number_load),

  .pdu_octet_mem_data(tx_pdu_octet_mem_data),
  .pdu_octet_mem_addr(tx_pdu_octet_mem_addr),

  .tx_start(tx_start),
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
  .bit_upsample_gauss_filter_valid_last(tx_bit_upsample_gauss_filter_valid_last)
);

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

