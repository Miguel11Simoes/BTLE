// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// pdu_buffer_ram of verilog/btle_tx.v (the AdvData memory, 32 x 8, one port on clkb) on the GF180MCU
// SRAM of the PDK, gf180mcu_fd_ip_sram__sram64x8m8wm1: the smallest the PDK has, 32 of its 64 words
// used (A[5] = 0). For the layout only (scripts/layout/tx_min_gf180/run.sh replaces the module of
// btle_tx.v with this one); the RTL keeps its own model.
//
// The macro (GF180MCU SRAM model): CEN, GWEN and WEN active low; a read (CEN = 0, GWEN = 1) puts
// mem[A] on Q after the clock, a write (GWEN = 0) leaves Q as it was, no access holds Q. adv_pdu_buffer
// samples read_data only in the clock after a read and never writes in a reading clock, so this is
// the model's behaviour (sdpram_one_clk reads every clock; the extra reads are never sampled).
// Tcyc = 55.6 ns: clkb at 18 MHz or slower.
module pdu_buffer_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 5
) (
  input wire clk,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  input wire read_enable,
  output wire [DATA_WIDTH-1:0] read_data
);

wire [ADDRESS_WIDTH-1:0] address = write_enable ? write_address : read_address;

gf180mcu_fd_ip_sram__sram64x8m8wm1 sram_i (
  .CLK(clk),
  .CEN(!(write_enable || read_enable)),
  .GWEN(!write_enable),
  .WEN({DATA_WIDTH{!write_enable}}),
  .A({{(6-ADDRESS_WIDTH){1'b0}}, address}),
  .D(write_data),
  .Q(read_data)
);

endmodule
