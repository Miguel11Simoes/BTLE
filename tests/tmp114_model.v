// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of the TI TMP114 (datasheet SNIS214E), for the testbenches only: what ble-tx-poc-gen's profile relies on.
//   - the registers (8.6): 00h Temp_Result, 16 bits, two's complement, 1/128 degC per unit, 0 until the first conversion;
//     03h Configuration, reset 0004h: bit 4 OS, bit 3 Mode (1: shutdown), bits 2:0 the conversion period;
//   - the frames (8.5.4): the control byte, its bit 7 auto-increment (not modelled: 0 expected), the pointer below;
//     a write's 16-bit word MSB first; a read, MSB first, of the register the pointer selects;
//   - after reset: continuous conversions (Mode = 0), one per Conv_Period; OS = 1 starts one conversion at once, the
//     partial one discarded, then shutdown, OS cleared, Mode = 1 (8.4.2.1);
//   - the conversion takes 7.5 ms (+conv_mode=0, the maximum, 7.5) or 6.4 ms (1, the typical), divided by +time_scale;
//   - no clock stretching. The 30 ms time-out of 8.5.4.5 is checked: a violation is a MISMATCH.
// Input: temps.hex, 1/16 degC, each one-shot takes the next, the continuous conversions the first; the last one stays.
// Log, as tests/tmp100_model.v's: conv <ns> <index> <hex>; read <ns> <hex> <converting>.

`timescale 1ns/1ps
module tmp114_model #
(
  parameter [6:0] ADDRESS = 7'h48
) (
  inout  wire scl,
  inout  wire sda,
  input  wire present
);
  real time_scale = 1.0;
  integer conv_mode = 0;
  reg [7:0] pointer = 0;
  reg [15:0] config_reg = 16'h0004, temp_reg = 16'h0000;
  reg converting = 0, shut_down = 0;
  integer index = 0, fd, n_temps = 0, generation = 0;
  reg signed [15:0] temps [0:4095];
  wire rx_strobe, rx_first, tx_strobe, start_strobe, stop_strobe, addressed, rw;
  wire [7:0] rx_byte;
  reg [7:0] tx_byte = 8'hFF;
  reg tx_second = 0, rx_second = 0;
  reg [7:0] rx_msb = 0;

  i2c_slave_model #(.ADDRESS(ADDRESS), .STRETCH(0)) slave_i (
    .scl(scl), .sda(sda), .ack_enable(present), .tx_byte(tx_byte),
    .rx_strobe(rx_strobe), .rx_first(rx_first), .rx_byte(rx_byte), .tx_strobe(tx_strobe),
    .start_strobe(start_strobe), .stop_strobe(stop_strobe), .addressed(addressed), .rw(rw));

  initial begin
    if (!$value$plusargs("time_scale=%f", time_scale)) time_scale = 1.0;
    if (!$value$plusargs("conv_mode=%d", conv_mode)) conv_mode = 0;
    fd = $fopen("tmp114.log", "w");
    $readmemh("temps.hex", temps);
    while (n_temps < 4096 && temps[n_temps] !== 16'hxxxx) n_temps = n_temps + 1;
  end

  function [15:0] result(input integer dummy);
    reg signed [15:0] t;
    begin
      t = (index < n_temps) ? temps[index] : temps[n_temps - 1];
      result = t << 3;
    end
  endfunction

  function real conv_ns(input integer dummy);
    conv_ns = ((conv_mode == 0) ? 7.5 : 6.4) * 1.0e6 / time_scale;
  endfunction

  // continuous at reset, until the first one-shot
  initial begin : continuous
    #1;
    while (generation == 0) begin
      converting = 1;
      #(conv_ns(0));
      if (generation == 0) begin
        temp_reg = result(0);
        $fdisplay(fd, "conv %0.0f %0d %04x", $realtime, index, temp_reg);
        $fflush(fd);
        converting = 0;
        #(250.0e6 / time_scale);
      end
    end
  end

  // one-shots after the first OS
  always @(posedge config_reg[4]) begin : one_shot
    generation = generation + 1;
    converting = 1;
    shut_down = 0;
    #(conv_ns(0));
    begin
      temp_reg = result(0);
      $fdisplay(fd, "conv %0.0f %0d %04x", $realtime, index, temp_reg);
      $fflush(fd);
      index = index + 1;
      converting = 0;
      shut_down = 1;
      config_reg[4] = 0;
      config_reg[3] = 1;
    end
  end

  always @(posedge start_strobe) begin tx_second = 0; rx_second = 0; end

  always @(posedge rx_strobe) begin
    if (rx_first) begin
      pointer = rx_byte;
      rx_second = 0;
      if (rx_byte[7]) begin
        $display("MISMATCH tmp114: auto-increment set in the control byte %02x", rx_byte);
        $fatal(1, "tmp114");
      end
    end else if (!rx_second) begin
      rx_msb = rx_byte;
      rx_second = 1;
    end else begin
      rx_second = 0;
      if (pointer == 8'h03) begin
        config_reg = {rx_msb, rx_byte};
      end
    end
  end

  always @(posedge tx_strobe) begin
    case (pointer)
      8'h00: begin
        tx_byte = tx_second ? temp_reg[7:0] : temp_reg[15:8];
        if (tx_second) begin $fdisplay(fd, "read %0.0f %04x %0d", $realtime, temp_reg, converting); $fflush(fd); end
        tx_second = !tx_second;
      end
      8'h03: begin tx_byte = tx_second ? config_reg[7:0] : config_reg[15:8]; tx_second = !tx_second; end
      default: tx_byte = 8'h00;   // a non-indexed register reads 00h (8.5.4.3)
    endcase
  end

  // the time-out: SCL low for 30 ms between a START and a STOP
  real scl_fell = 0.0;
  reg in_frame = 0;
  always @(posedge start_strobe) in_frame = 1;
  always @(posedge stop_strobe) in_frame = 0;
  always @(negedge scl) scl_fell = $realtime;
  always @(posedge scl) if (in_frame && ($realtime - scl_fell > 30.0e6 / time_scale)) begin
    $display("MISMATCH tmp114: SCL low for %0.0f ns in a frame, its time-out", $realtime - scl_fell);
    $fatal(1, "tmp114");
  end
endmodule
