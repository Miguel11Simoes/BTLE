// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE parameter passed to gfsk_modulation (default 0 = original). See CHANGES.md.
// Modified 2026-10-04 by Miguel Simões: one bit counter, no addr register and a 4-bit clk_count
// (same outputs on every clock); the packet buffer is one memory of 2^NUM_BIT_PAYLOAD_LENGTH bytes
// with one port, on clkb, plus a register for the last byte, read on request (module pdu_buffer).
// See CHANGES.md.
// Modified 2026-10-16 by Miguel Simões: a transmitter for Legacy Advertising PDUs only (at most
// 39 bytes: 2 header bytes, AdvA, at most 31 bytes of AdvData). The header is two registers, AdvA
// (the 6 bytes after the header) is fixed per chip (ADV_ADDRESS: a ROM here, an OTP in the ASIC)
// and only AdvData is in memory, 32 x 8 (module adv_pdu_buffer); the counters are cut to 39 bytes.
// See CHANGES.md.
// Modified 2026-11-04 by Miguel Simões: the senseworks tag. One packet format, fixed in the
// hardware (module tag_pdu_buffer): ADV_NONCONN_IND, AdvA, one Manufacturer Specific Data
// structure with COMPANY_ID, the sensor's two bytes (the only bytes written, PDU addresses 12 and
// 13) and the parity of a shortened BCH code (BCH_T = 8, 12 or 18) of AdvA and the sensor, computed
// by an LFSR while they are sent. See CHANGES.md and docs/Senseworks/TX_TAG_COMPARISON.md.
// Modified 2026-11-06 by Miguel Simões: ble-tx-poc: SENSOR_BYTES, one or two bytes of sensor (the
// lengths, the BCH message and the last bit follow); AdvA, TxAdd and the sensor on direct ports of
// the clk domain, instead of the (address, data) pair on clkb: no clkb, no read request, no read
// register (the same outputs on every clock). See CHANGES.md and docs/Senseworks/TX_POC.md.

// iverilog -o btle_tx btle_tx.v crc24.v crc24_core.v scramble.v scramble_core.v gfsk_modulation.v bit_repeat_upsample.v gauss_filter.v vco.v

`define KEEP_FOR_DBG (*mark_debug="true",DONT_TOUCH="TRUE"*)
// `define KEEP_FOR_DBG

`timescale 1ns / 1ps
module btle_tx #
(
  parameter integer NUM_BIT_PAYLOAD_LENGTH = 8, // 8 bit in the core spec 6.2
  parameter integer CRC_STATE_BIT_WIDTH = 24,
  parameter integer CHANNEL_NUMBER_BIT_WIDTH = 6,
  parameter integer SAMPLE_PER_SYMBOL = 8,
  parameter integer GAUSS_FILTER_BIT_WIDTH = 16,
  parameter integer NUM_TAP_GAUSS_FILTER = 17,
  parameter integer VCO_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8,
  parameter integer GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT = 1,
  parameter integer GAUSS_TABLE = 0, // passed to gauss_filter
  // AdvA from an OTP (1): six GF180MCU eFuse blocks (efuse_async_mem_1x8), programmed once per chip
  // through adv_address_otp_prog and read into their latches after each reset; the port adv_address
  // is then ignored. 0 (default): the port adv_address (tied to a constant it is a ROM).
  parameter integer ADV_ADDRESS_OTP = 0,
  // The tag's packet: the Company ID of the Manufacturer Specific Data (0xFFFF, the value for tests;
  // a product needs its own, assigned by the Bluetooth SIG), the number of errors the BCH code
  // corrects in AdvA, the sensor and the parity: 8, 12 or 18 (8, 12 or 16 bytes of parity), and the
  // bytes of sensor: 1 or 2.
  parameter [15:0] COMPANY_ID = 16'hFFFF,
  parameter integer BCH_T = 8,
  parameter integer SENSOR_BYTES = 1
) (
  input wire clk, // for baseband processing, 16MHz
  input wire rst,

  `KEEP_FOR_DBG input wire [3:0] gauss_filter_tap_index, // only need to set 0~8, 9~16 will be mirror of 0~7
  `KEEP_FOR_DBG input wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] gauss_filter_tap_value,

  `KEEP_FOR_DBG input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] cos_table_write_address,
  `KEEP_FOR_DBG input  wire signed [(IQ_BIT_WIDTH-1) : 0] cos_table_write_data,
  `KEEP_FOR_DBG input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] sin_table_write_address,
  `KEEP_FOR_DBG input  wire signed [(IQ_BIT_WIDTH-1) : 0] sin_table_write_data,

  `KEEP_FOR_DBG input  wire [7:0]  preamble,

  `KEEP_FOR_DBG input  wire [31:0] access_address,
  `KEEP_FOR_DBG input  wire [(CRC_STATE_BIT_WIDTH-1) : 0] crc_state_init_bit, // load into lfsr (linear feedback shift register) upon crc_state_init_bit_load==1
  `KEEP_FOR_DBG input  wire crc_state_init_bit_load,
  `KEEP_FOR_DBG input  wire [(CHANNEL_NUMBER_BIT_WIDTH-1) : 0] channel_number, // load into lfsr (linear feedback shift register) upon channel_number_load==1
  `KEEP_FOR_DBG input  wire channel_number_load,

  // What the packet carries, on the clk domain, stable from tx_start to the end of the packet:
  // AdvA, the device address sent in PDU bytes 2..7, least significant byte first (byte 2 =
  // adv_address[7:0]), as the Core spec sends it; TxAdd of the header (1: AdvA is a random address;
  // 0: a public one); the sensor, d0 in sensor[7:0] and, with SENSOR_BYTES = 2, d1 in sensor[15:8].
  `KEEP_FOR_DBG input  wire [47:0] adv_address,
  `KEEP_FOR_DBG input  wire tx_add,
  `KEEP_FOR_DBG input  wire [(8*SENSOR_BYTES-1) : 0] sensor,

  `KEEP_FOR_DBG input  wire tx_start,

  // ADV_ADDRESS_OTP = 1 only: the production port that programs AdvA (bit k of adv_address's order)
  // once per chip, a 1 blowing its fuse when held for at least 50 us out of reset; ready once
  // the fuses are read after a reset. Otherwise: unused, and ready is 1.
  input  wire [47:0] adv_address_otp_prog,
  output wire adv_address_otp_ready,
  output wire [47:0] adv_address_sent, // the AdvA of the packet: the port's or the OTP's

  `KEEP_FOR_DBG output wire signed [(IQ_BIT_WIDTH-1) : 0] i,
  `KEEP_FOR_DBG output wire signed [(IQ_BIT_WIDTH-1) : 0] q,
  `KEEP_FOR_DBG output wire iq_valid,
  `KEEP_FOR_DBG output wire iq_valid_last,

  // for debug purpose
  `KEEP_FOR_DBG output wire phy_bit,
  `KEEP_FOR_DBG output wire phy_bit_valid,
  `KEEP_FOR_DBG output wire phy_bit_valid_last,

  `KEEP_FOR_DBG output wire bit_upsample,
  `KEEP_FOR_DBG output wire bit_upsample_valid,
  `KEEP_FOR_DBG output wire bit_upsample_valid_last,

  `KEEP_FOR_DBG output wire signed [(GAUSS_FILTER_BIT_WIDTH-1) : 0] bit_upsample_gauss_filter,
  `KEEP_FOR_DBG output wire bit_upsample_gauss_filter_valid,
  `KEEP_FOR_DBG output wire bit_upsample_gauss_filter_valid_last
);

// Counters (upstream's in brackets). The outputs are upstream's on every clock.
//   - One bit counter: bit_count counts the 40 preamble/access-address bits
//     [bit_count_preamble_access], is cleared with the 40th, then counts the PDU
//     bits [bit_count].
//   - No addr register: the packet buffer is read at bit_count / 8, which is
//     [addr] in the only clock whose read upstream uses ([clk_count] 127, the
//     byte taken by octet one clock later).
//   - A 4-bit clk_count, the clock within a bit: in TX_PDU [clk_count] is 0
//     exactly when clk_count is 0 and bit_count[2:0] is 0 (8 bits per 128
//     clocks, one every 16), and 116 exactly when clk_count is 4 and
//     bit_count[2:0] is 0.
//   - No reset and no clear in IDLE for octet (loaded at [clk_count] 0 before
//     its first use) and for the preamble/access-address shift register (loaded
//     at tx_start before its first use).
// The senseworks tag (2026-11-04): one PDU, its length fixed (no payload_length
// register): 2 header bytes and a payload of PAYLOAD_LENGTH = 10 + SENSOR_BYTES +
// PARITY_BYTES (19 to 28), at most 30 bytes, so the PDU bits are counted in 8 bits
// (at most 240) and the byte address is 5 bits (0..29). The outputs are, on every
// clock, ble-tx-min's (upstream's) for the same PDU written whole in its buffer.
//
// The BCH parity. The code's message is the bits that a receiver does not know,
// AdvA (PDU bits 16..63) and the sensor (bits 96..103 or 96..111), 56 or 64 bits,
// in the order they are sent; the parity follows from bit 104 or 112 on. bch_lfsr
// divides the message by the generator g(x) as the bits are sent (the first bit
// the highest power):
// each message bit enters with the bit that leaves, and in the parity bits the
// register shifts out its remainder, the highest coefficient first, while 0s
// shift in. The bit sent there is bch_lfsr's top bit instead of octet's, so the
// CRC and the whitening cover the parity as any PDU bit; when 8 * PARITY_BYTES
// is more than BCH_DEG (t = 12, t = 18: 4 bits), the last bits sent are those
// 0s. g(x) is the least common multiple of the minimal polynomials of alpha^1
// .. alpha^2t over GF(2^8), primitive polynomial x^8 + x^4 + x^3 + x^2 + 1
// (BCH_G below holds it without its x^BCH_DEG term; scripts/senseworks/tag_bch.py
// is the reference). bch_lfsr is cleared outside TX_PDU, so a packet aborted
// by a reset leaves nothing for the next.

localparam [1:0] IDLE               = 0,
                 TX_PREAMBLE_ACCESS = 1,
                 TX_PDU             = 2,
                 WAIT_LAST_SAMPLE   = 3;
localparam integer BCH_DEG = (BCH_T == 8) ? 64 : (BCH_T == 12) ? 92 : 124;
localparam [123:0] BCH_G_ALL = (BCH_T == 8)  ? {60'd0, 64'h6ce707e26b6f9977} :
                               (BCH_T == 12) ? {32'd0, 92'he810da40f70569be7529981} :
                                               124'h1bcb6cce6906958aa17f2231050eb39;
localparam [BCH_DEG-1:0] BCH_G = BCH_G_ALL[BCH_DEG-1:0];
localparam integer PARITY_BYTES = (BCH_DEG + 7) / 8;                 // 8, 12, 16
localparam integer PAYLOAD_LENGTH = 10 + SENSOR_BYTES + PARITY_BYTES;   // AdvA, the AD structure: 19..28
localparam integer PDU_BIT_COUNT_WIDTH = 8;                          // (2 + 28) * 8 = 240 PDU bits
localparam integer LAST_PDU_BIT_INDEX = (PAYLOAD_LENGTH + 2) * 8 - 1;   // 167..239
localparam [PDU_BIT_COUNT_WIDTH-1:0] LAST_PDU_BIT = LAST_PDU_BIT_INDEX[PDU_BIT_COUNT_WIDTH-1:0];
localparam integer PARITY_FIRST_BIT_INDEX = 96 + 8 * SENSOR_BYTES;   // 104, 112
localparam [PDU_BIT_COUNT_WIDTH-1:0] ADVA_FIRST_BIT = 16, ADVA_END_BIT = 64,
                                     SENSOR_FIRST_BIT = 96,
                                     PARITY_FIRST_BIT = PARITY_FIRST_BIT_INDEX[PDU_BIT_COUNT_WIDTH-1:0];

generate
if (BCH_T != 8 && BCH_T != 12 && BCH_T != 18) begin : gen_bch_t_check
  initial $fatal(1, "btle_tx: BCH_T must be 8, 12 or 18");
end
if (SENSOR_BYTES != 1 && SENSOR_BYTES != 2) begin : gen_sensor_bytes_check
  initial $fatal(1, "btle_tx: SENSOR_BYTES must be 1 or 2");
end
endgenerate

`KEEP_FOR_DBG reg  [1:0] phy_tx_state;
`KEEP_FOR_DBG wire [4:0] addr;
`KEEP_FOR_DBG wire [7:0] data;
`KEEP_FOR_DBG reg  [7:0] octet;
`KEEP_FOR_DBG reg  [(PDU_BIT_COUNT_WIDTH-1):0] bit_count;

`KEEP_FOR_DBG reg info_bit;
`KEEP_FOR_DBG reg info_bit_valid;
`KEEP_FOR_DBG reg info_bit_valid_last;

`KEEP_FOR_DBG reg  [39:0] preamble_access_address;

`KEEP_FOR_DBG reg  [BCH_DEG-1:0] bch_lfsr;

`KEEP_FOR_DBG wire info_bit_after_crc24;
`KEEP_FOR_DBG wire info_bit_after_crc24_valid;
`KEEP_FOR_DBG wire info_bit_after_crc24_valid_last;

`KEEP_FOR_DBG wire signed [(IQ_BIT_WIDTH-1) : 0] i_internal;
`KEEP_FOR_DBG wire signed [(IQ_BIT_WIDTH-1) : 0] q_internal;

`KEEP_FOR_DBG reg [3:0] clk_count; // clocks within a bit (16 per bit); the octet phase is bit_count[2:0]

assign addr = bit_count[(PDU_BIT_COUNT_WIDTH-1):3];

// the PDU bit sent in this bit period (bit_count) is a message bit of the BCH code, or a parity bit
wire bch_message_bit = ((bit_count >= ADVA_FIRST_BIT) && (bit_count < ADVA_END_BIT)) ||
                       ((bit_count >= SENSOR_FIRST_BIT) && (bit_count < PARITY_FIRST_BIT));
wire bch_parity_bit = (bit_count >= PARITY_FIRST_BIT);

assign i =(phy_tx_state == IDLE? 0 : i_internal);
assign q = (phy_tx_state == IDLE? 0 : q_internal);

// registers whose reset value is never read
always @ (posedge clk) begin
  if (phy_tx_state == IDLE) begin
    if (tx_start) begin
      preamble_access_address <= {access_address, preamble};
    end
  end else if (phy_tx_state == TX_PREAMBLE_ACCESS) begin
    if (clk_count == 1) begin
      preamble_access_address[38:0] <= preamble_access_address[39:1];
    end
  end else if (phy_tx_state == TX_PDU) begin
    if (clk_count == 0 && bit_count[2:0] == 0) begin // speed 1/8M
      octet <= data;
    end else if (clk_count == 1) begin
      octet[6:0] <= octet[7:1];
    end
  end
end

// the BCH encoder: cleared outside TX_PDU, one step per PDU bit sent (see above)
always @ (posedge clk) begin
  if (phy_tx_state != TX_PDU) begin
    bch_lfsr <= 0;
  end else if (clk_count == 1) begin
    if (bch_message_bit) begin
      bch_lfsr <= {bch_lfsr[BCH_DEG-2:0], 1'b0} ^ ({BCH_DEG{bch_lfsr[BCH_DEG-1] ^ octet[0]}} & BCH_G);
    end else if (bch_parity_bit) begin
      bch_lfsr <= {bch_lfsr[BCH_DEG-2:0], 1'b0};
    end
  end
end

// state machine of the packet
always @ (posedge clk) begin
  if (rst) begin
    bit_count <= 0;

    info_bit <= 0;
    info_bit_valid <= 0;
    info_bit_valid_last <= 0;

    clk_count <= 0;

    phy_tx_state <= IDLE;
  end else begin
    case(phy_tx_state)
      IDLE: begin
        bit_count <= 0;

        info_bit <= 0;
        info_bit_valid <= 0;
        info_bit_valid_last <= 0;

        clk_count <= 0;

        phy_tx_state <= (tx_start? TX_PREAMBLE_ACCESS : phy_tx_state);
      end

      TX_PREAMBLE_ACCESS: begin
        clk_count <= clk_count + 1;
        if (clk_count == 1) begin // speed 1M
          info_bit <= preamble_access_address[0];
          info_bit_valid <= 1;

          if (bit_count[5:0] == (40 - 1)) begin
            bit_count <= 0;
            phy_tx_state <= TX_PDU;
          end else begin
            bit_count <= bit_count + 1;
          end
        end else begin
          info_bit_valid <= 0;
        end
      end

      TX_PDU: begin
        clk_count <= clk_count + 1;
        if (clk_count == 1) begin // speed 1M
          info_bit <= bch_parity_bit ? bch_lfsr[BCH_DEG-1] : octet[0];
          info_bit_valid <= 1;

          bit_count <= bit_count + 1;

          // the last PDU bit: bit_count == (PAYLOAD_LENGTH + 2) * 8 - 1
          if (bit_count == LAST_PDU_BIT) begin
            info_bit_valid_last <= 1;
            phy_tx_state <= WAIT_LAST_SAMPLE;
          end
        end else begin
          info_bit_valid <= 0;
        end
      end

      WAIT_LAST_SAMPLE: begin
        info_bit_valid <= 0;
        info_bit_valid_last <= 0;
        phy_tx_state <= (iq_valid_last? IDLE : phy_tx_state);
      end
    endcase
  end
end

tag_pdu_buffer # (
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .COMPANY_ID(COMPANY_ID),
  .PARITY_BYTES(PARITY_BYTES),
  .SENSOR_BYTES(SENSOR_BYTES)
) btle_tx_pdu_buffer_i (
  .rst(rst),
  .otp_prog(adv_address_otp_prog),
  .otp_ready(adv_address_otp_ready),
  .adv_address_in(adv_address),
  .tx_add(tx_add),
  .sensor(sensor),

  .adv_address(adv_address_sent),
  .read_address(addr),
  .read_data(data)
);

crc24 # (
  .NUM_BIT_PAYLOAD_LENGTH(NUM_BIT_PAYLOAD_LENGTH),
  .CRC_STATE_BIT_WIDTH(CRC_STATE_BIT_WIDTH)
) crc24_i (
  .clk(clk),
  .rst(rst),

  .crc_state_init_bit(crc_state_init_bit),
  .crc_state_init_bit_load(crc_state_init_bit_load),

  .info_bit(info_bit),
  .info_bit_valid(info_bit_valid),
  .info_bit_valid_last(info_bit_valid_last),

  .info_bit_after_crc24(info_bit_after_crc24),
  .info_bit_after_crc24_valid(info_bit_after_crc24_valid),
  .info_bit_after_crc24_valid_last(info_bit_after_crc24_valid_last)
);

scramble # (
  .NUM_BIT_PAYLOAD_LENGTH(NUM_BIT_PAYLOAD_LENGTH),
  .CHANNEL_NUMBER_BIT_WIDTH(CHANNEL_NUMBER_BIT_WIDTH)
) scramble_i (
  .clk(clk),
  .rst(rst),

  .channel_number(channel_number),
  .channel_number_load(channel_number_load),

  .data_in(info_bit_after_crc24),
  .data_in_valid(info_bit_after_crc24_valid),
  .data_in_valid_last(info_bit_after_crc24_valid_last),

  .data_out(phy_bit),
  .data_out_valid(phy_bit_valid),
  .data_out_valid_last(phy_bit_valid_last)
);

gfsk_modulation # (
  .SAMPLE_PER_SYMBOL(SAMPLE_PER_SYMBOL),
  .GAUSS_FILTER_BIT_WIDTH(GAUSS_FILTER_BIT_WIDTH),
  .GAUSS_TABLE(GAUSS_TABLE),
  .NUM_TAP_GAUSS_FILTER(NUM_TAP_GAUSS_FILTER),
  .VCO_BIT_WIDTH(VCO_BIT_WIDTH),
  .SIN_COS_ADDR_BIT_WIDTH(SIN_COS_ADDR_BIT_WIDTH),
  .IQ_BIT_WIDTH(IQ_BIT_WIDTH),
  .GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT(GAUSS_FIR_OUT_AMP_SCALE_DOWN_NUM_BIT_SHIFT)
) gfsk_modulation_i (
  .clk(clk),
  .rst(rst),

  .gauss_filter_tap_index(gauss_filter_tap_index), // only need to set 0~8, 9~16 will be mirror of 0~7
  .gauss_filter_tap_value(gauss_filter_tap_value),


  .phy_bit(phy_bit),
  .bit_valid(phy_bit_valid),
  .bit_valid_last(phy_bit_valid_last),

  .cos_out(i_internal),
  .sin_out(q_internal),
  .sin_cos_out_valid(iq_valid),
  .sin_cos_out_valid_last(iq_valid_last),

  .bit_upsample(bit_upsample),
  .bit_upsample_valid(bit_upsample_valid),
  .bit_upsample_valid_last(bit_upsample_valid_last),

  .bit_upsample_gauss_filter(bit_upsample_gauss_filter),
  .bit_upsample_gauss_filter_valid(bit_upsample_gauss_filter_valid),
  .bit_upsample_gauss_filter_valid_last(bit_upsample_gauss_filter_valid_last)
);

// The VCO's table writes: the tables are a ROM (vco.v); the ports are kept for the interface.
wire unused_vco_table_writes = &{1'b0, cos_table_write_address, cos_table_write_data,
  sin_table_write_address, sin_table_write_data};

endmodule

// The packet buffer of the senseworks tag (2026-11-04). The TX reads PDU bytes
// here up to the sensor's last (the next ones are the BCH parity, which btle_tx
// sends from its LFSR):
//   - bytes 0 and 1, the header: ADV_NONCONN_IND with the port tx_add and the
//     payload length 10 + SENSOR_BYTES + PARITY_BYTES;
//   - bytes 2..7, AdvA: the port adv_address_in, or an OTP in the ASIC
//     (ADV_ADDRESS_OTP = 1: programmed once);
//   - bytes 8..11, the AD structure's length (3 + SENSOR_BYTES + PARITY_BYTES),
//     its type (0xFF, Manufacturer Specific Data) and COMPANY_ID, least
//     significant byte first: constants;
//   - byte 12, and 13 with SENSOR_BYTES = 2, the sensor: the port sensor.
// The read is combinational (ble-tx-poc, 2026-11-06): btle_tx takes the byte at
// [clk_count] 0, read_address stable since [clk_count] 114, where the (address,
// data) pair of the tag's earlier branches had a request toggle, its
// synchronizers and a register on clkb to give the same byte there.
// Contract: the ports stable from tx_start to the end of the packet. Every other
// byte reads 0 (btle_tx does not use them).
// Bundled helper: preserve the existing single-file compilation interface.
/* verilator lint_off DECLFILENAME */
module tag_pdu_buffer #
/* verilator lint_on DECLFILENAME */
(
  parameter integer ADV_ADDRESS_OTP = 0,
  parameter [15:0] COMPANY_ID = 16'hFFFF,
  parameter integer PARITY_BYTES = 8,
  parameter integer SENSOR_BYTES = 1
) (
  input  wire rst,
  input  wire [47:0] otp_prog,
  output wire otp_ready,
  input  wire [47:0] adv_address_in,
  input  wire tx_add,
  input  wire [(8*SENSOR_BYTES-1):0] sensor,

  output wire [47:0] adv_address,
  input  wire [4:0] read_address,
  output reg  [7:0] read_data
);

// header byte 0: PDU type 0010 (ADV_NONCONN_IND), RFU 0, ChSel 0, TxAdd, RxAdd 0
wire [7:0] header0 = {1'b0, tx_add, 2'b00, 4'b0010};
localparam integer PAYLOAD_LENGTH = 10 + SENSOR_BYTES + PARITY_BYTES;  // AdvA and the AD structure
localparam integer AD_STRUCTURE_LENGTH = 3 + SENSOR_BYTES + PARITY_BYTES; // type, Company ID, sensor, parity
localparam [7:0] HEADER1 = PAYLOAD_LENGTH[7:0];
localparam [7:0] AD_LENGTH = AD_STRUCTURE_LENGTH[7:0];
localparam [7:0] AD_TYPE = 8'hFF;                   // Manufacturer Specific Data

wire [7:0] sensor_d1;                               // PDU byte 13: the parity's first with one byte of sensor
always @(*) begin
  case (read_address)
    5'd0:    read_data = header0;
    5'd1:    read_data = HEADER1;
    5'd2:    read_data = adv_address[7:0];
    5'd3:    read_data = adv_address[15:8];
    5'd4:    read_data = adv_address[23:16];
    5'd5:    read_data = adv_address[31:24];
    5'd6:    read_data = adv_address[39:32];
    5'd7:    read_data = adv_address[47:40];
    5'd8:    read_data = AD_LENGTH;
    5'd9:    read_data = AD_TYPE;
    5'd10:   read_data = COMPANY_ID[7:0];
    5'd11:   read_data = COMPANY_ID[15:8];
    5'd12:   read_data = sensor[7:0];
    5'd13:   read_data = sensor_d1;
    default: read_data = 8'h00;                     // the parity: sent from btle_tx's LFSR
  endcase
end

generate
if (SENSOR_BYTES == 2) begin : gen_sensor_d1
  assign sensor_d1 = sensor[15:8];
end else begin : gen_no_sensor_d1
  assign sensor_d1 = 8'h00;
end

if (ADV_ADDRESS_OTP != 0) begin : gen_adv_address_otp
  // AdvA in six 8-bit eFuse blocks of the GF180MCU eFuse compiler (efuse_async_mem_1x8, a macro):
  // each senses its fuses into latches after reset_n rises (within 10 ns) and holds them;
  // prog[i] = 1 for 50 us blows fuse i (a blown fuse reads 1). The fuses are static after a
  // reset, so they are read like a ROM.
  wire [5:0] byte_ready;
  genvar b;
  for (b=0; b<6; b=b+1) begin : otp_byte
    efuse_async_mem_1x8 efuse_i (
      .reset_n(~rst),
      .prog(otp_prog[8*b +: 8]),
      .out(adv_address[8*b +: 8]),
      .ready(byte_ready[b])
    );
  end
  assign otp_ready = &byte_ready;
  wire unused_adv_address_in = &{1'b0, adv_address_in};
end else begin : gen_adv_address_port
  assign adv_address = adv_address_in;
  assign otp_ready = 1'b1;
  wire unused_otp_inputs = &{1'b0, otp_prog, rst};
end
endgenerate

endmodule
