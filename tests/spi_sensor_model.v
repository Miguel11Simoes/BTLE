// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// A second sensor for the testbench of tag_core, not on I2C (tests/test_tag_core.py): the same RTL must serve it
// with another profile. A generic SPI temperature sensor, for the testbenches only, in the two shapes real
// parts have:
//   - COMMAND = 0, mode 0 (the Maxim MAX6675's shape): CS_n falling takes the value, then 16 bits out, most
//     significant first, on SCLK falling (the first with CS_n), sampled by the master on SCLK rising;
//   - COMMAND = 1, mode 3 (the ADI ADT7310's shape): CS_n falling, 8 bits in on SCLK rising (only 0x50, "read
//     the temperature" is accepted), then the same 16 bits out, on SCLK falling.
// Input: the 16-bit words to send, one per frame, in order, from spi_values.hex; the last one stays. It checks what
// a real part relies on: SCLK idle at its mode's level when CS_n falls (mode 3: high; mode 0: low), and
// reports a violation as a MISMATCH. Log: frame <ns> <value, hex>, per frame finished.

`timescale 1ns/1ps
module spi_sensor_model #
(
  parameter integer COMMAND = 0
) (
  input  wire sclk,
  input  wire mosi,
  input  wire cs_n,
  output wire miso
);
  reg [15:0] values [0:4095];
  reg [15:0] shift = 16'hFFFF;
  reg [7:0] command = 0;
  integer index = 0, n_values = 0, bits = 0, fd;
  reg driving = 0;
  assign miso = driving ? shift[15] : 1'bz;
  wire in_command = (COMMAND != 0) && (bits < 8);

  initial begin
    fd = $fopen("spi.log", "w");
    $readmemh("spi_values.hex", values);
    while (n_values < 4096 && values[n_values] !== 16'hxxxx) n_values = n_values + 1;
  end

  always @(negedge cs_n) begin
    if (sclk !== ((COMMAND != 0) ? 1'b1 : 1'b0)) begin
      $display("MISMATCH spi: SCLK %b when CS_n falls, mode %0d", sclk, (COMMAND != 0) ? 3 : 0);
      $fatal(1, "spi mode");
    end
    bits = 0;
    shift = values[(index < n_values) ? index : n_values - 1];
    driving = (COMMAND == 0);
  end

  always @(posedge sclk) if (cs_n === 1'b0) begin
    if (in_command) command = {command[6:0], mosi === 1'b1};
    bits = bits + 1;
  end

  always @(negedge sclk) if (cs_n === 1'b0) begin
    if (COMMAND != 0 && bits == 8) begin
      if (command !== 8'h50) begin
        $display("MISMATCH spi: command %02x, expected 50", command);
        $fatal(1, "spi command");
      end
      driving = 1;
    end else if (!in_command && bits != 0) begin
      shift = {shift[14:0], 1'b1};
    end
  end

  always @(posedge cs_n) begin
    driving = 0;
    if (bits >= ((COMMAND != 0) ? 24 : 16)) begin
      $fdisplay(fd, "frame %0.0f %04x", $realtime, values[(index < n_values) ? index : n_values - 1]);
      $fflush(fd);
      index = index + 1;
    end
  end
endmodule
