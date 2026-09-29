// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license

// Core_v5.3 section 3.1on page 2640
// The modulation index shall be between 0.45 and 0.55
// We implement 0.5

`timescale 1ns / 1ps
module vco #
(
  parameter integer VCO_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8
) (
  input wire clk,
  input wire rst,

  input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] cos_table_write_address,
  input  wire signed [(IQ_BIT_WIDTH-1) : 0] cos_table_write_data,
  input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] sin_table_write_address,
  input  wire signed [(IQ_BIT_WIDTH-1) : 0] sin_table_write_data,

  input wire signed [(VCO_BIT_WIDTH-1) : 0] voltage_signal,
  input wire voltage_signal_valid,
  input wire voltage_signal_valid_last,

  output wire signed [(IQ_BIT_WIDTH-1) : 0] cos_out,
  output wire signed [(IQ_BIT_WIDTH-1) : 0] sin_out,
  output reg sin_cos_out_valid,
  output reg sin_cos_out_valid_last
);

reg signed [(VCO_BIT_WIDTH-1) : 0] integral_voltage_signal;

reg voltage_signal_valid_delay1;
reg voltage_signal_valid_last_delay1;

// A full 2^SIN_COS_ADDR_BIT_WIDTH waveform is reconstructed from the first
// quarter of each sine/cosine table (addresses 0..90 degrees, excluding 90).
// At the quadrant boundary, sin(90) = cos(0) and cos(90) = -sin(0).
// The existing write ports accept full-wave addresses, but only writes to
// the first quarter are stored. Other values follow waveform symmetry.
localparam integer QUARTER_ADDR_BIT_WIDTH = SIN_COS_ADDR_BIT_WIDTH - 2;

wire [SIN_COS_ADDR_BIT_WIDTH-1:0] phase_address =
    integral_voltage_signal[(SIN_COS_ADDR_BIT_WIDTH-1) : 0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] quarter_offset =
    phase_address[QUARTER_ADDR_BIT_WIDTH-1:0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] quarter_read_address =
    phase_address[QUARTER_ADDR_BIT_WIDTH] ? -quarter_offset : quarter_offset;

wire signed [IQ_BIT_WIDTH-1:0] cos_quarter_data;
wire signed [IQ_BIT_WIDTH-1:0] sin_quarter_data;
reg swap_endpoint_delay;
reg cos_negative_delay;
reg sin_negative_delay;

wire signed [IQ_BIT_WIDTH-1:0] cos_sample =
    swap_endpoint_delay ? sin_quarter_data : cos_quarter_data;
wire signed [IQ_BIT_WIDTH-1:0] sin_sample =
    swap_endpoint_delay ? cos_quarter_data : sin_quarter_data;

assign cos_out = cos_negative_delay ? -cos_sample : cos_sample;
assign sin_out = sin_negative_delay ? -sin_sample : sin_sample;

// Match the RAM's registered read: sign and endpoint selection describe the
// same phase address that the RAM sampled on the preceding clock edge.
always @(posedge clk) begin
  swap_endpoint_delay <= phase_address[QUARTER_ADDR_BIT_WIDTH] &&
                         (quarter_offset == 0);
  cos_negative_delay <= phase_address[SIN_COS_ADDR_BIT_WIDTH-1] ^
                        phase_address[QUARTER_ADDR_BIT_WIDTH];
  sin_negative_delay <= phase_address[SIN_COS_ADDR_BIT_WIDTH-1];
end

always @ (posedge clk) begin
  if (rst) begin
    sin_cos_out_valid <= 0;
    sin_cos_out_valid_last <= 0;

    integral_voltage_signal <= 0;

    voltage_signal_valid_delay1 <= 0;
    voltage_signal_valid_last_delay1 <= 0;
  end else begin
    voltage_signal_valid_delay1 <= voltage_signal_valid;
    voltage_signal_valid_last_delay1 <= voltage_signal_valid_last;

    sin_cos_out_valid <= voltage_signal_valid_delay1;
    sin_cos_out_valid_last <= voltage_signal_valid_last_delay1;

    if (voltage_signal_valid) begin
      integral_voltage_signal <= integral_voltage_signal + voltage_signal;
    end
  end
end

// Both quarter tables live in ONE memory of 2^QUARTER_ADDR_BIT_WIDTH words of
// {cos, sin}, because they are always read at the same address: one read port,
// and one write port with a write mask of one bit per table. The write
// interface is unchanged (an address and data per table, held until the next
// register write). Upstream rewrites each table on every clock; here a table is
// written when its address/data pair changes, and on the first clock after
// reset, which leaves the same contents. The two tables share the write port:
// if both have a write pending in the same clock, they are written together
// when their addresses are equal; otherwise the older request goes first (the
// cosine on a tie) and the other waits one clock, in a one-entry queue per
// table.
wire cos_write_in_quarter =
    cos_table_write_address[SIN_COS_ADDR_BIT_WIDTH-1:QUARTER_ADDR_BIT_WIDTH] == 0;
wire sin_write_in_quarter =
    sin_table_write_address[SIN_COS_ADDR_BIT_WIDTH-1:QUARTER_ADDR_BIT_WIDTH] == 0;

reg [SIN_COS_ADDR_BIT_WIDTH+IQ_BIT_WIDTH-1:0] cos_write_pair_delay;
reg [SIN_COS_ADDR_BIT_WIDTH+IQ_BIT_WIDTH-1:0] sin_write_pair_delay;
reg rst_delay;

wire cos_write_new = cos_write_in_quarter && (rst_delay ||
    {cos_table_write_address, cos_table_write_data} != cos_write_pair_delay);
wire sin_write_new = sin_write_in_quarter && (rst_delay ||
    {sin_table_write_address, sin_table_write_data} != sin_write_pair_delay);

reg cos_write_queued;
reg sin_write_queued;
reg [QUARTER_ADDR_BIT_WIDTH-1:0] cos_queued_address;
reg [QUARTER_ADDR_BIT_WIDTH-1:0] sin_queued_address;
reg [IQ_BIT_WIDTH-1:0] cos_queued_data;
reg [IQ_BIT_WIDTH-1:0] sin_queued_data;

// the request of each table: its queued write first, else this clock's pair
wire cos_write_request = cos_write_queued || cos_write_new;
wire sin_write_request = sin_write_queued || sin_write_new;
wire [QUARTER_ADDR_BIT_WIDTH-1:0] cos_request_address = cos_write_queued ?
    cos_queued_address : cos_table_write_address[QUARTER_ADDR_BIT_WIDTH-1:0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] sin_request_address = sin_write_queued ?
    sin_queued_address : sin_table_write_address[QUARTER_ADDR_BIT_WIDTH-1:0];
wire [IQ_BIT_WIDTH-1:0] cos_request_data = cos_write_queued ?
    cos_queued_data : cos_table_write_data;
wire [IQ_BIT_WIDTH-1:0] sin_request_data = sin_write_queued ?
    sin_queued_data : sin_table_write_data;

wire same_write_address = (cos_request_address == sin_request_address);
wire cos_write = cos_write_request && (!sin_write_request || same_write_address ||
                                       cos_write_queued || !sin_write_queued);
wire sin_write = sin_write_request && (!cos_write_request || same_write_address ||
                                       !cos_write);

always @(posedge clk) begin
  cos_write_pair_delay <= {cos_table_write_address, cos_table_write_data};
  sin_write_pair_delay <= {sin_table_write_address, sin_table_write_data};
  rst_delay <= rst;

  if (rst) begin
    cos_write_queued <= 0;
    sin_write_queued <= 0;
  end else begin
    // a new pair waits if it is not written now, or if the queued one is
    if (cos_write_new && (!cos_write || cos_write_queued)) begin
      cos_write_queued <= 1;
      cos_queued_address <= cos_table_write_address[QUARTER_ADDR_BIT_WIDTH-1:0];
      cos_queued_data <= cos_table_write_data;
    end else if (cos_write) begin
      cos_write_queued <= 0;
    end
    if (sin_write_new && (!sin_write || sin_write_queued)) begin
      sin_write_queued <= 1;
      sin_queued_address <= sin_table_write_address[QUARTER_ADDR_BIT_WIDTH-1:0];
      sin_queued_data <= sin_table_write_data;
    end else if (sin_write) begin
      sin_write_queued <= 0;
    end
  end
end

cos_sin_table_ram # (
  .DATA_WIDTH(IQ_BIT_WIDTH),
  .ADDRESS_WIDTH(QUARTER_ADDR_BIT_WIDTH)
) cos_sin_table_ram_i (
  .clk(clk),
  .rst(rst),

  .write_address(cos_write ? cos_request_address : sin_request_address),
  .write_data({cos_request_data, sin_request_data}),
  .write_mask({cos_write, sin_write}),

  .read_address(quarter_read_address),
  .read_data({cos_quarter_data, sin_quarter_data})
);

endmodule

// One memory of 2^ADDRESS_WIDTH words of 2*DATA_WIDTH bits, with one write port
// that has a write mask of one bit per half, and one read port. It is written
// as its two halves, two sdpram_one_clk (the repository's RAM model) that share
// the write address and the read address; the mask bits are their write enables.
module cos_sin_table_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 9
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [2*DATA_WIDTH-1:0] write_data,
  input wire [1:0] write_mask,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  output wire [2*DATA_WIDTH-1:0] read_data
);

sdpram_one_clk # (
  .DATA_WIDTH(DATA_WIDTH),
  .ADDRESS_WIDTH(ADDRESS_WIDTH)
) high_half_sdpram_one_clk_i (
  .clk(clk),
  .rst(rst),

  .write_address(write_address),
  .write_data(write_data[2*DATA_WIDTH-1:DATA_WIDTH]),
  .write_enable(write_mask[1]),

  .read_address(read_address),
  .read_data(read_data[2*DATA_WIDTH-1:DATA_WIDTH])
);

sdpram_one_clk # (
  .DATA_WIDTH(DATA_WIDTH),
  .ADDRESS_WIDTH(ADDRESS_WIDTH)
) low_half_sdpram_one_clk_i (
  .clk(clk),
  .rst(rst),

  .write_address(write_address),
  .write_data(write_data[DATA_WIDTH-1:0]),
  .write_enable(write_mask[0]),

  .read_address(read_address),
  .read_data(read_data[DATA_WIDTH-1:0])
);

endmodule

