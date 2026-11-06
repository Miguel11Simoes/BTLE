// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// A sketch for one comparison, not the design: the architecture ble-tx-poc-gen did not take, measured against tag_fsm.v
// with the same four profiles and the same pins (docs/Senseworks/TX_POC_GEN.md section 6). A sequencer FSM executes a
// program of operations from a ROM per sensor (write a frame, wait, read a frame), through one bit engine for I2C and SPI,
// and the timers of tag_fsm.v's period. It simulates nothing here: it is only synthesized (scripts/area/compare_gen_architecture.sh).
//   an operation: [7] 1: a frame: [6:4] the bytes to write, the bytes follow, [3:2] the bytes to read, [1] no STOP, [0] SPI words
//                 [7] 0: [6:0] wait so many units of 32 ticks, 0: the end

`timescale 1ns / 1ps
module tag_chip_sequencer (
  input  wire clk,
  input  wire rst,
  input  wire [2:0] rate,
  input  wire [1:0] sel,
  input  wire sda_i,
  output reg  scl_oe,
  output reg  sda_oe,
  output wire cs_n,
  input  wire [47:0] adv_address_otp_prog,
  output wire adv_address_otp_ready,
  output wire signed [7:0] i,
  output wire signed [7:0] q,
  output wire iq_valid,
  output wire iq_valid_last
);

localparam [2:0] S_IDLE = 0, S_FETCH = 1, S_START = 2, S_WRITE = 3, S_READ = 4, S_STOP = 5, S_WAIT = 6;
reg [2:0] st;
reg [5:0] pc;
reg [2:0] w_left;
reg [1:0] r_left;
reg no_stop;
reg [3:0] bit_count;
reg [6:0] wait_count;
reg [7:0] shift;
reg [17:0] t;
reg [7:0] lfsr;
reg [15:0] sensor_r;
reg cs_low;
wire [47:0] adv_address_sent;

// The programs. Each: the frames and waits of tag_profile.py's sequences for the four sensors.
function [7:0] rom(input [1:0] s, input [5:0] a);
  case ({s, a})
    // TMP100
    8'h00: rom = 8'hB0; 8'h01: rom = 8'h90; 8'h02: rom = 8'h01; 8'h03: rom = 8'h81; 8'h04: rom = 8'h4D;
    8'h05: rom = 8'h90; 8'h06: rom = 8'h90; 8'h07: rom = 8'h00; 8'h08: rom = 8'h98; 8'h09: rom = 8'h91; 8'h0A: rom = 8'h00;
    // TMP114
    8'h40: rom = 8'hC0; 8'h41: rom = 8'h90; 8'h42: rom = 8'h03; 8'h43: rom = 8'h00; 8'h44: rom = 8'h1C; 8'h45: rom = 8'h08;
    8'h46: rom = 8'hA2; 8'h47: rom = 8'h90; 8'h48: rom = 8'h00; 8'h49: rom = 8'h98; 8'h4A: rom = 8'h91; 8'h4B: rom = 8'h00;
    // MAX31875
    8'h80: rom = 8'hC0; 8'h81: rom = 8'h90; 8'h82: rom = 8'h01; 8'h83: rom = 8'h01; 8'h84: rom = 8'h21; 8'h85: rom = 8'h1A;
    8'h86: rom = 8'hA2; 8'h87: rom = 8'h90; 8'h88: rom = 8'h00; 8'h89: rom = 8'h98; 8'h8A: rom = 8'h91; 8'h8B: rom = 8'h00;
    // TMP126: the words as bytes
    8'hC0: rom = 8'hC1; 8'hC1: rom = 8'h00; 8'hC2: rom = 8'h03; 8'hC3: rom = 8'h00; 8'hC4: rom = 8'h1E; 8'hC5: rom = 8'h08;
    8'hC6: rom = 8'hA9; 8'hC7: rom = 8'h01; 8'hC8: rom = 8'h00; 8'hC9: rom = 8'h00;
    default: rom = 8'h00;
  endcase
endfunction

wire [7:0] step = rom(sel, pc);
wire spi = (sel == 2'd3);
wire off = (rate == 3'd0);
wire [5:0] t_top = (rate == 3'd2) ? 6'b111110 : (rate == 3'd3) ? 6'b111100 : (rate == 3'd4) ? 6'b111000 :
                   (rate == 3'd5) ? 6'b110000 : (rate == 3'd6) ? 6'b100000 : (rate == 3'd7) ? 6'b000000 : 6'b111111;
wire [9:0] t_high = {t_top, 4'd0};
wire wrap = &t;
wire begin_event = &t[17:12] && (t[11:0] == 12'd1024) && !off;
wire tx_start = wrap && !off;
wire [1:0] phase = t[1:0];
wire unit = (t[4:0] == 5'd31);
wire [3:0] frame_bits = spi ? 4'd7 : 4'd8;

always @(posedge clk) begin
  if (rst || off) t <= {t_high, 8'd0};
  else if (wrap) t <= {t_high, lfsr ^ adv_address_sent[7:0]};
  else t <= t + 1'b1;
  if (rst) begin
    lfsr <= 8'd0; st <= S_IDLE; pc <= 6'd0; scl_oe <= 1'b0; sda_oe <= 1'b0; cs_low <= 1'b0;
  end else begin
    if (wrap) lfsr <= {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3] ^ (lfsr[6:0] == 7'd0)};
    case (st)
      S_IDLE: if (begin_event) begin pc <= 6'd0; st <= S_FETCH; end
      S_FETCH: if (phase == 2'd0) begin
        pc <= pc + 6'd1;
        if (step[7]) begin
          w_left <= step[6:4]; r_left <= step[3:2]; no_stop <= step[1]; st <= S_START; cs_low <= 1'b1;
        end else if (step[6:0] != 7'd0) begin
          wait_count <= step[6:0]; st <= S_WAIT;
        end else begin
          st <= S_IDLE;
        end
      end
      S_WAIT: if (unit) begin
        if (wait_count == 7'd0) st <= S_FETCH; else wait_count <= wait_count - 7'd1;
      end
      S_START: begin
        if (phase == 2'd1) sda_oe <= 1'b1;
        if (phase == 2'd3) begin
          scl_oe <= 1'b1;
          st <= (w_left != 3'd0) ? S_WRITE : S_READ;
          bit_count <= 4'd0;
          shift <= step;
        end
      end
      S_WRITE: begin
        if (phase == 2'd0) begin sda_oe <= (bit_count <= frame_bits - 4'd0) ? !shift[7] : 1'b0; scl_oe <= 1'b1; end
        if (phase == 2'd1) scl_oe <= 1'b0;
        if (phase == 2'd2 && spi) sda_oe <= 1'b0;
        if (phase == 2'd3) begin
          scl_oe <= 1'b1;
          shift <= {shift[6:0], 1'b1};
          bit_count <= bit_count + 4'd1;
          if (bit_count == (spi ? 4'd7 : 4'd8)) begin
            bit_count <= 4'd0;
            pc <= pc + 6'd1;
            shift <= rom(sel, pc + 6'd1);
            w_left <= w_left - 3'd1;
            if (w_left == 3'd1) st <= (r_left != 2'd0) ? S_READ : S_STOP;
          end
        end
      end
      S_READ: begin
        if (phase == 2'd0) begin
          sda_oe <= (bit_count == 4'd8) && !spi && (r_left != 2'd1);
          scl_oe <= 1'b1;
        end
        if (phase == 2'd1) scl_oe <= 1'b0;
        if (phase == 2'd2 && bit_count != 4'd8) sensor_r <= {sensor_r[14:0], sda_i};
        if (phase == 2'd3) begin
          scl_oe <= 1'b1;
          bit_count <= bit_count + 4'd1;
          if (bit_count == frame_bits) begin
            bit_count <= 4'd0;
            r_left <= r_left - 2'd1;
            if (r_left == 2'd1) st <= S_STOP;
          end
        end
      end
      S_STOP: begin
        if (phase == 2'd0) begin sda_oe <= 1'b1; cs_low <= 1'b0; end
        if (phase == 2'd1) scl_oe <= 1'b0;
        if (phase == 2'd2) sda_oe <= 1'b0;
        if (phase == 2'd3) st <= S_FETCH;
      end
      default: st <= S_IDLE;
    endcase
    if (st == S_WRITE && w_left == 3'd1 && no_stop && phase == 2'd3 && bit_count == 4'd8) begin
      sda_oe <= 1'b0; scl_oe <= 1'b0; st <= S_FETCH;
    end
  end
end

assign cs_n = !(spi && cs_low);

btle_tx #(.GAUSS_TABLE(1), .ADV_ADDRESS_OTP(0), .BCH_T(8), .SENSOR_BYTES(2)) btle_tx_i (
  .clk(clk), .rst(rst),
  .gauss_filter_tap_index(4'd15), .gauss_filter_tap_value(16'd0),
  .cos_table_write_address(11'd0), .cos_table_write_data(8'd0),
  .sin_table_write_address(11'd0), .sin_table_write_data(8'd0),
  .preamble(8'hAA), .access_address(32'h8E89BED6),
  .crc_state_init_bit(24'h555555), .crc_state_init_bit_load(tx_start),
  .channel_number(6'd37), .channel_number_load(tx_start),
  .adv_address(48'hC10203040506), .tx_add(1'b1), .sensor({sensor_r[7:0], sensor_r[15:8]}),
  .tx_start(tx_start),
  .adv_address_otp_prog(adv_address_otp_prog), .adv_address_otp_ready(adv_address_otp_ready),
  .adv_address_sent(adv_address_sent),
  .i(i), .q(q), .iq_valid(iq_valid), .iq_valid_last(iq_valid_last)
);

endmodule
