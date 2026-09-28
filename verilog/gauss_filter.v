// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE (default 0 = original FIR with taps written at
// runtime). With 1 the output is computed by distributed arithmetic: the 17-sample window is split
// into 3 groups (6+6+5 samples), each indexing a constant table of signed tap sums computed at
// elaboration from GAUSS_TABLE_TAPS; tap_index/tap_value are then ignored. Exact for every input
// sequence (same shift register, same valid timing, same modulo-2^W sum). See CHANGES.md.

// Core_v5.3 section 3.1on page 2640
// BT = 0.5

`timescale 1ns / 1ps
module gauss_filter #
(
  parameter integer GAUSS_FILTER_BIT_WIDTH = 16,
  parameter integer NUM_TAP_GAUSS_FILTER = 17,
  parameter integer GAUSS_TABLE = 0, // 1: fixed-tap table (distributed arithmetic) instead of the runtime FIR
  // taps 0..8 (9..16 mirror 7..0), W bits each, tap 0 in the LSBs. Default: BLE BT = 0.5, 8 samples/symbol,
  // the values python/btlelib.py generates (0 0 0 1 4 9 15 22 24 22 15 9 4 1 0 0 0). Assumes W = 16.
  parameter [9*16-1:0] GAUSS_TABLE_TAPS = {16'd24, 16'd22, 16'd15, 16'd9, 16'd4, 16'd1, 16'd0, 16'd0, 16'd0}
) (
  input wire clk,
  input wire rst,

  input wire [3:0] tap_index, // only need to set 0~8, 9~16 will be mirror of 0~7
  input wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap_value,

  input wire bit_upsample,
  input wire bit_upsample_valid,
  input wire bit_upsample_valid_last,
  
  output reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] bit_upsample_gauss_filter,
  output reg bit_upsample_gauss_filter_valid,
  output reg bit_upsample_gauss_filter_valid_last
);

reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap0;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap1;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap2;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap3;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap4;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap5;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap6;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap7;
reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap8;

reg [(NUM_TAP_GAUSS_FILTER-2) : 0] bit_upsample_store;

wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap0_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap1_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap2_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap3_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap4_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap5_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap6_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap7_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap8_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap9_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap10_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap11_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap12_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap13_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap14_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap15_mult;
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] tap16_mult;

assign tap0_mult  = (bit_upsample         ? gauss_filter_tap0:(-gauss_filter_tap0));
assign tap1_mult  = (bit_upsample_store[0]? gauss_filter_tap1:(-gauss_filter_tap1));
assign tap2_mult  = (bit_upsample_store[1]? gauss_filter_tap2:(-gauss_filter_tap2));
assign tap3_mult  = (bit_upsample_store[2]? gauss_filter_tap3:(-gauss_filter_tap3));
assign tap4_mult  = (bit_upsample_store[3]? gauss_filter_tap4:(-gauss_filter_tap4));
assign tap5_mult  = (bit_upsample_store[4]? gauss_filter_tap5:(-gauss_filter_tap5));
assign tap6_mult  = (bit_upsample_store[5]? gauss_filter_tap6:(-gauss_filter_tap6));
assign tap7_mult  = (bit_upsample_store[6]? gauss_filter_tap7:(-gauss_filter_tap7));
assign tap8_mult  = (bit_upsample_store[7]? gauss_filter_tap8:(-gauss_filter_tap8));
assign tap9_mult  = (bit_upsample_store[8]? gauss_filter_tap7:(-gauss_filter_tap7));
assign tap10_mult = (bit_upsample_store[9]? gauss_filter_tap6:(-gauss_filter_tap6));
assign tap11_mult = (bit_upsample_store[10]?gauss_filter_tap5:(-gauss_filter_tap5));
assign tap12_mult = (bit_upsample_store[11]?gauss_filter_tap4:(-gauss_filter_tap4));
assign tap13_mult = (bit_upsample_store[12]?gauss_filter_tap3:(-gauss_filter_tap3));
assign tap14_mult = (bit_upsample_store[13]?gauss_filter_tap2:(-gauss_filter_tap2));
assign tap15_mult = (bit_upsample_store[14]?gauss_filter_tap1:(-gauss_filter_tap1));
assign tap16_mult = (bit_upsample_store[15]?gauss_filter_tap0:(-gauss_filter_tap0));

wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] fir_sum = (tap0_mult+tap1_mult+tap2_mult+tap3_mult+tap4_mult+tap5_mult+tap6_mult+tap7_mult+tap8_mult+tap9_mult+tap10_mult+tap11_mult+tap12_mult+tap13_mult+tap14_mult+tap15_mult+tap16_mult);
wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_sum;

// ---- GAUSS_TABLE: distributed arithmetic over the same 17-sample window ----
// window position 0 = bit_upsample, position k (1..16) = bit_upsample_store[k-1];
// position k uses tap k for k <= 8 and tap 16-k for k >= 9, as the FIR above.
function signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_tap;
  input integer pos;
  integer t;
  begin
    t = (pos <= 8) ? pos : (16 - pos);
    table_tap = (GAUSS_TABLE_TAPS >> (t*16));
  end
endfunction

// sum over the group of (bit ? tap : -tap), modulo 2^W like the FIR
function signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_entry;
  input integer first_pos;
  input integer num_pos;
  input integer bits;
  integer k;
  reg signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] acc;
  begin
    acc = 0;
    for (k=0; k<num_pos; k=k+1)
      acc = acc + ( ((bits >> k) & 1) ? table_tap(first_pos+k) : -table_tap(first_pos+k) );
    table_entry = acc;
  end
endfunction

genvar e;
generate
if (GAUSS_TABLE) begin : gen_table
  wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_a [0:63]; // positions 0..5
  wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_b [0:63]; // positions 6..11
  wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] table_c [0:31]; // positions 12..16
  for (e=0; e<64; e=e+1) begin : fill_ab
    assign table_a[e] = table_entry(0, 6, e);
    assign table_b[e] = table_entry(6, 6, e);
  end
  for (e=0; e<32; e=e+1) begin : fill_c
    assign table_c[e] = table_entry(12, 5, e);
  end
  assign table_sum = table_a[{bit_upsample_store[4:0], bit_upsample}] +
                     table_b[bit_upsample_store[10:5]] +
                     table_c[bit_upsample_store[15:11]];
end else begin : gen_no_table
  assign table_sum = 0;
end
endgenerate

// Populate input tap index and value to internal taps
always @ (posedge clk) begin
  if (rst) begin
    gauss_filter_tap0 <= 0;
    gauss_filter_tap1 <= 0;
    gauss_filter_tap2 <= 0;
    gauss_filter_tap3 <= 0;
    gauss_filter_tap4 <= 0;
    gauss_filter_tap5 <= 0;
    gauss_filter_tap6 <= 0;
    gauss_filter_tap7 <= 0;
    gauss_filter_tap8 <= 0;
  end else begin
    case(tap_index)
      0: begin gauss_filter_tap0 <= tap_value; end
      1: begin gauss_filter_tap1 <= tap_value; end
      2: begin gauss_filter_tap2 <= tap_value; end
      3: begin gauss_filter_tap3 <= tap_value; end
      4: begin gauss_filter_tap4 <= tap_value; end
      5: begin gauss_filter_tap5 <= tap_value; end
      6: begin gauss_filter_tap6 <= tap_value; end
      7: begin gauss_filter_tap7 <= tap_value; end
      8: begin gauss_filter_tap8 <= tap_value; end
    endcase
  end
end


always @ (posedge clk) begin
  if (rst) begin
    bit_upsample_gauss_filter <= 0;
    bit_upsample_gauss_filter_valid <= 0;
    bit_upsample_gauss_filter_valid_last <= 0;
    bit_upsample_store <= 0;
  end else begin
    bit_upsample_gauss_filter_valid <= bit_upsample_valid;
    bit_upsample_gauss_filter_valid_last <= bit_upsample_valid_last;
    if (bit_upsample_valid) begin
      bit_upsample_store[(NUM_TAP_GAUSS_FILTER-2) : 1] <= bit_upsample_store[(NUM_TAP_GAUSS_FILTER-3) : 0];
      bit_upsample_store[0] <= bit_upsample;

      bit_upsample_gauss_filter <= (GAUSS_TABLE ? table_sum : fir_sum);
    end 
  end
end

endmodule
