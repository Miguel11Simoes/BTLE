// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of the TI TMP126 (datasheet SNIS209C), for the testbenches only: three-wire SPI, what ble-tx-poc-gen's
// profile relies on.
//   - CS low, SCLK high at rest (figure 7-1: a violation is a MISMATCH); a 16-bit command word, MSB first, in on SCLK rising:
//     [14] CRC enable (must be 0 here), [9] auto-increment (must be 0), [8] 1: read, [7:0] the sub-address; then 16-bit data
//     words, in on rising and latched after the 16th (a write), or out from the falling edge after the command's last rising
//     (a read), MSB first; SIO high impedance after CS rises and during writes (8.5.2.1.5);
//   - the master drives SIO through an open-drain pin: if it pulls SIO low while this drives it, the net goes unknown, a MISMATCH;
//   - 00h Temp_Result: 14 bits in [15:2], two's complement, 1/32 degC per LSB, the low 2 bits 0, 0 until the first conversion;
//   - 03h Configuration, reset 0006h: bit 4 One_Shot, bit 3 Mode (1: shutdown), bits 2:0 the period;
//   - after reset: continuous conversions (the period, 1 s at reset); One_Shot starts one at once, the partial one discarded;
//     then shutdown, Mode = 1, One_Shot = 0 (8.4.3);
//   - the conversion takes 7.5 ms (+conv_mode=0, the maximum) or 6 ms (1, the typical), divided by +time_scale.
// Input: temps.hex, 1/16 degC, each one-shot takes the next, the continuous conversions the first; the last one stays.
// Log, as tests/tmp100_model.v's: conv <ns> <index> <hex>; read <ns> <hex> <converting>; partial <ns> <clocks>, a frame not of whole words.

`timescale 1ns/1ps
module tmp126_model (
  input  wire sclk,
  input  wire cs_n,
  inout  wire sio,
  input  wire present
);
  real time_scale = 1.0;
  integer conv_mode = 0;
  reg [15:0] config_reg = 16'h0006, temp_reg = 16'h0000;
  reg converting = 0, shut_down = 0;
  integer index = 0, fd, n_temps = 0, generation = 0, bits = 0;
  reg signed [15:0] temps [0:4095];
  reg [15:0] command = 0, shift_in = 0, shift_out = 16'hFFFF;
  reg driving = 0;
  wire reading = (bits >= 16) && command[8];
  assign sio = (driving && present) ? shift_out[15] : 1'bz;

  initial begin
    if (!$value$plusargs("time_scale=%f", time_scale)) time_scale = 1.0;
    if (!$value$plusargs("conv_mode=%d", conv_mode)) conv_mode = 0;
    fd = $fopen("tmp126.log", "w");
    $readmemh("temps.hex", temps);
    while (n_temps < 4096 && temps[n_temps] !== 16'hxxxx) n_temps = n_temps + 1;
  end

  function [15:0] result(input integer dummy);
    reg signed [15:0] t;
    begin
      t = (index < n_temps) ? temps[index] : temps[n_temps - 1];
      result = t << 3;
      result[1:0] = 0;
    end
  endfunction

  function real conv_ns(input integer dummy);
    conv_ns = ((conv_mode == 0) ? 7.5 : 6.0) * 1.0e6 / time_scale;
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
        #(1000.0e6 / time_scale);
      end
    end
  end

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

  always @(sio) if (driving && present && sio === 1'bx) begin
    $display("MISMATCH tmp126: the master drives SIO low while the sensor drives it");
    $fatal(1, "tmp126");
  end

  always @(negedge cs_n) if (present) begin
    if (sclk !== 1'b1) begin
      $display("MISMATCH tmp126: SCLK %b when CS falls", sclk);
      $fatal(1, "tmp126");
    end
    bits = 0;
    driving = 0;
  end

  always @(posedge sclk) if (cs_n === 1'b0 && present) begin
    if (driving) begin
      if (sio === 1'bx) begin
        $display("MISMATCH tmp126: the master drives SIO low while the sensor drives it");
        $fatal(1, "tmp126");
      end
    end else begin
      if (sio === 1'bx) begin
        $display("MISMATCH tmp126: SIO unknown at SCLK rising");
        $fatal(1, "tmp126");
      end
      if (bits < 16) command = {command[14:0], sio === 1'b1};
      else shift_in = {shift_in[14:0], sio === 1'b1};
    end
    bits = bits + 1;
    if (bits == 16) begin
      if (command[14] || command[9]) begin
        $display("MISMATCH tmp126: command %04x: CRC or auto-increment", command);
        $fatal(1, "tmp126");
      end
    end
    if (bits == 32 && !command[8] && command[7:0] == 8'h03) config_reg = shift_in;
  end

  always @(negedge sclk) if (cs_n === 1'b0 && present) begin
    if (bits == 16 && command[8]) begin
      case (command[7:0])
        8'h00: shift_out = temp_reg;
        8'h03: shift_out = config_reg;
        default: shift_out = 16'h0000;
      endcase
      driving = 1;
    end else if (driving) begin
      shift_out = {shift_out[14:0], 1'b1};
    end
  end

  always @(posedge cs_n) if (present) begin
    if (bits % 16 != 0) begin
      $fdisplay(fd, "partial %0.0f %0d", $realtime, bits);
      $fflush(fd);
    end
    if (driving && bits >= 32 && command[7:0] == 8'h00) begin
      $fdisplay(fd, "read %0.0f %04x %0d", $realtime, temp_reg, converting);
      $fflush(fd);
    end
    #200 driving = 0;
  end
endmodule
