// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-09-19 by Miguel Simões: GAUSS_TABLE parameter passed to gfsk_modulation (default 0 = original). See CHANGES.md.
// Modified 2026-10-04 by Miguel Simões: one bit counter, no addr register and a 4-bit clk_count
// (same outputs on every clock); the packet buffer is one memory of 2^NUM_BIT_PAYLOAD_LENGTH bytes
// with one port, on clkb, plus a register for the last byte, read on request (module pdu_buffer).
// See CHANGES.md.

// iverilog -o btle_tx btle_tx.v sdpram_one_clk.v sdpram_two_clk.v crc24.v crc24_core.v scramble.v scramble_core.v gfsk_modulation.v bit_repeat_upsample.v gauss_filter.v vco.v 

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
  parameter integer GAUSS_TABLE = 0 // passed to gauss_filter
) (
  input wire clk, // for baseband processing, 16MHz
  input wire rst,

  input wire clkb, // for writing pkt to ram with different/higher clock speed

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

  `KEEP_FOR_DBG input  wire [7:0] pdu_octet_mem_data,
  `KEEP_FOR_DBG input  wire [NUM_BIT_PAYLOAD_LENGTH:0] pdu_octet_mem_addr,

  `KEEP_FOR_DBG input  wire tx_start,

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
//     byte taken by octet one clock later); "[addr] == 2 && clk_count == 1" is
//     "bit_count == 8 && clk_count == 1".
//   - A 4-bit clk_count, the clock within a bit: in TX_PDU [clk_count] is 0
//     exactly when clk_count is 0 and bit_count[2:0] is 0 (8 bits per 128
//     clocks, one every 16), and 116 exactly when clk_count is 4 and
//     bit_count[2:0] is 0.
//   - An 8-bit payload_length without upstream's value in IDLE (all ones):
//     before it is loaded (bit_count <= 8) the end test
//     bit_count == (L+2)*8-1 >= 15 fails for every L.
//   - No reset and no clear in IDLE for octet (loaded at [clk_count] 0 before
//     its first use) and for the preamble/access-address shift register (loaded
//     at tx_start before its first use).

localparam [1:0] IDLE               = 0,
                 TX_PREAMBLE_ACCESS = 1,
                 TX_PDU             = 2,
                 WAIT_LAST_SAMPLE   = 3;

`KEEP_FOR_DBG reg  [1:0] phy_tx_state;
`KEEP_FOR_DBG wire [NUM_BIT_PAYLOAD_LENGTH:0] addr;
`KEEP_FOR_DBG wire [7:0] data;
`KEEP_FOR_DBG reg  [7:0] octet;
`KEEP_FOR_DBG reg  [7:0] payload_length;
`KEEP_FOR_DBG reg  [(NUM_BIT_PAYLOAD_LENGTH+3):0] bit_count;

`KEEP_FOR_DBG reg info_bit;
`KEEP_FOR_DBG reg info_bit_valid;
`KEEP_FOR_DBG reg info_bit_valid_last;

`KEEP_FOR_DBG reg  [39:0] preamble_access_address;

`KEEP_FOR_DBG wire info_bit_after_crc24;
`KEEP_FOR_DBG wire info_bit_after_crc24_valid;
`KEEP_FOR_DBG wire info_bit_after_crc24_valid_last;

`KEEP_FOR_DBG wire signed [(IQ_BIT_WIDTH-1) : 0] i_internal;
`KEEP_FOR_DBG wire signed [(IQ_BIT_WIDTH-1) : 0] q_internal;

`KEEP_FOR_DBG reg [3:0] clk_count; // clocks within a bit (16 per bit); the octet phase is bit_count[2:0]

assign addr = bit_count[(NUM_BIT_PAYLOAD_LENGTH+3):3];

// The byte for octet is asked of the packet buffer at [clk_count] 116 of the
// bit period before it: bit_count / 8 is then already the next byte's address
// (since [clk_count] 114) and the byte is taken 12 clocks later, at
// [clk_count] 0. The request also comes in the first 14 clocks of TX_PDU, for
// byte 0.
localparam [3:0] PDU_READ_CLOCK = 4;
wire pdu_read_request = (phy_tx_state == TX_PDU) && (clk_count == PDU_READ_CLOCK) && (bit_count[2:0] == 0);

assign i = (phy_tx_state == IDLE? 0 : i_internal);
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

// state machine to extract payload length and check crc
always @ (posedge clk) begin
  if (rst) begin
    payload_length <= 0;
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
          info_bit <= octet[0];
          info_bit_valid <= 1;

          bit_count <= bit_count + 1;

          if (bit_count == ((payload_length+2)*8 - 1)) begin
            info_bit_valid_last <= 1;
            phy_tx_state <= WAIT_LAST_SAMPLE;
          end
        end else begin
          info_bit_valid <= 0;
        end

        if (bit_count == 8 && clk_count == 1) begin
          payload_length <= octet;
        end

        if (bit_count == 9 && clk_count == 2) begin
          $display("payload_length %d", payload_length);
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

pdu_buffer # (
  .ADDRESS_WIDTH(NUM_BIT_PAYLOAD_LENGTH+1) // 2 header bytes + up to 2^NUM_BIT_PAYLOAD_LENGTH - 1 payload bytes
) btle_tx_pdu_buffer_i (
  .clkb(clkb),
  .write_address(pdu_octet_mem_addr),
  .write_data(pdu_octet_mem_data),

  .clk(clk),
  .rst(rst),
  .read_request(pdu_read_request),
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
  
  .cos_table_write_address(cos_table_write_address),
  .cos_table_write_data(cos_table_write_data),
  .sin_table_write_address(sin_table_write_address),
  .sin_table_write_data(sin_table_write_data),

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

endmodule

// The packet buffer (2026-10-04). Upstream keeps it in a memory with two ports
// and 2^ADDRESS_WIDTH words: the write port, on clkb (the AXI clock), writes
// the pair (write_address, write_data), the processor's register, on EVERY
// clkb clock; the read port, on clk, reads read_address on every clock, and
// btle_tx uses one read per byte. The TX reads only bytes 0 to
// 2^(ADDRESS_WIDTH-1): 2 header bytes and at most 2^(ADDRESS_WIDTH-1) - 1
// payload bytes. Here:
//   - one memory of 2^(ADDRESS_WIDTH-1) words with ONE port, on clkb, and a
//     register for byte 2^(ADDRESS_WIDTH-1); writes to the addresses above it,
//     which the TX never reads, are dropped;
//   - the pair is still written on every clkb clock, except the one that reads;
//   - btle_tx raises read_request for one clk clock, with read_address already
//     stable, and keeps read_address until it takes the byte. The request
//     toggles a flip-flop on clk; two flip-flops synchronize it to clkb; the
//     next clkb clock reads, and the one after puts the byte in read_data
//     (clkb domain). The byte is there 4 clkb clocks after the request at the
//     latest: within the 12 clk clocks btle_tx leaves before it takes the byte
//     when clkb runs at 8 MHz or faster.
// The bytes sent are upstream's whenever the packet is written before tx_start,
// as the upstream testbenches do (the repository's firmware does not
// transmit). A byte rewritten while it is being read (between the request and
// the clock in which btle_tx takes it) may differ: upstream reads it at the
// last of those clocks.
module pdu_buffer #
(
  parameter integer ADDRESS_WIDTH = 9
) (
  input  wire clkb,
  input  wire [ADDRESS_WIDTH-1:0] write_address,
  input  wire [7:0] write_data,

  input  wire clk,
  input  wire rst,
  input  wire read_request,
  input  wire [ADDRESS_WIDTH-1:0] read_address,
  output reg  [7:0] read_data
);

localparam integer RAM_ADDRESS_WIDTH = ADDRESS_WIDTH - 1;
localparam [ADDRESS_WIDTH-1:0] TOP_ADDRESS = 1 << RAM_ADDRESS_WIDTH;

// clk side: each request toggles request_toggle
reg request_toggle;
always @ (posedge clk) begin
  if (rst) begin
    request_toggle <= 0;
  end else if (read_request) begin
    request_toggle <= ~request_toggle;
  end
end

// clkb side
reg [1:0] rst_sync;     // rst, synchronized to clkb
reg [2:0] request_sync; // two synchronizing flip-flops, then the value seen last
reg ram_read_delay;
reg [7:0] top_byte;     // byte TOP_ADDRESS
wire clkb_rst = rst_sync[1];
wire read = request_sync[2] ^ request_sync[1];
wire read_top = read_address[ADDRESS_WIDTH-1]; // read_address is TOP_ADDRESS
wire ram_read = read && !read_top;
wire ram_write = !read && !write_address[ADDRESS_WIDTH-1];
wire [7:0] ram_read_data;

always @ (posedge clkb) begin
  rst_sync <= {rst_sync[0], rst};
  if (clkb_rst) begin
    request_sync <= 0;
    ram_read_delay <= 0;
  end else begin
    request_sync <= {request_sync[1:0], request_toggle};
    ram_read_delay <= ram_read;
  end

  if (write_address == TOP_ADDRESS) begin
    top_byte <= write_data;
  end

  if (read && read_top) begin
    read_data <= top_byte;
  end else if (ram_read_delay) begin
    read_data <= ram_read_data;
  end
end

pdu_buffer_ram # (
  .DATA_WIDTH(8),
  .ADDRESS_WIDTH(RAM_ADDRESS_WIDTH)
) pdu_buffer_ram_i (
  .clk(clkb),
  .rst(clkb_rst),

  .write_address(write_address[RAM_ADDRESS_WIDTH-1:0]),
  .write_data(write_data),
  .write_enable(ram_write),

  .read_address(read_address[RAM_ADDRESS_WIDTH-1:0]),
  .read_enable(ram_read),
  .read_data(ram_read_data)
);

endmodule

// One memory of 2^ADDRESS_WIDTH words of DATA_WIDTH bits with ONE port: a clock
// with write_enable writes write_address, a clock with read_enable reads
// read_address (the data is on read_data from the next clock on), and never
// both in one clock. A one-port macro has one address: the multiplexer that
// picks it is here, and the repository's RAM model (sdpram_one_clk) gets that
// address on both of its ports. The model also reads in the other clocks;
// pdu_buffer takes read_data only in the clock after a read.
module pdu_buffer_ram #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 8
) (
  input wire clk,
  input wire rst,

  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,

  input wire [ADDRESS_WIDTH-1:0] read_address,
  input wire read_enable,
  output wire [DATA_WIDTH-1:0] read_data
);

wire [ADDRESS_WIDTH-1:0] address = write_enable ? write_address : read_address;

sdpram_one_clk # (
  .DATA_WIDTH(DATA_WIDTH),
  .ADDRESS_WIDTH(ADDRESS_WIDTH)
) sdpram_one_clk_i (
  .clk(clk),
  .rst(rst),

  .write_address(address),
  .write_data(write_data),
  .write_enable(write_enable),

  .read_address(address),
  .read_data(read_data)
);

endmodule
