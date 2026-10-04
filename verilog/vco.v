// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-10-04 by Miguel Simões: only the first quarter of the SINE table is stored, in one
// memory with one port (the VCO of ble-tx-sin2), rewritten in every clock the port is free.
// See CHANGES.md.

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
// quarter of the SINE table alone (addresses 0..90 degrees, excluding 90). At
// the offset x into a quadrant the VCO needs sin x and cos x = sin(90 - x):
// entry a, at the offset, and entry b, at minus the offset. cos 0 = sin 90 is
// not in the quarter: it is kept in a register, written by the cosine table's
// address 0, the only cosine entry stored. The other cosine writes are
// ignored, so the tables must satisfy cos[k] = sin[2^QUARTER_ADDR_BIT_WIDTH - k]
// for k = 1 .. 2^QUARTER_ADDR_BIT_WIDTH - 1 (the project's tables do). In the
// quadrant given by the two top bits of the phase:
//   0: cos =  b, sin =  a        1: cos = -a, sin =  b
//   2: cos = -b, sin = -a        3: cos =  a, sin = -b
// Only sine writes to the first quarter are stored.
localparam integer QUARTER_ADDR_BIT_WIDTH = SIN_COS_ADDR_BIT_WIDTH - 2;

wire signed [(VCO_BIT_WIDTH-1) : 0] next_integral_voltage_signal =
    integral_voltage_signal + voltage_signal;
wire [SIN_COS_ADDR_BIT_WIDTH-1:0] phase_address =
    integral_voltage_signal[(SIN_COS_ADDR_BIT_WIDTH-1) : 0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] quarter_offset =
    phase_address[QUARTER_ADDR_BIT_WIDTH-1:0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] next_quarter_offset =
    next_integral_voltage_signal[QUARTER_ADDR_BIT_WIDTH-1:0];
wire [QUARTER_ADDR_BIT_WIDTH-1:0] a_address = quarter_offset;
wire [QUARTER_ADDR_BIT_WIDTH-1:0] b_address = -quarter_offset;
wire [QUARTER_ADDR_BIT_WIDTH-1:0] next_b_address = -next_quarter_offset;

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
      integral_voltage_signal <= next_integral_voltage_signal;
    end
  end
end

// The memory has ONE port, and a sample needs two entries. The TX gives the
// VCO at most one sample every two clocks, never in the clock right after a
// sample or a reset, so each sample has two clocks of the port:
//   - in the clock of the sample, entry b of the NEXT phase (integral +
//     voltage_signal), read ahead; it lands in b_entry one clock later;
//   - in the clock after, entry a of the new phase, which the VCO outputs.
// In every other clock the port reads entry a again, or takes a table write,
// except in the clock after a reset (entry a of phase 0). While transmitting no
// clock is left for writes; a write waits until one is.
//
// The sine write interface is unchanged: an address and data, held until the
// next register write. Upstream rewrites the table on every clock; here the
// pair is rewritten in every clock the port is free, which leaves the same
// contents. A pair that arrives while the port is busy is written in the first
// free clock, with the data its input still holds: the pair must not change
// again before that clock.
wire sin_write_in_quarter =
    sin_table_write_address[SIN_COS_ADDR_BIT_WIDTH-1:QUARTER_ADDR_BIT_WIDTH] == 0;

reg [IQ_BIT_WIDTH-1:0] sin_write_data_delay;
reg rst_delay;

wire sin_write_ready = sin_write_in_quarter;

wire b_read = voltage_signal_valid && !rst;
wire table_write = !b_read && !voltage_signal_valid_delay1 && !rst_delay && sin_write_ready;
wire a_read = !b_read && !table_write;
wire [QUARTER_ADDR_BIT_WIDTH-1:0] table_write_address =
    sin_table_write_address[QUARTER_ADDR_BIT_WIDTH-1:0];

always @(posedge clk) begin
  sin_write_data_delay <= sin_table_write_data;
  rst_delay <= rst;
end

// cos 0 = sin 90, the cosine table's entry 0: taken one clock after its pair
// is presented, when upstream reads it back
reg cos_write_zero_delay;
reg [IQ_BIT_WIDTH-1:0] cos_write_data_delay;
reg [IQ_BIT_WIDTH-1:0] cos_zero;

always @(posedge clk) begin
  cos_write_zero_delay <= (cos_table_write_address == 0);
  cos_write_data_delay <= cos_table_write_data;
  if (cos_write_zero_delay) begin
    cos_zero <= cos_write_data_delay;
  end
end

// The entries of the phase shown. a is the memory output after a read of a,
// and a_hold after a read of b (the output moves on to the next phase) or
// after a write to entry a (the output keeps the old value: a one-port memory
// does not read while it writes). b is b_entry: the entry read ahead, or the
// value of a write to entry b; at offset 0 it is cos 0. A write to entry a or
// b shows from the next clock, as upstream: its value is the pair registered
// in the clock of the write.
wire [IQ_BIT_WIDTH-1:0] table_read_data;
wire [IQ_BIT_WIDTH-1:0] write_data_delay = sin_write_data_delay;
reg write_hit_a_delay;
reg write_hit_b_delay;
reg a_from_hold;
reg [IQ_BIT_WIDTH-1:0] a_hold;
reg [IQ_BIT_WIDTH-1:0] b_entry;
reg odd_quadrant_delay;
wire cos_negative_delay; // the two quadrant bits XORed, both registered
reg sin_negative_delay;
reg offset_zero_delay;

wire signed [IQ_BIT_WIDTH-1:0] a_value = a_from_hold ? a_hold : table_read_data;
wire signed [IQ_BIT_WIDTH-1:0] b_value = offset_zero_delay ? cos_zero : b_entry;
wire signed [IQ_BIT_WIDTH-1:0] cos_sample = odd_quadrant_delay ? a_value : b_value;
wire signed [IQ_BIT_WIDTH-1:0] sin_sample = odd_quadrant_delay ? b_value : a_value;

assign cos_negative_delay = sin_negative_delay ^ odd_quadrant_delay;
assign cos_out = cos_negative_delay ? -cos_sample : cos_sample;
assign sin_out = sin_negative_delay ? -sin_sample : sin_sample;

// Quadrant, signs and offset 0 describe the phase whose entry a the memory
// read last: the phase moves only with a sample, and the clock after one
// reads entry a.
always @(posedge clk) begin
  odd_quadrant_delay <= phase_address[QUARTER_ADDR_BIT_WIDTH];
  sin_negative_delay <= phase_address[SIN_COS_ADDR_BIT_WIDTH-1];
  offset_zero_delay <= (quarter_offset == 0);

  write_hit_a_delay <= table_write && (table_write_address == a_address);
  write_hit_b_delay <= table_write && (table_write_address == b_address);

  if (write_hit_a_delay) begin
    a_hold <= write_data_delay;
  end else if (b_read) begin
    a_hold <= a_value;
  end
  a_from_hold <= !a_read && (b_read || write_hit_a_delay || a_from_hold);

  if (voltage_signal_valid_delay1) begin
    b_entry <= table_read_data;
  end else if (write_hit_b_delay) begin
    b_entry <= write_data_delay;
  end
end

sin_table_ram # (
  .DATA_WIDTH(IQ_BIT_WIDTH),
  .ADDRESS_WIDTH(QUARTER_ADDR_BIT_WIDTH)
) sin_table_ram_i (
  .clk(clk),
  .rst(rst),

  .write_address(table_write_address),
  .write_data(sin_table_write_data),
  .write_enable(table_write),

  .read_address(b_read ? next_b_address : a_address),
  .read_data(table_read_data)
);

endmodule

// One memory of 2^ADDRESS_WIDTH words of DATA_WIDTH bits, with ONE port. A
// one-port macro takes write_address in a clock with a write (write_enable),
// in which it keeps its output, and read_address in the others, in which it
// reads. It is modelled by sdpram_one_clk (the repository's RAM model), which
// also reads in a clock with a write: there read_address is entry a of the
// phase shown, and the VCO shows the memory output only while it holds that
// entry, unchanged (after a write to it, a_hold), so the VCO outputs are those
// it has with the macro.
module sin_table_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 9
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  output wire [DATA_WIDTH-1:0] read_data
);

sdpram_one_clk # (
  .DATA_WIDTH(DATA_WIDTH),
  .ADDRESS_WIDTH(ADDRESS_WIDTH)
) sdpram_one_clk_i (
  .clk(clk),
  .rst(rst),

  .write_address(write_address),
  .write_data(write_data),
  .write_enable(write_enable),

  .read_address(read_address),
  .read_data(read_data)
);

endmodule
