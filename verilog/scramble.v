// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-10-04 by Miguel Simões: a 6-bit input count that stops at 41 and no state register
// (same outputs on every clock while a packet has fewer than 8 192 bits). See CHANGES.md.

// Core_v5.3 figure3.5 on page 2735

// Upstream's 13-bit data_in_count is only compared with 40 and 41, and does not
// wrap in a packet of btle_tx (at most 40 + 2 056 + 24 bits, cleared after the
// last one): here it has 6 bits and stops at 41. Upstream's state is IDLE exactly when the
// count is 0 (IDLE is entered with the count cleared and left with it
// incremented), so the state register is not needed.

`timescale 1ns / 1ps
module scramble #
(
  parameter integer NUM_BIT_PAYLOAD_LENGTH = 8, // 8 bit in the core spec 6.2
  parameter integer CHANNEL_NUMBER_BIT_WIDTH = 6
) (
  input wire clk,
  input wire rst,

  input  wire [(CHANNEL_NUMBER_BIT_WIDTH-1) : 0] channel_number, // load into lfsr (linear feedback shift register) upon channel_number_load==1
  input  wire channel_number_load,
  input  wire data_in,
  input  wire data_in_valid,
  input  wire data_in_valid_last, // if this is true together with valid, it means last bit input
  output wire data_out,
  output wire data_out_valid,
  output wire data_out_valid_last // indicate last bit out together with data_out_valid
);

wire data_in_valid_internal;
wire data_out_internal;
wire data_out_valid_internal;
wire scramble_start_for_input;
wire scramble_start_for_output;

reg data_in_delay;
reg data_in_valid_delay;
reg data_in_valid_last_delay;

reg [5:0] data_in_count; // input bits, stops at 41; 0 is upstream's IDLE

assign scramble_start_for_input = (data_in_count>=40);
assign data_in_valid_internal = (scramble_start_for_input? data_in_valid : 0);

assign scramble_start_for_output = (data_in_count>=41);
assign data_out = (scramble_start_for_output? data_out_internal : data_in_delay);

assign data_out_valid = data_in_valid_delay;
assign data_out_valid_last = data_in_valid_last_delay;

scramble_core # (
  .CHANNEL_NUMBER_BIT_WIDTH(CHANNEL_NUMBER_BIT_WIDTH)
) crc24_core_i (
  .clk(clk),
  .rst(rst),

  .channel_number(channel_number),
  .channel_number_load(channel_number_load),
  .data_in(data_in),
  .data_in_valid(data_in_valid_internal),
  .data_out(data_out_internal),
  .data_out_valid(data_out_valid_internal)
);

always @ (posedge clk) begin
  if (rst) begin
    data_in_delay <= 0;
    data_in_valid_delay <= 0;
    data_in_valid_last_delay <= 0;

    data_in_count <= 0;
  end else begin
    data_in_delay <= data_in;
    data_in_valid_delay <= data_in_valid;
    data_in_valid_last_delay <= data_in_valid_last;

    if (data_in_count != 0 && data_in_valid_last_delay) begin
      data_in_count <= 0;
    end else if (data_in_valid && data_in_count != 41) begin
      data_in_count <= data_in_count + 1;
    end
  end
end


// Intentionally unused compatibility/debug fields. No functional fanout is added.
wire unused_interface_fields = &{1'b0,
  NUM_BIT_PAYLOAD_LENGTH, data_out_valid_internal};

endmodule
