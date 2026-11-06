// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of the TI TMP100 (datasheet SBOS231I), for the testbenches only:
//   - the pointer register (2 bits, the last value written stays): temperature, configuration, TLOW, THIGH;
//   - at power-up: pointer 0, configuration 0, the temperature register reads 0 until the first conversion is
//     complete, continuous conversions at 9 bits (section 7.5.2, 7.5.3);
//   - SD = 1: shuts down when the current conversion completes (7.5.3.1); OS = 1 written while in shutdown
//     starts one conversion, and back to shutdown; written at any other time it does nothing (7.5.3.6);
//   - the resolution R1 R0, 9 to 12 bits, the unused low bits of the register 0 (7.3.1, table 10); the conversion
//     time is the maximum (+conv_mode=0, 6.5) or the typical (1, table 10) divided by +time_scale;
//   - reading the configuration gives OS as the comparator's state, not the end of a conversion (7.5.3.6);
//     here always 1 (below THIGH, POL = 0);
//   - no bus timeout (the datasheet states none), no clock stretching by the device (the testbench may add it).
// Input: temps.hex, the temperatures to convert in 1/16 degC (12 bits, two's complement), in order: each one-shot
// conversion takes the next, the continuous conversions of power-up the first; when they run out the last one
// stays. Log: one line per event:
//   conv <ns> <index> <register, hex>                a conversion completed
//   read <ns> <register, hex> <converting: 0 or 1>   the temperature register read (2 bytes)
//   os_ignored <ns>                                  OS written outside shutdown
//   write_readonly <ns>                              a byte written with the pointer on the temperature

`timescale 1ns/1ps
module tmp100_model #
(
  parameter [6:0] ADDRESS = 7'h48
) (
  inout  wire scl,
  inout  wire sda,
  input  wire present               // 0: it never acknowledges (disconnected)
);
  real time_scale = 1.0;
  integer conv_mode = 0;
  reg [1:0] pointer = 0;
  reg [7:0] config_reg = 8'h00;
  reg [15:0] temp_reg = 16'h0000, tlow_reg = 16'h4B00, thigh_reg = 16'h5000;
  reg converting = 0, shut_down = 0, one_shot = 0;
  integer index = 0, fd, n_temps = 0;
  reg signed [15:0] temps [0:4095];
  wire rx_strobe, rx_first, tx_strobe, start_strobe, stop_strobe, addressed, rw;
  wire [7:0] rx_byte;
  reg [7:0] tx_byte = 8'hFF;
  reg tx_second = 0;
  integer rx_count = 0;
  reg [7:0] rx_msb = 0;

  i2c_slave_model #(.ADDRESS(ADDRESS), .STRETCH(1)) slave_i (
    .scl(scl), .sda(sda), .ack_enable(present), .tx_byte(tx_byte),
    .rx_strobe(rx_strobe), .rx_first(rx_first), .rx_byte(rx_byte), .tx_strobe(tx_strobe),
    .start_strobe(start_strobe), .stop_strobe(stop_strobe), .addressed(addressed), .rw(rw));

  initial begin
    if (!$value$plusargs("time_scale=%f", time_scale)) time_scale = 1.0;
    if (!$value$plusargs("conv_mode=%d", conv_mode)) conv_mode = 0;
    fd = $fopen("tmp100.log", "w");
    $readmemh("temps.hex", temps);
    while (n_temps < 4096 && temps[n_temps] !== 16'hxxxx) n_temps = n_temps + 1;
  end

  function real conv_ns(input integer dummy);
    real ms;
    begin
      case (config_reg[6:5])
        2'd0: ms = (conv_mode == 0) ? 75.0 : 40.0;
        2'd1: ms = (conv_mode == 0) ? 150.0 : 80.0;
        2'd2: ms = (conv_mode == 0) ? 300.0 : 160.0;
        default: ms = (conv_mode == 0) ? 600.0 : 320.0;
      endcase
      conv_ns = ms * 1.0e6 / time_scale;
    end
  endfunction

  function [15:0] to_register(input integer dummy);
    reg signed [15:0] t;
    begin
      t = (index < n_temps) ? temps[index] : temps[n_temps - 1];
      to_register = t << 4;                       // T11..T0 on top
      case (config_reg[6:5])
        2'd0: to_register[6:0] = 0;
        2'd1: to_register[5:0] = 0;
        2'd2: to_register[4:0] = 0;
        default: to_register[3:0] = 0;
      endcase
    end
  endfunction

  // the conversions: continuous until SD = 1 takes effect, then one per OS
  initial begin : conversions
    reg [15:0] result;
    reg was_one_shot;
    was_one_shot = 0;
    #1;
    forever begin
      converting = 1;
      shut_down = 0;
      result = to_register(0);
      #(conv_ns(0));
      temp_reg = result;
      $fdisplay(fd, "conv %0.0f %0d %04x", $realtime, index, temp_reg);
      $fflush(fd);
      if (was_one_shot) index = index + 1;
      converting = 0;
      if (config_reg[0]) begin
        shut_down = 1;
        wait (one_shot);
        one_shot = 0;
        was_one_shot = 1;
      end else begin
        was_one_shot = 0;
      end
    end
  end

  always @(posedge start_strobe) tx_second = 0;

  always @(posedge rx_strobe) begin
    if (rx_first) begin
      pointer = rx_byte[1:0];
      rx_count = 0;
    end else begin
      if (pointer == 2'd1) begin                  // the configuration: one byte
        if (rx_byte[7]) begin
          if (shut_down && rx_byte[0]) one_shot = 1;
          else begin $fdisplay(fd, "os_ignored %0.0f", $realtime); $fflush(fd); end
        end
        config_reg = {1'b1, rx_byte[6:0]};
      end else if (rx_count == 0) begin
        if (pointer == 2'd0) begin $fdisplay(fd, "write_readonly %0.0f", $realtime); $fflush(fd); end
        rx_msb = rx_byte;
        rx_count = 1;
      end else begin
        if (pointer == 2'd2) tlow_reg = {rx_msb, rx_byte};
        if (pointer == 2'd3) thigh_reg = {rx_msb, rx_byte};
        rx_count = 0;
      end
    end
  end

  always @(posedge tx_strobe) begin
    case (pointer)
      2'd0: begin
        tx_byte = tx_second ? temp_reg[7:0] : temp_reg[15:8];
        if (tx_second) begin $fdisplay(fd, "read %0.0f %04x %0d", $realtime, temp_reg, converting); $fflush(fd); end
        tx_second = !tx_second;
      end
      2'd1: tx_byte = config_reg;
      2'd2: begin tx_byte = tx_second ? tlow_reg[7:0] : tlow_reg[15:8]; tx_second = !tx_second; end
      default: begin tx_byte = tx_second ? thigh_reg[7:0] : thigh_reg[15:8]; tx_second = !tx_second; end
    endcase
  end
endmodule
