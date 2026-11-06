// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// The I2C slave under the models of the sensor and of the EEPROM (tests/tmp100_model.v,
// tests/eeprom_24aa02e48_model.v): behaviour, for the testbenches only. Its state is not reset with the
// DUT, as a real slave's is not: a master that stops clocking in the middle of a read leaves it driving SDA.
//   - START and STOP from SDA edges with SCL high, from any state;
//   - after START, the address byte: an acknowledge if the address matches (ADDRESS_MASK: the bits compared)
//     and ack_enable is high;
//   - a write: each byte received is given on rx_byte with a pulse of rx_strobe (rx_first on the first);
//     the acknowledge follows ack_enable;
//   - a read: tx_byte is taken at each byte's start, after a pulse of tx_strobe; the master's acknowledge
//     decides if another byte follows. SDA changes +t_out_ns after SCL falls (T_AA, valid until the next fall);
//   - with STRETCH = 1, +stretch_ns (0: off): SCL held low so long after SCL falls, on every bit with
//     +stretch_every_bit=1, else after the acknowledge bits only.

`timescale 1ns/1ps
module i2c_slave_model #
(
  parameter [6:0] ADDRESS = 7'h48,
  parameter [6:0] ADDRESS_MASK = 7'h7F,
  parameter integer STRETCH = 0
) (
  inout  wire scl,
  inout  wire sda,
  input  wire ack_enable,
  input  wire [7:0] tx_byte,
  output reg  rx_strobe,
  output reg  rx_first,
  output reg  [7:0] rx_byte,
  output reg  tx_strobe,
  output reg  start_strobe,
  output reg  stop_strobe,
  output reg  addressed,
  output reg  rw
);
  localparam IDLE = 0, ADDR = 1, ACK_ADDR = 2, RX = 3, ACK_RX = 4, TX = 5, ACK_TX = 6;
  integer state = IDLE;
  integer bits = 0;
  reg [7:0] shift = 0;
  reg sda_low = 0, scl_low = 0, master_ack = 0, first = 0;
  reg [7:0] out_byte = 8'hFF;
  integer generation = 0;           // START and STOP cancel what a falling edge has scheduled

  assign sda = sda_low ? 1'b0 : 1'bz;
  assign scl = scl_low ? 1'b0 : 1'bz;

  real t_out_ns = 300.0, stretch_ns = 0.0;
  integer stretch_every_bit = 0;

  initial begin
    rx_strobe = 0; rx_first = 0; rx_byte = 0; tx_strobe = 0; start_strobe = 0; stop_strobe = 0; addressed = 0; rw = 0;
    if (!$value$plusargs("t_out_ns=%f", t_out_ns)) t_out_ns = 300.0;
    if (STRETCH != 0) begin
      if (!$value$plusargs("stretch_ns=%f", stretch_ns)) stretch_ns = 0.0;
      if (!$value$plusargs("stretch_every_bit=%d", stretch_every_bit)) stretch_every_bit = 0;
    end
  end

  always @(negedge sda) if (scl === 1'b1) begin     // START (also a repeated one)
    generation = generation + 1;
    state = ADDR; bits = 0; addressed = 0; sda_low = 0;
    start_strobe = 1; #1 start_strobe = 0;
  end

  always @(posedge sda) if (scl === 1'b1) begin     // STOP
    generation = generation + 1;
    state = IDLE; addressed = 0; sda_low = 0;
    stop_strobe = 1; #1 stop_strobe = 0;
  end

  always @(posedge scl) begin
    case (state)
      ADDR, RX: begin shift = {shift[6:0], sda === 1'b1}; bits = bits + 1; end
      ACK_TX: master_ack = (sda === 1'b0);
      default: ;
    endcase
  end

  task drive_sda(input reg low, input integer gen);
    begin
      #(t_out_ns);
      if (gen == generation) sda_low = low;
    end
  endtask

  task next_tx_byte;
    begin
      tx_strobe = 1; #0 out_byte = tx_byte; tx_strobe = 0;
    end
  endtask

  always @(negedge scl) begin : falling
    integer gen;
    reg ack_slot;
    gen = generation;
    ack_slot = 0;
    case (state)
      ADDR: if (bits == 8) begin
        rw = shift[0];
        if (((shift[7:1] ^ ADDRESS) & ADDRESS_MASK) == 0 && ack_enable) begin
          addressed = 1;
          state = ACK_ADDR;
          ack_slot = 1;
          drive_sda(1'b1, gen);
        end else begin
          state = IDLE;
        end
      end
      ACK_ADDR: begin
        bits = 0;
        first = 1;
        if (rw) begin
          next_tx_byte;
          state = TX;
          drive_sda(!out_byte[7], gen);
        end else begin
          state = RX;
          drive_sda(1'b0, gen);
        end
      end
      RX: if (bits == 8) begin
        rx_byte = shift; rx_first = first; first = 0;
        rx_strobe = 1; #0 rx_strobe = 0;
        if (ack_enable) begin
          state = ACK_RX;
          ack_slot = 1;
          drive_sda(1'b1, gen);
        end else begin
          state = IDLE;
        end
      end
      ACK_RX: begin
        bits = 0;
        state = RX;
        drive_sda(1'b0, gen);
      end
      TX: begin
        bits = bits + 1;
        if (bits < 8) begin
          drive_sda(!out_byte[7 - bits], gen);
        end else begin
          state = ACK_TX;
          drive_sda(1'b0, gen);
        end
      end
      ACK_TX: begin
        if (master_ack) begin
          bits = 0;
          next_tx_byte;
          state = TX;
          drive_sda(!out_byte[7], gen);
        end else begin
          state = IDLE;
        end
      end
      default: ;
    endcase
    if (stretch_ns > 0.0 && (stretch_every_bit != 0 || ack_slot) && state != IDLE) begin
      scl_low = 1;
      #(stretch_ns);
      scl_low = 0;
    end
  end
endmodule
