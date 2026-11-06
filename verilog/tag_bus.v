// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// The layer of bits under tag_core's sequencer (ble-tx-poc): one command at a time, req held until done.
// START, STOP, WRITE a byte or READ a byte, chosen by the profile on one of:
//   - I2C: SCL and SDA are open-drain (the pins only pull low; the pull-ups are external), with clock
//     stretching: a phase that needs SCL high waits for it. WRITE's ninth bit is the slave's
//     acknowledge (acked); READ's ninth is the master's (read_ack).
//   - SPI, mode 0 or 3 (cpol: the clock's idle level): SCLK on the SCL pin and MOSI on the SDA pin, still
//     open-drain, CS_n and MISO on their own pins; START is CS_n falling, STOP is CS_n rising, no ninth
//     bit. SDA changes only while SCL is low, so an I2C device on the same two wires (the profile's
//     EEPROM) never sees a START.
//   - an ADC (ADC_EN = 1): the pins stay idle; START pulses adc_start and waits for adc_done, READ gives
//     the result, most significant bit first. adc_done must fall by the clock after adc_start rises, and
//     stay high once the result is valid, until the next adc_start.
// A bit is four phases, one per bus_en clock: SCL = bus_en / 4 (16 kHz with bus_en at 64 kHz):
//   0: SCL is low; SDA changes
//   1: SCL rises
//   2: SCL is high (or waits for it): SDA, or MISO, is sampled
//   3: SCL falls
// So SDA changes a phase away from each edge of SCL, what I2C asks of a master at any clock ratio.
// While a phase waits, stalled is high; tag_core times it out and pulses abort, which releases the pins.
// The pins' inputs are asynchronous to clk: two flip-flops each.

`define KEEP_FOR_DBG (*mark_debug="true",DONT_TOUCH="TRUE"*)

`timescale 1ns / 1ps
module tag_bus #
(
  parameter integer ADC_EN = 0,
  parameter integer ADC_BITS = 12
) (
  input  wire clk,
  input  wire rst,
  input  wire bus_en,

  input  wire spi,
  input  wire cpol,
  input  wire adc,

  input  wire [1:0] cmd,
  input  wire req,
  input  wire [7:0] write_data,
  input  wire read_ack,
  input  wire abort,
  output wire done,
  output reg  acked,
  output wire stalled,
  output wire rx_valid,
  output wire rx_bit,

  input  wire scl_i,
  input  wire sda_i,
  input  wire miso_i,
  `KEEP_FOR_DBG output reg scl_oe,
  `KEEP_FOR_DBG output reg sda_oe,
  output reg  cs_n,

  output reg  adc_start,
  input  wire adc_done,
  input  wire [(ADC_BITS-1):0] adc_data
);

localparam [1:0] CMD_START = 2'd0,      // and CMD_STOP = 1
                 CMD_WRITE = 2'd2,
                 CMD_READ  = 2'd3;

`KEEP_FOR_DBG reg active;
`KEEP_FOR_DBG reg [1:0] op;
`KEEP_FOR_DBG reg [1:0] phase;
reg [3:0] bits_left;
reg [8:0] shift;                  // the bits to send, the next on top; 1: SDA released

(* ASYNC_REG = "TRUE" *) reg [1:0] scl_sync;
(* ASYNC_REG = "TRUE" *) reg [1:0] sda_sync;
(* ASYNC_REG = "TRUE" *) reg [1:0] miso_sync;
wire scl = scl_sync[1];
wire sda = sda_sync[1];
wire miso = miso_sync[1];

wire op_bits = op[1];             // WRITE or READ
wire op_read = op == CMD_READ;
wire op_start = op == CMD_START;
wire last_bit = bits_left == 4'd1;
wire ack_bit = !(spi || adc) && last_bit;
wire adc_bit;

assign stalled = active && (phase == 2'd2) && (
                   op_bits  ? (!adc && !scl) :
                   op_start ? (adc ? !adc_done : (!spi && !(scl && sda))) :
                              (!adc && !spi && !scl));
assign done = bus_en && active && (phase == 2'd3) && (!op_bits || last_bit);
assign rx_valid = bus_en && active && op_read && (phase == 2'd2) && !stalled && !ack_bit;
assign rx_bit = adc ? adc_bit : (spi ? miso : sda);

always @ (posedge clk) begin
  scl_sync <= {scl_sync[0], scl_i};
  sda_sync <= {sda_sync[0], sda_i};
  miso_sync <= {miso_sync[0], miso_i};

  if (rst || abort) begin
    active <= 1'b0;
    acked <= 1'b0;
    scl_oe <= 1'b0;
    sda_oe <= 1'b0;
    cs_n <= 1'b1;
    adc_start <= 1'b0;
  end else if (bus_en) begin
    if (!active) begin
      if (req) begin
        active <= 1'b1;
        op <= cmd;
        phase <= 2'd0;
        bits_left <= (spi || adc) ? 4'd8 : 4'd9;
        shift <= (cmd == CMD_WRITE) ? {write_data, 1'b1} : {8'hFF, !read_ack};
      end
    end else if (!stalled) begin
      phase <= phase + 2'd1;
      if (phase == 2'd3 && (!op_bits || last_bit)) begin
        active <= 1'b0;
      end
      if (op_bits) begin
        case (phase)
          2'd0: if (!adc) sda_oe <= !shift[8];
          2'd1: if (!adc) scl_oe <= 1'b0;
          2'd2: if (ack_bit) acked <= !sda;
          default: begin
            if (!adc) scl_oe <= 1'b1;
            shift <= {shift[7:0], 1'b1};
            bits_left <= bits_left - 4'd1;
          end
        endcase
      end else if (adc) begin
        if (op_start) begin
          adc_start <= (phase == 2'd0);
        end
      end else if (spi) begin
        if (op_start) begin
          case (phase)
            2'd0: if (cs_n) scl_oe <= !cpol;   // the clock at its idle level, CS_n still high
            2'd1: cs_n <= 1'b0;
            2'd2: scl_oe <= 1'b1;
            default: ;
          endcase
        end else begin
          case (phase)
            2'd0: sda_oe <= 1'b0;
            2'd1: cs_n <= 1'b1;
            2'd2: scl_oe <= 1'b0;
            default: ;
          endcase
        end
      end else if (op_start) begin             // also a repeated START: SCL low on entry
        case (phase)
          2'd0: sda_oe <= 1'b0;
          2'd1: scl_oe <= 1'b0;
          2'd2: sda_oe <= 1'b1;                // SDA falls with SCL high
          default: scl_oe <= 1'b1;
        endcase
      end else begin                           // STOP: SCL low on entry
        case (phase)
          2'd0: sda_oe <= 1'b1;
          2'd1: scl_oe <= 1'b0;
          2'd2: sda_oe <= 1'b0;                // SDA rises with SCL high
          default: ;
        endcase
      end
    end
  end
end

generate
if (ADC_EN != 0) begin : gen_adc
  reg [15:0] adc_shift;                        // the result, left aligned
  wire [(ADC_BITS+15):0] adc_wide = {adc_data, 16'd0};
  always @ (posedge clk) begin
    if (bus_en && active) begin
      if (op_start && phase == 2'd2 && adc_done) begin
        adc_shift <= adc_wide[(ADC_BITS+15):ADC_BITS];
      end else if (op_bits && phase == 2'd3) begin
        adc_shift <= {adc_shift[14:0], 1'b0};
      end
    end
  end
  assign adc_bit = adc_shift[15];
  wire unused_adc_wide = &{1'b0, adc_wide[(ADC_BITS-1):0]};
end else begin : gen_no_adc
  assign adc_bit = 1'b0;
  wire unused_adc_data = &{1'b0, adc_data};
end
endgenerate

endmodule
