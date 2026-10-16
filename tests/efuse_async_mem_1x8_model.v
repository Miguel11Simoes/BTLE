// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of efuse_async_mem_1x8, the 8-bit asynchronous eFuse block of the GF180MCU eFuse
// compiler (github.com/egorxe/gf180_efuse_compiler, wrapper efuse_async_mem; the macro itself and its
// own behaviour model of the array are in results/otp/gf180-efuse/). Written from the wrapper's
// documented behaviour, for the testbenches of ble-tx-min only (never synthesised: the area flow
// reads verilog/ only):
//   - reset_n low: ready is 0 and prog is inhibited (the wrapper's NAND of reset_n and prog);
//   - reset_n rising: the fuses are sensed into the output latches; out and ready within 10 ns;
//   - prog[i] = 1 for at least 50 us (Tprog) with reset_n high blows fuse i, read as 1 from the next
//     reset on; a shorter pulse leaves it intact (reported, as it would be a marginal fuse on silicon);
//   - before the first sense, out is unknown.
// +efuse_init=<hex> sets the initial fuses of every instance (default 0: an unprogrammed chip).

`timescale 1ns/1ps
module efuse_async_mem_1x8 (
  output reg       ready,
  input  wire      reset_n,
  output reg [7:0] out,
  input  wire [7:0] prog
);
  localparam real T_PROG_NS = 50000.0;
  reg [7:0] fuses;
  real since [0:7];
  integer i;
  reg [7:0] init;

  initial begin
    if ($value$plusargs("efuse_init=%h", init)) fuses = init; else fuses = 8'h00;
    ready = 1'b0;
    out = 8'hxx;
    for (i = 0; i < 8; i = i + 1) since[i] = -1.0;
  end

  // programming: a fuse blows when its prog bit falls after Tprog with reset_n high
  always @(prog or reset_n) begin
    for (i = 0; i < 8; i = i + 1) begin
      if (reset_n === 1'b1 && prog[i] === 1'b1) begin
        if (since[i] < 0.0) since[i] = $realtime;
      end else if (since[i] >= 0.0) begin
        if ($realtime - since[i] >= T_PROG_NS) fuses[i] = 1'b1;
        else $display("efuse %m: prog[%0d] held %0.0f ns < Tprog: fuse not blown", i, $realtime - since[i]);
        since[i] = -1.0;
      end
    end
  end

  // sensing
  always @(negedge reset_n) ready = 1'b0;
  always @(posedge reset_n) begin
    #5;
    if (reset_n === 1'b1) begin
      out = fuses;
      ready = 1'b1;
    end
  end
endmodule
