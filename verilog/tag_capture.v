// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// The capture of a byte of sensor (ble-tx-poc): from the bits a measure program reads, in the order they
// are read (most significant first), the window of the profile: skip bits, then take bits; with sign
// extension from the first bit taken if is_signed. The bits arrive one at a time, so the window needs
// counters and no shifter. The byte is the saturation to 0..254 of (the window + offset): 0xFF is left
// for "the sensor did not answer", which tag_core sets itself. The conversion to units is the gateway's.

`timescale 1ns / 1ps
module tag_capture (
  input  wire clk,
  input  wire clear,              // before the event's first bit

  input  wire bit_valid,
  input  wire bit_in,

  input  wire [5:0] skip,
  input  wire [4:0] take,         // 1..16
  input  wire is_signed,
  input  wire [15:0] offset,      // two's complement

  output wire [7:0] value
);

localparam signed [17:0] MAX_VALUE = 18'sd254;

reg [5:0] skip_left;
reg [4:0] take_left;
reg [15:0] window;

always @ (posedge clk) begin
  if (clear) begin
    skip_left <= skip;
    take_left <= take;
    window <= 16'd0;
  end else if (bit_valid) begin
    if (skip_left != 6'd0) begin
      skip_left <= skip_left - 6'd1;
    end else if (take_left != 5'd0) begin
      take_left <= take_left - 5'd1;
      window <= (take_left == take) ? {{15{is_signed & bit_in}}, bit_in} : {window[14:0], bit_in};
    end
  end
end

wire signed [17:0] sum = $signed({{2{is_signed & window[15]}}, window}) + $signed({{2{offset[15]}}, offset});

assign value = sum[17]            ? 8'd0 :
               (sum > MAX_VALUE)  ? MAX_VALUE[7:0] :
                                    sum[7:0];

endmodule
