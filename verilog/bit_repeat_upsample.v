// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-10-04 by Miguel Simões: the two 15-bit delay lines, used only through their OR,
// are two 4-bit down-counters (same outputs on every clock, for every input). See CHANGES.md.

// Input phy_bit rate 1M, output phy_bit rate 8M
// clk speed 16M

`timescale 1ns / 1ps
module bit_repeat_upsample #
(
  parameter integer SAMPLE_PER_SYMBOL = 8
) (
  input wire clk,
  input wire rst,

  input wire phy_bit,
  input wire bit_valid,
  input wire bit_valid_last,

  output reg  bit_upsample,
  output wire bit_upsample_valid,
  output wire bit_upsample_valid_last
);

// Upstream shifts bit_valid and bit_valid_last through 15-bit delay lines and
// uses only the OR of each line: "a pulse in the last 15 clocks". A counter
// gives the same: it is loaded with 15 by a pulse and counts down to 0, so it
// is nonzero in exactly the 15 clocks after the pulse (a new pulse reloads it).
reg [3:0] bit_valid_window;
reg [3:0] bit_valid_last_window;
wire bit_valid_wide;
wire bit_valid_last_wide;
reg bit_upsample_valid_internal;
reg [2:0] bit_upsample_count;
reg first_bit_valid_encountered;

assign bit_valid_wide = (bit_valid_window != 0);
assign bit_valid_last_wide = (bit_valid_last_window != 0);

assign bit_upsample_valid = (bit_upsample_valid_internal & bit_valid_wide);
assign bit_upsample_valid_last = ((bit_upsample_count==0) & bit_valid_last_wide);

always @ (posedge clk) begin
  if (rst) begin
    bit_valid_window <= 0;
    bit_valid_last_window <= 0;
    bit_upsample <= 0;
    bit_upsample_valid_internal <= 0;
    bit_upsample_count <= 0;

    first_bit_valid_encountered <= 0;
  end else begin
    bit_valid_window <= (bit_valid ? 4'd15 : (bit_valid_wide ? (bit_valid_window - 1'b1) : 4'd0));
    bit_valid_last_window <= (bit_valid_last ? 4'd15 : (bit_valid_last_wide ? (bit_valid_last_window - 1'b1) : 4'd0));

    if (bit_valid) begin
      bit_upsample <= phy_bit;
    end
    bit_upsample_valid_internal <= (~bit_upsample_valid_internal);

    first_bit_valid_encountered <= (bit_valid? 1 : first_bit_valid_encountered);
    if (first_bit_valid_encountered == 0) begin
      bit_upsample_count <= 1;
    end else begin
      bit_upsample_count <= (bit_upsample_valid_internal == 0? (bit_upsample_count + 1) : bit_upsample_count);
    end
  end
end

endmodule
