// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// The tag of ble-tx-poc-tmp100: the smallest link layer between a TI TMP100 and the AdvData of ble-tx-tag-8's packet
// (docs/Senseworks/TX_POC_TMP100.md). A state machine with no processor, no memory and no choice of sensor: one
// conversion per event at 9 bits, the sensor in shutdown between them, its two bytes sent as read, the gateway converts.
//
// All the state is one counter of ticks, t. A tick is 32.768 kHz: clk itself on the ASIC (TICK_DIV = 1), one clk in
// TICK_DIV on the FPGA (488: 16 MHz / 488 = 32.787 kHz). In the last 2^12 ticks of a period, t[11:7] is the window of 128
// ticks and t[6:0] the place in it: 32 slots of 4 ticks each, one bit of I2C per slot, so SCL runs at 8.2 kHz.
//   window  8  START 0x90 ACK 0x01 ACK 0x81 ACK STOP   configuration: SD = 1, OS = 1, 9 bits: one conversion
//   window 30  START 0x90 ACK 0x00 ACK STOP            22 windows, 82.4 ms, after the first: the 75 ms maximum is over
//   window 31  START 0x91 ACK read ACK read NACK STOP  the temperature, into sensor_r
//   the wrap   tx_start
// Nothing waits for the bus: it cannot hang. The sensor gives no flag at the end of a conversion, so the wait is fixed.
//   - At power-up the TMP100 converts continuously: the first event's write only puts it in shutdown (SBOS231I 7.5.3.6:
//     OS has no effect outside shutdown), the first packet carries the last of those conversions.
//   - No sensor, or no ACK: SDA stays at the pull-up, sensor_r reads 0xFFFF, which no reading can be (the low 4 bits of
//     the register are 0). No flag and no ACK check are needed.
//   - A reset in the middle of a frame: every event writes the configuration again and the frames recover the bus
//     (a slave holding SDA gets the clocks of the next frame, and its NACK): at most one wrong packet, then right.
// The period, start to start, is exact in ticks: 2^15 (1 s) with RATE_EN = 0, else 2^(11+rate) (rate 1..7: 125 ms to 8 s,
// rate 0: off, nothing on the bus or on the air), less advDelay, 0 to 255 ticks (0 to 7.8 ms, within the Core's 0 to
// 10 ms, Core 6.1, Vol 6 Part B 4.4.2.2): an 8-bit LFSR stepped once per event, XOR AdvA's first byte. The conversion
// happens within the period, so a shorter period does not stretch it: the shortest, 125 ms, leaves 2^12 ticks for it.
// test_mode (the FPGA's PER measurements; tied to 0 on the chip): a counter in the packet, nothing on the bus; rate 0
// clears it. The ASIC's clock switch to 16 MHz for the packet is not in this core (tag_chip.v).

`define KEEP_FOR_DBG (*mark_debug="true",DONT_TOUCH="TRUE"*)

`timescale 1ns / 1ps
module tag_fsm #
(
  parameter integer TICK_DIV = 488,       // clk clocks per tick; 1: every clock is a tick
  parameter integer RATE_EN = 0,          // 1: the period by the input rate; 0: fixed at 1 s, 3 flip-flops less
  parameter integer BCH_T = 8,            // passed to btle_tx
  parameter integer ADV_ADDRESS_OTP = 0,  // 1: AdvA from six eFuse blocks, passed to btle_tx
  parameter [47:0] ADV_ADDRESS = 48'hC10203040506,  // a random static address (two top bits 11): TxAdd = 1
  parameter [15:0] COMPANY_ID = 16'hFFFF, // passed to btle_tx
  parameter [5:0] CHANNEL = 6'd37
) (
  input  wire clk,
  input  wire rst,

  input  wire [2:0] rate,                 // RATE_EN = 1, static
  input  wire test_mode,

  // the I2C bus: scl_oe, sda_oe: pull the open-drain pin low
  input  wire sda_i,
  output reg  scl_oe,
  output reg  sda_oe,

  // ADV_ADDRESS_OTP = 1: passed to btle_tx
  input  wire [47:0] adv_address_otp_prog,
  output wire adv_address_otp_ready,

  // to the radio
  output wire signed [7:0] i,
  output wire signed [7:0] q,
  output wire iq_valid,
  output wire iq_valid_last,

  // btle_tx's debug outputs
  output wire phy_bit,
  output wire phy_bit_valid,
  output wire phy_bit_valid_last,
  output wire bit_upsample,
  output wire bit_upsample_valid,
  output wire bit_upsample_valid_last,
  output wire signed [15:0] bit_upsample_gauss_filter,
  output wire bit_upsample_gauss_filter_valid,
  output wire bit_upsample_gauss_filter_valid_last,

  // the state, for the controller's status registers
  output wire tx_start,
  output wire [15:0] sensor,              // as read: the first byte in [15:8]
  output wire [47:0] adv_address_sent
);

localparam integer T_BITS = (RATE_EN != 0) ? 18 : 15;

function [7:0] sent_first_at_lsb(input [7:0] b);  // a byte for slots numbered in the order they are sent
  sent_first_at_lsb = {b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]};
endfunction

// What SDA does in each slot of a frame, 1: released: slot 0 START, 1..8 a byte, 9 ACK, 10..17 a byte, 18 ACK, 19..26
// a byte, 27 ACK, 28 STOP. Reading, SDA is released and the master acknowledges the first byte, not the second.
localparam [28:0] FRAME_CONFIG  = {2'b11, sent_first_at_lsb(8'h81), 1'b1, sent_first_at_lsb(8'h01), 1'b1, sent_first_at_lsb(8'h90), 1'b1};
localparam [28:0] FRAME_POINTER = {2'b11, 8'hFF, 1'b1, sent_first_at_lsb(8'h00), 1'b1, sent_first_at_lsb(8'h90), 1'b1};
localparam [28:0] FRAME_READ    = {2'b11, 8'hFF, 1'b0, 8'hFF, 1'b1, sent_first_at_lsb(8'h91), 1'b1};
localparam [4:0] WINDOW_CONFIG = 5'd8, WINDOW_POINTER = 5'd30, WINDOW_READ = 5'd31;

`KEEP_FOR_DBG reg [(T_BITS-1):0] t;
reg [7:0] lfsr;
reg [15:0] sensor_r;

wire tick;
wire off = (RATE_EN != 0) && (rate == 3'd0);
wire [1:0] phase = t[1:0];
wire [4:0] slot = t[6:2];
wire [4:0] window = t[11:7];
wire wrap = &t;
wire measuring = &t[(T_BITS-1):12] && !test_mode && !off;
wire in_config = measuring && (window == WINDOW_CONFIG);
wire in_pointer = measuring && (window == WINDOW_POINTER);
wire in_read = measuring && (window == WINDOW_READ);
wire in_frame = in_config || in_pointer || in_read;
wire [4:0] stop_slot = in_pointer ? 5'd19 : 5'd28;
wire [28:0] frame = in_read ? FRAME_READ : (in_config ? FRAME_CONFIG : FRAME_POINTER);
wire frame_bit = (slot <= 5'd28) ? frame[slot] : 1'b1;
wire is_start = (slot == 5'd0);
wire is_stop = (slot == stop_slot);
wire is_bit = !is_start && (slot < stop_slot);
wire scl_low = in_frame && ((is_start && (phase == 2'd3)) || (is_stop && (phase == 2'd0)) ||
                            (is_bit && (phase[1] == phase[0])));   // low in phases 3 and 0, high in 1 and 2
wire sda_low = in_frame && ((is_start && (phase != 2'd0)) || (is_stop && !phase[1]) || (is_bit && !frame_bit));
wire sample = in_read && (phase == 2'd2) && (((slot >= 5'd10) && (slot <= 5'd17)) || ((slot >= 5'd19) && (slot <= 5'd26)));

// what t restarts from: the bits above t[7:0] leave 2^(11+rate) ticks to the wrap, or 2^15
wire [(T_BITS-9):0] t_high;

assign tx_start = wrap && tick && !off;

always @ (posedge clk) begin
  if (rst || off) begin
    t <= {t_high, 8'd0};
  end else if (tick) begin
    if (wrap) begin
      t <= {t_high, lfsr ^ adv_address_sent[7:0]};
    end else begin
      t <= t + 1'b1;
    end
  end
  if (rst) begin
    lfsr <= 8'd0;
    scl_oe <= 1'b0;
    sda_oe <= 1'b0;
  end else if (tick) begin
    if (wrap) lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3] ^ (lfsr[6:0] == 7'd0)};  // 256 states, none stuck
    scl_oe <= scl_low;
    sda_oe <= sda_low;
  end
  if (test_mode && off) begin
    sensor_r <= 16'd0;
  end else if (tick) begin
    if (sample) sensor_r <= {sensor_r[14:0], sda_i};
    else if (test_mode && wrap) sensor_r <= sensor_r + 1'b1;
  end
end

generate
if (TICK_DIV > 1) begin : gen_tick_divider
  localparam integer DIV_BITS = $clog2(TICK_DIV);
  localparam integer DIV_LAST_INT = TICK_DIV - 1;
  localparam [(DIV_BITS-1):0] DIV_LAST = DIV_LAST_INT[(DIV_BITS-1):0];
  reg [(DIV_BITS-1):0] tick_count;
  always @ (posedge clk) begin
    if (rst || (tick_count == DIV_LAST)) begin
      tick_count <= {DIV_BITS{1'b0}};
    end else begin
      tick_count <= tick_count + 1'b1;
    end
  end
  assign tick = (tick_count == DIV_LAST);
end else begin : gen_no_tick_divider
  assign tick = 1'b1;
end

if (RATE_EN != 0) begin : gen_rate
  wire [5:0] t_top = (rate == 3'd2) ? 6'b111110 :   // 250 ms
                     (rate == 3'd3) ? 6'b111100 :   // 500 ms
                     (rate == 3'd4) ? 6'b111000 :   // 1 s
                     (rate == 3'd5) ? 6'b110000 :   // 2 s
                     (rate == 3'd6) ? 6'b100000 :   // 4 s
                     (rate == 3'd7) ? 6'b000000 :   // 8 s
                                      6'b111111;    // 125 ms, and off
  assign t_high = {t_top, 4'd0};
end else begin : gen_fixed_rate
  assign t_high = {(T_BITS-8){1'b0}};
  wire unused_rate = &{1'b0, rate};
end
endgenerate

assign sensor = sensor_r;

wire [3:0] btle_tx_tap_index = 4'd15;     // GAUSS_TABLE = 1: its taps are fixed
wire [15:0] btle_tx_tap_value = 16'd0;

btle_tx #(
  .GAUSS_TABLE(1),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .COMPANY_ID(COMPANY_ID),
  .BCH_T(BCH_T),
  .SENSOR_BYTES(2)
) btle_tx_i (
  .clk(clk),
  .rst(rst),

  .gauss_filter_tap_index(btle_tx_tap_index),
  .gauss_filter_tap_value(btle_tx_tap_value),

  .cos_table_write_address(11'd0),
  .cos_table_write_data(8'd0),
  .sin_table_write_address(11'd0),
  .sin_table_write_data(8'd0),

  .preamble(8'hAA),
  .access_address(32'h8E89BED6),
  .crc_state_init_bit(24'h555555),
  .crc_state_init_bit_load(tx_start),
  .channel_number(CHANNEL),
  .channel_number_load(tx_start),

  .adv_address(ADV_ADDRESS),
  .tx_add(1'b1),
  .sensor({sensor_r[7:0], sensor_r[15:8]}),  // the byte read first, first on the air

  .tx_start(tx_start),

  .adv_address_otp_prog(adv_address_otp_prog),
  .adv_address_otp_ready(adv_address_otp_ready),
  .adv_address_sent(adv_address_sent),

  .i(i),
  .q(q),
  .iq_valid(iq_valid),
  .iq_valid_last(iq_valid_last),

  .phy_bit(phy_bit),
  .phy_bit_valid(phy_bit_valid),
  .phy_bit_valid_last(phy_bit_valid_last),

  .bit_upsample(bit_upsample),
  .bit_upsample_valid(bit_upsample_valid),
  .bit_upsample_valid_last(bit_upsample_valid_last),

  .bit_upsample_gauss_filter(bit_upsample_gauss_filter),
  .bit_upsample_gauss_filter_valid(bit_upsample_gauss_filter_valid),
  .bit_upsample_gauss_filter_valid_last(bit_upsample_gauss_filter_valid_last)
);

endmodule
