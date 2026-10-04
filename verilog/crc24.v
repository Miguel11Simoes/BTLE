// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-10-04 by Miguel Simões: one 6-bit bit counter instead of the 13-bit input count and
// the 5-bit CRC count, and two states instead of three (same outputs on every clock inside
// btle_tx). See CHANGES.md.

// Core_v5.3 figure3.4 on page 2734
// Assume clk speed 16M, info_bit 1M, info_bit_valid every 16 clk
// CRC operation skips the 40 bits at the beginning (preamble+access_address)

// Upstream counts every input bit in a 13-bit info_bit_count that is only ever
// compared with 40, counts the CRC bits in a separate 5-bit crc_bit_count, and
// has three states, IDLE, WORK_ON_INPUT and CRC_BIT_OUTPUT. Here:
//   - bit_count (6 bits) counts the input bits up to 40 and stops there
//     (upstream's count never wraps: at most 40 + 2 056 bits per packet, and it
//     is cleared at the end of every CRC output);
//   - during the CRC output the same register counts on from 40 to 63, so the
//     index of the CRC bit sent is 23 - (bit_count - 40) = ~bit_count[4:0];
//   - IDLE and WORK_ON_INPUT are one state: they differ only in that IDLE
//     ignores info_bit_valid_last, which never comes with the first bit;
//   - clk_count has no reset: it is cleared in every clock of the input state
//     and read only in the CRC state, which follows one.
// btle_tx, which drives every input, meets what this needs: at least 40 valid
// bits (preamble and access address) before info_bit_valid_last, and
// info_bit_valid_last never with the first bit of a packet.

`timescale 1ns / 1ps
module crc24 #
(
  parameter integer NUM_BIT_PAYLOAD_LENGTH = 8, // 8 bit in the core spec 6.2
  parameter integer CRC_STATE_BIT_WIDTH = 24
) (
  input wire clk,
  input wire rst,

  input  wire [(CRC_STATE_BIT_WIDTH-1) : 0] crc_state_init_bit, // load into lfsr (linear feedback shift register) upon crc_state_init_bit_load==1
  input  wire crc_state_init_bit_load,
  input  wire info_bit,
  input  wire info_bit_valid,
  input  wire info_bit_valid_last, // if this is true together with valid, it means last bit input
  output reg  info_bit_after_crc24,
  output reg  info_bit_after_crc24_valid,
  output reg  info_bit_after_crc24_valid_last // indicate last bit out together with info_bit_after_crc24_valid
);

reg crc_output; // 0: upstream's IDLE and WORK_ON_INPUT, 1: CRC_BIT_OUTPUT

wire [(CRC_STATE_BIT_WIDTH-1) : 0] lfsr;

wire info_bit_valid_internal;
reg [5:0] bit_count; // input bits, up to 40; then 40 + the CRC bits sent
reg [3:0] clk_count;

assign info_bit_valid_internal = (bit_count>=40? info_bit_valid : 0);

always @ (posedge clk) begin
  if (rst) begin
    info_bit_after_crc24 <= 0;
    info_bit_after_crc24_valid <= 0;
    info_bit_after_crc24_valid_last <= 0;

    bit_count <= 0;

    crc_output <= 0;
  end else begin
    if (!crc_output) begin
      info_bit_after_crc24 <= info_bit;
      info_bit_after_crc24_valid <= info_bit_valid;
      info_bit_after_crc24_valid_last <= 0;

      clk_count <= 0;

      if (info_bit_valid && bit_count != 40) begin
        bit_count <= bit_count + 1;
      end

      crc_output <= info_bit_valid_last;
    end else begin
      clk_count <= clk_count + 1;
      if (clk_count == 15) begin
        bit_count <= bit_count + 1;
        info_bit_after_crc24 <= lfsr[~bit_count[4:0]];
        info_bit_after_crc24_valid <= 1;
        if (bit_count == 63) begin
          info_bit_after_crc24_valid_last <= 1;

          bit_count <= 0;

          crc_output <= 0;
        end
      end else begin
        info_bit_after_crc24_valid <= 0;
        info_bit_after_crc24_valid_last <= 0;
      end
    end
  end
end

crc24_core # (
  .CRC_STATE_BIT_WIDTH(CRC_STATE_BIT_WIDTH)
) crc24_core_i (
  .clk(clk),
  .rst(rst),

  .crc_state_init_bit(crc_state_init_bit),
  .crc_state_init_bit_load(crc_state_init_bit_load),
  .data_in(info_bit),
  .data_in_valid(info_bit_valid_internal),

  .lfsr(lfsr)
);

endmodule
