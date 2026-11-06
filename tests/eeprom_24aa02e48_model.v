// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// Simulation model of the Microchip 24AA02E48 (datasheet DS22124D), for the testbenches only:
//   - 256 bytes; the control code 1010, the three chip-select bits don't care (section 5.0);
//   - 0x00-0x7F free; 0x80-0xFF permanently write-protected, "write operations to this address range are
//     inhibited" (6.3), with the EUI-48 at 0xFA-0xFF, the OUI first (9.0);
//   - a write: the word address, then up to 8 bytes in the page buffer, wrapping within the page, written at the
//     STOP; during the write cycle (5 ms max, table 1-2, divided by +time_scale) it acknowledges nothing (4.5);
//   - reads at the address pointer, which increments after each byte (8.1, 8.3), 8 bits wide.
// Input: eeprom.hex (the whole array, 256 lines), or absent with present = 0. Log, one line per event:
//   start <ns>            a START on the bus (whoever it is for)
//   read <ns> <addr> <data>
//   write <ns> <addr> <data>   the master wrote data bytes (the tag never should)

`timescale 1ns/1ps
module eeprom_24aa02e48_model (
  inout  wire scl,
  inout  wire sda,
  input  wire present
);
  real time_scale = 1.0;
  reg [7:0] mem [0:255];
  reg [7:0] page [0:7];
  reg [7:0] pointer = 0, page_base = 0;
  reg [3:0] page_count = 0;
  reg busy = 0;
  reg [7:0] tx_byte = 8'hFF;
  integer fd, k;
  wire rx_strobe, rx_first, tx_strobe, start_strobe, stop_strobe, addressed, rw;
  wire [7:0] rx_byte;

  i2c_slave_model #(.ADDRESS(7'b1010000), .ADDRESS_MASK(7'b1111000)) slave_i (
    .scl(scl), .sda(sda), .ack_enable(present && !busy), .tx_byte(tx_byte),
    .rx_strobe(rx_strobe), .rx_first(rx_first), .rx_byte(rx_byte), .tx_strobe(tx_strobe),
    .start_strobe(start_strobe), .stop_strobe(stop_strobe), .addressed(addressed), .rw(rw));

  initial begin
    if (!$value$plusargs("time_scale=%f", time_scale)) time_scale = 1.0;
    fd = $fopen("eeprom.log", "w");
    $readmemh("eeprom.hex", mem);
  end

  always @(posedge start_strobe) begin $fdisplay(fd, "start %0.0f", $realtime); $fflush(fd); end

  always @(posedge rx_strobe) begin
    if (rx_first) begin
      pointer = rx_byte;
      page_count = 0;
    end else begin
      $fdisplay(fd, "write %0.0f %02x %02x", $realtime, pointer, rx_byte); $fflush(fd);
      if (page_count == 0) page_base = pointer;
      page[pointer[2:0]] = rx_byte;
      pointer[2:0] = pointer[2:0] + 3'd1;
      if (page_count < 8) page_count = page_count + 1;
    end
  end

  always @(posedge tx_strobe) begin
    tx_byte = mem[pointer];
    $fdisplay(fd, "read %0.0f %02x %02x", $realtime, pointer, tx_byte); $fflush(fd);
    pointer = pointer + 8'd1;
  end

  always @(posedge stop_strobe) begin
    if (page_count != 0) begin
      if (!page_base[7])
        for (k = 0; k < page_count; k = k + 1)
          mem[{page_base[7:3], page_base[2:0] + k[2:0]}] = page[page_base[2:0] + k[2:0]];
      page_count = 0;
      busy = 1;
      #(5.0e6 / time_scale);
      busy = 0;
    end
  end
endmodule
