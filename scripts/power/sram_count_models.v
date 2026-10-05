// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// RAM models that count their accesses, for run_sram_energy.sh. Each behaves
// as the model it replaces and, at the end of the simulation, prints one line
//   SRAMCOUNT <instance> <model> <words>x<bits> clocks <n> writes <n> reads <n> both <n>
// counted on the edges of its clock (for sdpram_two_clk, writes on the write
// clock and reads on the read clock, each with its own clock count).
//
//   sdpram_one_clk, sdpram_two_clk (verilog/): two ports, as a 1RW1R macro
//     drives them: a write in each clock with write_enable, a read in EVERY
//     clock of the read port (the model has no read enable; upstream's tables
//     and packet buffer read on every clock).
//   pdu_buffer_ram (btle_tx.v of ble-tx-pdu), sin_table_ram (vco.v of
//     ble-tx-sin2 and ble-tx-pdu): one port, as a 1RW macro: pdu_buffer_ram
//     writes with write_enable, reads with read_enable, and is deselected in
//     the other clocks; sin_table_ram writes with write_enable and reads in
//     every other clock (its macro is always selected). "both" counts clocks
//     with a write and a read: none in a one-port memory.
// pdu_buffer_ram also prints, at the end, what its macro holds and sees while
// deselected, for run_sram_idle.sh:
//   PDUMEM <instance> <word 0> ... <word N-1>   (hex; xx for a word never written)
//   PDUIN <instance> address <a> data <d>       (the macro's address input in a
//                                                clock without a write, the read
//                                                address, and its data input)
// The runner renames the repository's definitions of these modules, so that
// these ones are used; for the upstream reference it adds the suffix _ref to
// every module name here.

`timescale 1ns / 1ps

module sdpram_one_clk #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 11
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  output reg [DATA_WIDTH-1:0] read_data
);

reg [DATA_WIDTH-1:0] memory [((1<<ADDRESS_WIDTH)-1):0];
integer clocks = 0, writes = 0, reads = 0;

always @ (posedge clk) begin
  clocks = clocks + 1;
  reads = reads + 1;
  if (write_enable === 1'b1) writes = writes + 1;
  if (write_enable) begin
    memory[write_address] <= write_data;
  end
  read_data <= memory[read_address];
end

final $display("SRAMCOUNT %m sdpram_one_clk %0dx%0d clocks %0d writes %0d reads %0d both %0d",
               1 << ADDRESS_WIDTH, DATA_WIDTH, clocks, writes, reads, writes);

endmodule

module sdpram_two_clk #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 11
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire clkb,
  input wire [ADDRESS_WIDTH-1:0] read_address,
  output reg [DATA_WIDTH-1:0] read_data
);

reg [DATA_WIDTH-1:0] memory [((1<<ADDRESS_WIDTH)-1):0];
integer write_clocks = 0, read_clocks = 0, writes = 0, reads = 0;

always @ (posedge clk) begin
  write_clocks = write_clocks + 1;
  if (write_enable === 1'b1) writes = writes + 1;
  if (write_enable) begin
    memory[write_address] <= write_data;
  end
end

always @ (posedge clkb) begin
  read_clocks = read_clocks + 1;
  reads = reads + 1;
  read_data <= memory[read_address];
end

final $display("SRAMCOUNT %m sdpram_two_clk %0dx%0d clocks %0d writes %0d reads %0d both %0d read_clocks %0d",
               1 << ADDRESS_WIDTH, DATA_WIDTH, write_clocks, writes, reads, 0, read_clocks);

endmodule

module pdu_buffer_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 8
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  input wire read_enable,
  output reg [DATA_WIDTH-1:0] read_data
);

reg [DATA_WIDTH-1:0] memory [((1<<ADDRESS_WIDTH)-1):0];
integer clocks = 0, writes = 0, reads = 0, both = 0;

always @ (posedge clk) begin
  clocks = clocks + 1;
  if (write_enable === 1'b1) writes = writes + 1;
  if (read_enable === 1'b1) reads = reads + 1;
  if (write_enable === 1'b1 && read_enable === 1'b1) both = both + 1;
  if (write_enable) begin
    memory[write_address] <= write_data;
  end
  // as the repository's model (sdpram_one_clk with one address): pdu_buffer
  // takes read_data only in the clock after a read
  read_data <= memory[write_enable ? write_address : read_address];
end

final $display("SRAMCOUNT %m pdu_buffer_ram %0dx%0d clocks %0d writes %0d reads %0d both %0d",
               1 << ADDRESS_WIDTH, DATA_WIDTH, clocks, writes, reads, both);

integer word_shown;
final begin
  $write("PDUMEM %m");
  for (word_shown = 0; word_shown < (1 << ADDRESS_WIDTH); word_shown = word_shown + 1)
    $write(" %02h", memory[word_shown]);
  $write("\n");
  $display("PDUIN %m address %0d data %0d", read_address, write_data);
end

endmodule

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
  output reg [DATA_WIDTH-1:0] read_data
);

reg [DATA_WIDTH-1:0] memory [((1<<ADDRESS_WIDTH)-1):0];
integer clocks = 0, writes = 0, reads = 0;

always @ (posedge clk) begin
  clocks = clocks + 1;
  if (write_enable === 1'b1) writes = writes + 1;
  else reads = reads + 1;
  if (write_enable) begin
    memory[write_address] <= write_data;
  end
  // as the repository's model (sdpram_one_clk): it also reads in a clock with
  // a write, which the VCO does not use (see vco.v)
  read_data <= memory[read_address];
end

final $display("SRAMCOUNT %m sin_table_ram %0dx%0d clocks %0d writes %0d reads %0d both %0d",
               1 << ADDRESS_WIDTH, DATA_WIDTH, clocks, writes, reads, 0);

endmodule
