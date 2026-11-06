// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of the Maxim MAX31875 (datasheet, Internal Registers and Configuration Register), for the testbenches only:
//   - the pointer, 00h the temperature, 01h the configuration, "must be written for each I2C transaction": a read with no
//     pointer written since the last read is logged, no_pointer <ns>; a read is a write of the pointer, a repeated START, the read;
//   - the configuration, 16 bits, MSB first: D8 shutdown, D6:D5 the resolution (00 8 bits, 01 9, 10 10, 11 12; 10 at power-on),
//     D0 one-shot: "Writing a 1 to D0 while in shutdown mode immediately begins a new temperature conversion", "no effect
//     when not in shutdown"; setting D8 during a conversion: it completes, then shutdown;
//   - at power-on: 0.25 conversions per second, 10 bits; the temperature register 0 until the first;
//   - the conversion: 50 ms at 10 bits, the maximum (+conv_mode=0) or 35 ms, the typical (1), halved per bit less, divided by
//     +time_scale; two's complement, left aligned, 1/256 degC per unit, the unused low bits 0.
// Input: temps.hex, 1/16 degC, each one-shot takes the next, the automatic conversions the first; the last one stays.
// Log, as tests/tmp100_model.v's: conv <ns> <index> <hex>; read <ns> <hex> <converting>; os_ignored <ns>.

`timescale 1ns/1ps
module max31875_model #
(
  parameter [6:0] ADDRESS = 7'h48
) (
  inout  wire scl,
  inout  wire sda,
  input  wire present
);
  real time_scale = 1.0;
  integer conv_mode = 0;
  reg [1:0] pointer = 0;
  reg pointer_written = 0, read_begins = 0;
  reg [15:0] config_reg = 16'h0040, temp_reg = 16'h0000;
  reg converting = 0, shut_down = 0, one_shot = 0;
  integer index = 0, fd, n_temps = 0;
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
    fd = $fopen("max31875.log", "w");
    $readmemh("temps.hex", temps);
    while (n_temps < 4096 && temps[n_temps] !== 16'hxxxx) n_temps = n_temps + 1;
  end

  function real conv_ns(input integer dummy);
    real ms;
    begin
      ms = (conv_mode == 0) ? 50.0 : 35.0;
      case (config_reg[6:5])
        2'd0: ms = ms / 4.0;
        2'd1: ms = ms / 2.0;
        2'd2: ms = ms;
        default: ms = ms * 4.0;
      endcase
      conv_ns = ms * 1.0e6 / time_scale;
    end
  endfunction

  function [15:0] to_register(input integer dummy);
    reg signed [15:0] t;
    begin
      t = (index < n_temps) ? temps[index] : temps[n_temps - 1];
      to_register = t << 4;
      case (config_reg[6:5])
        2'd0: to_register[7:0] = 0;
        2'd1: to_register[6:0] = 0;
        2'd2: to_register[5:0] = 0;
        default: to_register[3:0] = 0;
      endcase
    end
  endfunction

  initial begin : conversions
    reg [15:0] result;
    reg was_one_shot;
    real idle_from;
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
      config_reg[0] = 0;
      was_one_shot = 0;
      idle_from = $realtime;                     // the automatic rate's rest, unless shutdown is set in it
      while (!config_reg[8] && ($realtime - idle_from < 3950.0e6 / time_scale)) #(1.0e5 / time_scale);
      if (config_reg[8]) begin
        shut_down = 1;
        wait (one_shot);
        one_shot = 0;
        was_one_shot = 1;
      end
    end
  end

  always @(posedge start_strobe) begin tx_second = 0; rx_second = 0; read_begins = 1; end

  always @(posedge rx_strobe) begin
    if (rx_first) begin
      pointer = rx_byte[1:0];
      pointer_written = 1;
      rx_second = 0;
    end else if (!rx_second) begin
      rx_msb = rx_byte;
      rx_second = 1;
    end else begin
      rx_second = 0;
      if (pointer == 2'd1) begin
        if (rx_byte[0]) begin
          if (shut_down) one_shot = 1;
          else begin $fdisplay(fd, "os_ignored %0.0f", $realtime); $fflush(fd); end
        end
        config_reg = {rx_msb, rx_byte};
      end
    end
  end

  always @(posedge tx_strobe) begin
    if (read_begins && !pointer_written) begin    // more bytes of a read in course come from the same register
      $fdisplay(fd, "no_pointer %0.0f", $realtime);
      $fflush(fd);
    end
    read_begins = 0;
    case (pointer)
      2'd0: begin
        tx_byte = tx_second ? temp_reg[7:0] : temp_reg[15:8];
        if (tx_second) begin
          $fdisplay(fd, "read %0.0f %04x %0d", $realtime, temp_reg, converting);
          $fflush(fd);
          pointer_written = 0;
        end
        tx_second = !tx_second;
      end
      2'd1: begin tx_byte = tx_second ? config_reg[7:0] : config_reg[15:8]; tx_second = !tx_second; end
      default: tx_byte = 8'hFF;
    endcase
  end
endmodule
