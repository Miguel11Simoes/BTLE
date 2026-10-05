// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license

// Repeat each accepted bit SAMPLE_PER_SYMBOL times, one sample every two
// clocks. A new bit must not arrive before all repeats of the previous bit.
// The packet marker follows its own bit; idle time cannot change its phase.
`timescale 1ns / 1ps
module bit_repeat_upsample #(
  parameter integer SAMPLE_PER_SYMBOL = 8
)(
  input wire clk, rst,
  input wire phy_bit, bit_valid, bit_valid_last,
  output reg bit_upsample,
  output reg bit_upsample_valid,
  output reg bit_upsample_valid_last
);
  localparam integer COUNT_WIDTH = (SAMPLE_PER_SYMBOL > 1) ? $clog2(SAMPLE_PER_SYMBOL) : 1;
  localparam [COUNT_WIDTH-1:0] REPEATS = SAMPLE_PER_SYMBOL-1;
  reg [COUNT_WIDTH-1:0] remaining;
  reg wait_cycle, saved_last;
  always @(posedge clk) begin
    if (rst) begin
      bit_upsample <= 0;
      bit_upsample_valid <= 0;
      bit_upsample_valid_last <= 0;
      remaining <= 0;
      wait_cycle <= 0;
      saved_last <= 0;
    end else begin
      bit_upsample_valid <= 0;
      bit_upsample_valid_last <= 0;
      if (bit_valid) begin
        bit_upsample <= phy_bit;
        bit_upsample_valid <= 1;
        bit_upsample_valid_last <= bit_valid_last && (SAMPLE_PER_SYMBOL == 1);
        remaining <= REPEATS;
        saved_last <= bit_valid_last;
        wait_cycle <= 1;
      end else if (remaining != 0) begin
        wait_cycle <= !wait_cycle;
        if (!wait_cycle) begin
          bit_upsample_valid <= 1;
          bit_upsample_valid_last <= saved_last && (remaining == 1);
          remaining <= remaining-1'b1;
        end
      end
    end
  end
endmodule
