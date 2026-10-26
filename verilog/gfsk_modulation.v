// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE parameter passed to gauss_filter (default 0 = original). See CHANGES.md.

`timescale 1ns / 1ps
module gfsk_modulation #
(
  parameter integer SAMPLE_PER_SYMBOL = 8,
  parameter integer GAUSS_FILTER_BIT_WIDTH = 16,
  parameter integer NUM_TAP_GAUSS_FILTER = 17,
  parameter integer VCO_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8,
  parameter integer GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT = 1,
  parameter integer GAUSS_TABLE = 0 // passed to gauss_filter
) (
  input wire clk,
  input wire rst,

  input wire [3:0] gauss_filter_tap_index, // only need to set 0~8, 9~16 will be mirror of 0~7
  input wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap_value,
  

  input wire phy_bit,
  input wire bit_valid,
  input wire bit_valid_last,

  output wire signed [(IQ_BIT_WIDTH-1) : 0] cos_out,
  output wire signed [(IQ_BIT_WIDTH-1) : 0] sin_out,
  output wire sin_cos_out_valid,
  output wire sin_cos_out_valid_last, 

  // for debug purpose
  output wire bit_upsample,
  output wire bit_upsample_valid,
  output wire bit_upsample_valid_last,

  output wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] bit_upsample_gauss_filter,
  output wire bit_upsample_gauss_filter_valid,
  output wire bit_upsample_gauss_filter_valid_last
);

// wire bit_upsample;
// wire bit_upsample_valid;
// wire bit_upsample_valid_last;

// wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] bit_upsample_gauss_filter;
// wire bit_upsample_gauss_filter_valid;
// wire bit_upsample_gauss_filter_valid_last;

// always @ (posedge clk) begin
//   if (bit_upsample_gauss_filter_valid) begin
//     $display("%d", bit_upsample_gauss_filter);
//   end
// end

bit_repeat_upsample # (
  .SAMPLE_PER_SYMBOL(SAMPLE_PER_SYMBOL)        
) bit_repeat_upsample_i (
  .clk(clk),
  .rst(rst),

  .phy_bit(phy_bit),
  .bit_valid(bit_valid),
  .bit_valid_last(bit_valid_last),

  .bit_upsample(bit_upsample),
  .bit_upsample_valid(bit_upsample_valid),
  .bit_upsample_valid_last(bit_upsample_valid_last)
);

// Drain the 17-tap FIR with 16 zero-valued samples before ending a packet.
// The 1-bit FIR encodes only +/-1. Feed -1 while draining, then cancel
// the contribution of the padded taps to obtain exact zero extension.
wire tail_bit, tail_valid, tail_source_last;
wire signed [GAUSS_FILTER_BIT_WIDTH-1:0] raw_filter;
wire raw_filter_valid, raw_filter_last;
btle_gauss_tail #(.WIDTH(GAUSS_FILTER_BIT_WIDTH), .NUM_TAPS(NUM_TAP_GAUSS_FILTER), .FIXED_TAPS(GAUSS_TABLE)) tail_i (
  .clk(clk), .rst(rst), .tap_index(gauss_filter_tap_index), .tap_value(gauss_filter_tap_value),
  .source_bit(bit_upsample), .source_valid(bit_upsample_valid), .source_last(bit_upsample_valid_last),
  .filter_bit(tail_bit), .filter_valid(tail_valid), .filter_source_last(tail_source_last),
  .raw_filter(raw_filter), .raw_valid(raw_filter_valid), .raw_last(raw_filter_last),
  .value(bit_upsample_gauss_filter), .valid(bit_upsample_gauss_filter_valid),
  .last(bit_upsample_gauss_filter_valid_last)
);

gauss_filter # (
  .GAUSS_FILTER_BIT_WIDTH(GAUSS_FILTER_BIT_WIDTH),
  .GAUSS_TABLE(GAUSS_TABLE),
  .NUM_TAP_GAUSS_FILTER(NUM_TAP_GAUSS_FILTER)
) gauss_filter_i (
  .clk(clk),
  .rst(rst),

  .tap_index(gauss_filter_tap_index),
  .tap_value(gauss_filter_tap_value),

  .bit_upsample(tail_bit),
  .bit_upsample_valid(tail_valid),
  .bit_upsample_valid_last(tail_source_last),

  .bit_upsample_gauss_filter(raw_filter),
  .bit_upsample_gauss_filter_valid(raw_filter_valid),
  .bit_upsample_gauss_filter_valid_last(raw_filter_last)
);

vco # (
  .VCO_BIT_WIDTH(VCO_BIT_WIDTH),
  .SIN_COS_ADDR_BIT_WIDTH(SIN_COS_ADDR_BIT_WIDTH),
  .IQ_BIT_WIDTH(IQ_BIT_WIDTH)
) vco_i (
  .clk(clk),
  .rst(rst),

  .voltage_signal({{GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT{1'b1}}, bit_upsample_gauss_filter[(GAUSS_FILTER_BIT_WIDTH-1) : GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT]}),
  .voltage_signal_valid(bit_upsample_gauss_filter_valid),
  .voltage_signal_valid_last(bit_upsample_gauss_filter_valid_last),
  
  .cos_out(cos_out),
  .sin_out(sin_out),
  .sin_cos_out_valid(sin_cos_out_valid),
  .sin_cos_out_valid_last(sin_cos_out_valid_last)
);

endmodule


// Full-convolution packet tail adapter. No valid sample is generated on the
// clock immediately after the previous one: compatible with one-port VCOs.
// Bundled helper: preserve the existing single-file compilation interface.
/* verilator lint_off DECLFILENAME */
module btle_gauss_tail #(
/* verilator lint_on DECLFILENAME */
  parameter integer WIDTH = 16,
  parameter integer NUM_TAPS = 17,
  parameter integer FIXED_TAPS = 0,
  parameter [9*16-1:0] TAPS = {16'd24,16'd22,16'd15,16'd9,16'd4,16'd1,16'd0,16'd0,16'd0}
)(
  input wire clk, rst,
  input wire [3:0] tap_index,
  input wire signed [WIDTH-1:0] tap_value,
  input wire source_bit, source_valid, source_last,
  output wire filter_bit, filter_valid, filter_source_last,
  input wire signed [WIDTH-1:0] raw_filter,
  input wire raw_valid, raw_last,
  output wire signed [WIDTH-1:0] value,
  output wire valid, last
);
  reg [4:0] remaining, padding;
  reg wait_cycle;
  reg signed [WIDTH-1:0] taps [0:8];
  reg signed [WIDTH-1:0] correction, next_correction;
  integer j, index;
  wire emit_padding = (remaining != 0) && !wait_cycle;
  assign filter_bit = (remaining != 0) ? 1'b0 : source_bit;
  assign filter_valid = (remaining != 0) ? emit_padding : source_valid;
  // Preserve the original end marker internally to align the correction with
  // the FIR pipeline. The externally visible marker moves to the final tail.
  assign filter_source_last = (remaining == 0) && source_valid && source_last;
  assign value = raw_filter + correction;
  assign valid = raw_valid;
  localparam integer LAST_TAP = NUM_TAPS-1;
  assign last = raw_valid && ({27'b0, padding} == NUM_TAPS-1);
  always @* begin
    next_correction = 0;
    index = 0;
    for (j=0; j<NUM_TAPS-1; j=j+1) begin
      index = (j<=8) ? j : NUM_TAPS-1-j;
      if (remaining != 0 && j < NUM_TAPS-{27'b0, remaining}) begin
        if (FIXED_TAPS != 0)
          next_correction = next_correction + $signed(TAPS[index*16 +: 16]);
        else
          next_correction = next_correction + taps[index];
      end
    end
  end
  // the runtime taps: registers with FIXED_TAPS = 0 only (with fixed taps next_correction reads TAPS)
  generate
  if (FIXED_TAPS == 0) begin : gen_runtime_taps
    integer k;
    always @(posedge clk) begin
      if (rst) begin
        for (k=0;k<9;k=k+1) taps[k] <= 0;
      end else begin
        if (tap_index < 9) taps[tap_index] <= tap_value;
      end
    end
  end else begin : gen_fixed_taps
    integer k;
    always @(*) begin
      for (k=0;k<9;k=k+1) taps[k] = 0;
    end
    wire unused_runtime_taps = &{1'b0, tap_index, tap_value};
  end
  endgenerate
  always @(posedge clk) begin
    if (rst) begin
      remaining <= 0;
      padding <= 0;
      wait_cycle <= 0;
      correction <= 0;
    end else begin
      // Capture the same tap epoch as the one-cycle FIR, including a tap write
      // on this edge. The old register value contributes to both terms.
      if (filter_valid) correction <= next_correction;
      if (remaining == 0) begin
        if (source_valid && source_last) begin
          remaining <= LAST_TAP[4:0];
          wait_cycle <= 1;
        end
      end else begin
        wait_cycle <= !wait_cycle;
        if (emit_padding) remaining <= remaining-1'b1;
      end
      if (raw_valid) begin
        if (raw_last) padding <= 1;
        else if ({27'b0, padding} == NUM_TAPS-1) padding <= 0;
        else if (padding != 0) padding <= padding+1'b1;
      end
    end
  end
endmodule
