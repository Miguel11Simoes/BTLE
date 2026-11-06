// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0

// The tag of the proof of concept (ble-tx-poc, docs/PLANO_PoC.md section 3.1): a state machine, no
// processor, reads a sensor and sends its value in the tag's Legacy Advertising packet. The same core
// on the FPGA and in the ASIC; the sensor is not in the RTL but in a profile (scripts/senseworks/tag_profile.py
// documents the image): I2C or SPI, or an ADC with ADC_EN, the program that talks to it, the window that
// makes a byte of what it answers, the interval and the channel.
//
//   clocks     one clock, clk (16 MHz for btle_tx), and two enables: tick, 32 kHz, for the timers, and
//              bus_en, 64 kHz, for the bus (four phases per bit: SCL at 16 kHz). BUS_DIV = 250 makes them
//              from 16 MHz (the MMCM of the FPGA does not go down to 32 kHz); BUS_DIV = 1 ties them to 1,
//              for an ASIC clocked at 32.768 kHz between packets (then SCL is 8.2 kHz). That clock's switch
//              to 16 MHz for the packet is not in this core.
//   timers     the interval (profile, units of 32 ticks) + advDelay: an 8-bit LFSR, its seed AdvA's first
//              byte, one value per event, in ticks: 0..255 ticks, 0..8 ms, within the Core's 0..10 ms (Core
//              6.1, Vol 6 Part B 4.4.2.2). T_advEvent = interval + advDelay, start to start.
//   profile    CFG_SRC = 0, EEPROM (the proof of concept): at boot read over the I2C bus from address 0 of
//              the 24AA02E48 into flip-flops, with the EUI-48 at 0xFA..0xFF for AdvA; checked (version,
//              size, CRC-8); DEFAULT_PROFILE if it fails, ADV_ADDRESS and TX_ADD if the EUI-48 cannot be read.
//              CFG_SRC = 1, OTP: DEFAULT_PROFILE, compiled in, no flip-flops; AdvA is ADV_ADDRESS, or six
//              eFuse blocks with ADV_ADDRESS_OTP = 1.
//              CFG_SRC = 2, MTP: as OTP for AdvA; the profile read and checked as from the EEPROM, from a
//              byte-wide read port (mtp_*): mtp_read high with mtp_address until mtp_valid.
//   sequencer  runs the profile's boot program once and its measure program every event: XFER (I2C or
//              SPI), WAIT, END. A bus that stays stalled for about 128 ms, or a missing acknowledge, ends
//              the program; the event then sends 0xFF, and the next event tries again.
//   capture    tag_capture: the window, the sign, the offset, the saturation.
//   test mode  (profile) a counter instead of the sensor, the program not run, for the receiver to count
//              the packets lost.
//   btle_tx    the tag's transmitter, GAUSS_TABLE = 1 (no firmware), on the channel of the profile.
//
// At reset, and after a failure, the bus is cleared first: a STOP, nine clocks with SDA released, a STOP. A reset
// in the middle of a read leaves a slave holding SDA low until it has clocked its byte out (the nine clocks); in the
// middle of a write, it leaves a slave taking in bytes, to which those nine clocks would be a byte of 1s, written to
// its register: the first STOP, with SCL high a START and a STOP, ends the frame before them.

`define KEEP_FOR_DBG (*mark_debug="true",DONT_TOUCH="TRUE"*)

`timescale 1ns / 1ps
module tag_core #
(
  parameter integer CFG_SRC = 0,          // the profile: 0 EEPROM, 1 OTP (compiled in), 2 MTP
  parameter integer SENSOR_BYTES = 1,     // 1 or 2: the packet's bytes of sensor, and the captures
  parameter integer BCH_T = 8,            // passed to btle_tx
  parameter integer ADC_EN = 0,           // 1: an ADC as the profile's third choice of bus (tag_bus.v)
  parameter integer ADC_BITS = 12,
  parameter integer BUS_DIV = 250,        // clk clocks per bus_en, 2 bus_en per tick; 1: both tied to 1
  parameter integer ADV_ADDRESS_OTP = 0,  // 1: AdvA from six eFuse blocks (CFG_SRC 1 or 2), passed to btle_tx
  // AdvA and its TxAdd when not read from the EEPROM: a random static address (two top bits 11)
  parameter [47:0] ADV_ADDRESS = 48'hC10203040506,
  parameter integer TX_ADD = 1,
  parameter [15:0] COMPANY_ID = 16'hFFFF, // passed to btle_tx
  parameter [6:0] EEPROM_I2C_ADDRESS = 7'h50,
  // The profile compiled in: the TMP100 at 0x48, 9 bits, N = 2T + 80, an event per second, channel 37
  // (tag_profile.py --verilog; with SENSOR_BYTES = 2 the second byte's capture takes no bit: it reads 0)
  parameter [255:0] DEFAULT_PROFILE = 256'h0120e803250680095000b09001014d00b09001814da190009491000000000084
) (
  input  wire clk,
  input  wire rst,

  // the sensor bus (tag_bus.v), the EEPROM's too: scl_oe, sda_oe: pull the open-drain pin low
  input  wire scl_i,
  input  wire sda_i,
  input  wire miso_i,
  output wire scl_oe,
  output wire sda_oe,
  output wire cs_n,

  // ADC_EN = 1
  output wire adc_start,
  input  wire adc_done,
  input  wire [(ADC_BITS-1):0] adc_data,

  // CFG_SRC = 2
  output wire mtp_read,
  output wire [5:0] mtp_address,
  input  wire [7:0] mtp_data,
  input  wire mtp_valid,

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
  output wire event_done,                 // one clock at the end of each packet
  output wire [(8*SENSOR_BYTES-1):0] sensor,
  output wire sensor_failed,              // the last event's sensor did not answer
  output wire profile_ok,                 // the profile in use was read and checked; 0: DEFAULT_PROFILE
  output wire adv_address_read,           // AdvA is the EEPROM's EUI-48
  output wire tx_add,
  output wire [47:0] adv_address_sent,
  output wire [5:0] channel,
  output wire [15:0] interval,
  output wire test_mode,
  output wire [3:0] state_status
);

localparam integer CFG_SRC_EEPROM = 0, CFG_SRC_OTP = 1, CFG_SRC_MTP = 2;
localparam integer PROG_BYTES = 21;
localparam integer PROFILE_BYTES = 6 + 4*SENSOR_BYTES + PROG_BYTES + 1;    // 32, 36
localparam integer CFG_BITS = 8*PROFILE_BYTES;
localparam [7:0] PROFILE_VERSION = 8'h01;
localparam [7:0] PROFILE_SIZE = PROFILE_BYTES[7:0];
localparam [5:0] PROFILE_READS = PROFILE_BYTES[5:0];

localparam [3:0] ST_READY      = 4'd0,   // AdvA's OTP sensed
                 ST_CLEAR_READ = 4'd1,   // the bus clear, at reset and after a failure: ST_CLEAR_FIRST, these
                 ST_CLEAR_STOP = 4'd2,
                 ST_FETCH      = 4'd3,   // the next step of the program
                 ST_WAIT       = 4'd4,
                 ST_START      = 4'd5,   // an XFER: START, the bytes written, the bytes read, STOP
                 ST_WRITE      = 4'd6,
                 ST_READ       = 4'd7,
                 ST_STOP       = 4'd8,
                 ST_END        = 4'd9,   // the end of a program, by phase
                 ST_SLEEP      = 4'd10,  // the interval
                 ST_DELAY      = 4'd11,  // advDelay
                 ST_TX         = 4'd12,  // tx_start
                 ST_TX_WAIT    = 4'd13,
                 ST_MTP        = 4'd14,  // the profile from the MTP
                 ST_CLEAR_FIRST = 4'd15;

localparam [1:0] PH_LOAD_PROFILE = 2'd0, // the loader's program, reading the profile
                 PH_LOAD_EUI     = 2'd1, // the loader's program, reading the EUI-48
                 PH_BOOT         = 2'd2, // the profile's boot program
                 PH_MEASURE      = 2'd3; // the profile's measure program

localparam [1:0] CMD_START = 2'd0, CMD_STOP = 2'd1, CMD_WRITE = 2'd2, CMD_READ = 2'd3;
localparam [7:0] BUS_TIMEOUT = 8'd127;   // units of 32 ticks

`KEEP_FOR_DBG reg [3:0] state;
`KEEP_FOR_DBG reg [1:0] ph;
`KEEP_FOR_DBG reg [4:0] pc;
reg [2:0] w_left;
reg [5:0] r_left;
reg hold;
reg failed;
reg [7:0] wait_count;                    // WAIT and the bus timeout in units of 32 ticks, advDelay in ticks
reg [7:0] lfsr;
reg [(8*SENSOR_BYTES-1):0] sensor_r;
reg sensor_failed_r;
reg profile_ok_r;
reg eui_ok;
reg [4:0] prescale;
reg [15:0] interval_count;

wire bus_en, tick;

// --------------------------------------------------------------- the profile
wire [(CFG_BITS-1):0] cfg;
wire [(CFG_BITS-1):0] cfg_default;
wire [7:0] cfg_version = cfg[8*(PROFILE_BYTES-1) +: 8];
wire [7:0] cfg_size    = cfg[8*(PROFILE_BYTES-2) +: 8];
wire [15:0] cfg_interval = {cfg[8*(PROFILE_BYTES-4) +: 8], cfg[8*(PROFILE_BYTES-3) +: 8]};
wire [7:0] cfg_radio   = cfg[8*(PROFILE_BYTES-5) +: 8];  // [5:0] channel, [6] TxAdd, [7] test mode
wire [7:0] cfg_bus     = cfg[8*(PROFILE_BYTES-6) +: 8];  // [4:0] the measure program, [5] SPI, [6] CPOL, [7] ADC
wire cfg_test_mode = cfg_radio[7];
wire cfg_adc = (ADC_EN != 0) && cfg_bus[7];
wire [(8*32-1):0] cfg_programs = {cfg[(8*(PROG_BYTES+1)-1):8], {(8*(32-PROG_BYTES)){1'b0}}};  // what follows reads as END
wire [7:0] cfg_step = cfg_programs[{~pc, 3'b000} +: 8];

// The loader's program: the profile from address 0, 7 standing for PROFILE_READS; then the EUI-48 from 0xFA
localparam [7:0] XFER_ADDRESS = 8'b1_010_000_1, XFER_PROFILE = 8'b1_001_111_0, XFER_EUI = 8'b1_001_110_0;
localparam [4:0] LOADER_EUI_PC = 5'd6;
reg [7:0] loader_step;
always @(*) begin
  case (pc[3:0])
    4'd0:    loader_step = XFER_ADDRESS;
    4'd1:    loader_step = {EEPROM_I2C_ADDRESS, 1'b0};
    4'd2:    loader_step = 8'h00;
    4'd3:    loader_step = XFER_PROFILE;
    4'd4:    loader_step = {EEPROM_I2C_ADDRESS, 1'b1};
    4'd5:    loader_step = 8'h00;                       // END
    4'd6:    loader_step = XFER_ADDRESS;
    4'd7:    loader_step = {EEPROM_I2C_ADDRESS, 1'b0};
    4'd8:    loader_step = 8'hFA;
    4'd9:    loader_step = XFER_EUI;
    4'd10:   loader_step = {EEPROM_I2C_ADDRESS, 1'b1};
    default: loader_step = 8'h00;                       // END
  endcase
end

wire loading = (ph == PH_LOAD_PROFILE) || (ph == PH_LOAD_EUI);
wire [7:0] step = loading ? loader_step : cfg_step;

// --------------------------------------------------------------- the bus
wire in_clear = (state == ST_CLEAR_FIRST) || (state == ST_CLEAR_READ) || (state == ST_CLEAR_STOP);
wire bus_i2c = loading || in_clear;      // the EEPROM, and the bus clear, are I2C whatever the profile
wire bus_spi = cfg_bus[5] && !bus_i2c;
wire bus_adc = cfg_adc && !bus_i2c;
reg [1:0] bus_cmd;
always @(*) begin
  case (state)
    ST_START:                bus_cmd = CMD_START;
    ST_STOP, ST_CLEAR_FIRST, ST_CLEAR_STOP: bus_cmd = CMD_STOP;
    ST_WRITE:                bus_cmd = CMD_WRITE;
    default:                 bus_cmd = CMD_READ;
  endcase
end
wire bus_req = in_clear || (state == ST_START) || ((state == ST_WRITE) && (w_left != 3'd0)) ||
               ((state == ST_READ) && (r_left != 6'd0)) || ((state == ST_STOP) && !hold);
wire bus_done, bus_acked, bus_stalled, bus_rx_valid, bus_rx_bit;
wire ms_pulse = tick && (prescale == 5'd31);
wire bus_timeout = bus_stalled && ms_pulse && (wait_count == 8'd0);

tag_bus #(
  .ADC_EN(ADC_EN),
  .ADC_BITS(ADC_BITS)
) tag_bus_i (
  .clk(clk),
  .rst(rst),
  .bus_en(bus_en),
  .spi(bus_spi),
  .cpol(cfg_bus[6]),
  .adc(bus_adc),
  .cmd(bus_cmd),
  .req(bus_req),
  .write_data(step),
  .read_ack((state == ST_READ) && (r_left != 6'd1)),
  .abort(bus_timeout),
  .done(bus_done),
  .acked(bus_acked),
  .stalled(bus_stalled),
  .rx_valid(bus_rx_valid),
  .rx_bit(bus_rx_bit),
  .scl_i(scl_i),
  .sda_i(sda_i),
  .miso_i(miso_i),
  .scl_oe(scl_oe),
  .sda_oe(sda_oe),
  .cs_n(cs_n),
  .adc_start(adc_start),
  .adc_done(adc_done),
  .adc_data(adc_data)
);

wire read_bit = bus_rx_valid && (state == ST_READ);
wire eui_bit_valid = read_bit && (ph == PH_LOAD_EUI);
wire capture_bit_valid = read_bit && (ph == PH_MEASURE);

// --------------------------------------------------------------- the checks at the end of each load
wire profile_bit_valid, profile_bit, crc_zero, mtp_finished;
wire profile_good = !failed && (cfg_version == PROFILE_VERSION) && (cfg_size == PROFILE_SIZE) && crc_zero;
wire profile_rejected = (state == ST_END) && (ph == PH_LOAD_PROFILE) && !profile_good;
wire eui_rejected = (state == ST_END) && (ph == PH_LOAD_EUI) && failed;

// --------------------------------------------------------------- the event
wire event_start = (state == ST_DELAY) && tick && (wait_count == 8'd0);
wire tx_start = (state == ST_TX);
wire [7:0] lfsr_next = {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3] ^ (lfsr[6:0] == 7'd0)};  // 256 states, none stuck
wire [(8*SENSOR_BYTES-1):0] capture_value;
wire [47:0] adv_address_cfg;

always @ (posedge clk) begin
  if (rst) begin
    state <= ST_READY;
    ph <= (CFG_SRC == CFG_SRC_OTP) ? PH_BOOT : PH_LOAD_PROFILE;
    pc <= 5'd0;
    failed <= 1'b0;
    sensor_r <= {(8*SENSOR_BYTES){1'b1}};   // all 1s, so that the test mode's first value is 0
    sensor_failed_r <= 1'b0;
    profile_ok_r <= 1'b0;
    eui_ok <= 1'b0;
  end else begin
    case (state)
      ST_READY: begin
        if (adv_address_otp_ready) state <= ST_CLEAR_FIRST;
      end

      ST_CLEAR_FIRST: begin
        if (bus_done) state <= ST_CLEAR_READ;
      end

      ST_CLEAR_READ: begin
        if (bus_done) state <= ST_CLEAR_STOP;
      end

      ST_CLEAR_STOP: begin
        if (bus_done) begin
          if (failed) begin
            state <= ST_END;
          end else if ((CFG_SRC == CFG_SRC_MTP) && (ph == PH_LOAD_PROFILE)) begin
            state <= ST_MTP;
          end else begin
            state <= ST_FETCH;
          end
        end
      end

      ST_MTP: begin
        if (mtp_finished) state <= ST_END;
      end

      ST_FETCH: begin
        pc <= pc + 5'd1;
        if (step[7]) begin
          w_left <= step[6:4];
          r_left <= ((ph == PH_LOAD_PROFILE) && (step[3:1] == 3'd7)) ? PROFILE_READS : {3'd0, step[3:1]};
          hold <= step[0];
          state <= ST_START;
        end else if (step[6:0] != 7'd0) begin
          wait_count <= {1'b0, step[6:0]};
          state <= ST_WAIT;
        end else begin
          state <= ST_END;
        end
      end

      ST_WAIT: begin                        // k + 1 pulses of the free-running prescaler: at least k units
        if (ms_pulse) begin
          if (wait_count == 8'd0) begin
            state <= ST_FETCH;
          end else begin
            wait_count <= wait_count - 8'd1;
          end
        end
      end

      ST_START: begin
        if (bus_done) state <= ST_WRITE;
      end

      ST_WRITE: begin
        if (w_left == 3'd0) begin
          state <= ST_READ;
        end else if (bus_done) begin
          pc <= pc + 5'd1;
          w_left <= w_left - 3'd1;
          if (!bus_spi && !bus_adc && !bus_acked) begin
            failed <= 1'b1;
            state <= ST_CLEAR_FIRST;
          end
        end
      end

      ST_READ: begin
        if (r_left == 6'd0) begin
          state <= ST_STOP;
        end else if (bus_done) begin
          r_left <= r_left - 6'd1;
        end
      end

      ST_STOP: begin
        if (hold || bus_done) state <= ST_FETCH;
      end

      ST_END: begin
        failed <= 1'b0;
        case (ph)
          PH_LOAD_PROFILE: begin
            profile_ok_r <= profile_good;
            pc <= (CFG_SRC == CFG_SRC_EEPROM) ? LOADER_EUI_PC : 5'd0;
            ph <= (CFG_SRC == CFG_SRC_EEPROM) ? PH_LOAD_EUI : PH_BOOT;
            state <= ST_FETCH;
          end
          PH_LOAD_EUI: begin
            if (CFG_SRC == CFG_SRC_EEPROM) eui_ok <= !failed;
            pc <= 5'd0;
            ph <= PH_BOOT;
            state <= ST_FETCH;
          end
          PH_BOOT: begin
            lfsr <= adv_address_sent[7:0];
            state <= ST_SLEEP;
          end
          default: begin                    // PH_MEASURE
            sensor_r <= failed ? {(8*SENSOR_BYTES){1'b1}} : capture_value;
            sensor_failed_r <= failed;
            state <= ST_TX;
          end
        endcase
      end

      ST_SLEEP: begin
        if (interval_count == 16'd0) begin
          wait_count <= lfsr;
          state <= ST_DELAY;
        end
      end

      ST_DELAY: begin
        if (tick) begin
          if (wait_count == 8'd0) begin
            lfsr <= lfsr_next;
            if (cfg_test_mode) begin
              sensor_r <= sensor_r + 1'b1;
              state <= ST_TX;
            end else begin
              ph <= PH_MEASURE;
              pc <= cfg_bus[4:0];
              state <= ST_FETCH;
            end
          end else begin
            wait_count <= wait_count - 8'd1;
          end
        end
      end

      ST_TX: begin
        state <= ST_TX_WAIT;
      end

      ST_TX_WAIT: begin
        if (iq_valid_last) state <= ST_SLEEP;
      end

      default: ;
    endcase

    if (in_clear || (state == ST_START) || (state == ST_WRITE) || (state == ST_READ) || (state == ST_STOP)) begin
      if (!bus_stalled) begin
        wait_count <= BUS_TIMEOUT;
      end else if (ms_pulse) begin
        wait_count <= wait_count - 8'd1;
      end
    end

    if (bus_timeout) begin
      failed <= 1'b1;
      state <= in_clear ? ST_END : ST_CLEAR_FIRST;
    end
  end
end

// The timers. The prescaler restarts with the event, so T_advEvent is exact in ticks.
always @ (posedge clk) begin
  if (rst) begin
    prescale <= 5'd0;
    interval_count <= 16'd0;
  end else begin
    if (event_start) begin
      prescale <= 5'd0;
      interval_count <= cfg_interval;
    end else begin
      if (tick) prescale <= prescale + 5'd1;
      if (ms_pulse && (interval_count != 16'd0)) interval_count <= interval_count - 16'd1;
    end
  end
end

generate
if (BUS_DIV > 1) begin : gen_bus_divider
  localparam integer DIV_BITS = $clog2(BUS_DIV);
  localparam integer DIV_LAST_INT = BUS_DIV - 1;
  localparam [(DIV_BITS-1):0] DIV_LAST = DIV_LAST_INT[(DIV_BITS-1):0];
  reg [(DIV_BITS-1):0] bus_count;
  reg tick_half;
  always @ (posedge clk) begin
    if (rst) begin
      bus_count <= {DIV_BITS{1'b0}};
      tick_half <= 1'b0;
    end else if (bus_count == DIV_LAST) begin
      bus_count <= {DIV_BITS{1'b0}};
      tick_half <= !tick_half;
    end else begin
      bus_count <= bus_count + 1'b1;
    end
  end
  assign bus_en = (bus_count == DIV_LAST);
  assign tick = bus_en && tick_half;
end else begin : gen_no_bus_divider
  assign bus_en = 1'b1;
  assign tick = 1'b1;
end

if (SENSOR_BYTES == 2) begin : gen_default_two_captures
  assign cfg_default = {DEFAULT_PROFILE[255:176], 32'd0, DEFAULT_PROFILE[175:0]};
end else begin : gen_default_one_capture
  assign cfg_default = DEFAULT_PROFILE;
end

// The profile: flip-flops with the copy, or the constants when it is compiled in. The bits arrive most
// significant first, byte 0 first, so it is a shift register with byte 0 on top.
if (CFG_SRC == CFG_SRC_OTP) begin : gen_cfg_compiled
  assign cfg = cfg_default;
  assign crc_zero = 1'b1;
  wire unused_profile_bit = &{1'b0, profile_bit_valid, profile_bit, profile_rejected};
end else begin : gen_cfg_registers
  reg [(CFG_BITS-1):0] cfg_r;
  reg [7:0] crc;                         // x^8 + x^2 + x + 1, from 0xFF: 0 over the whole image
  always @ (posedge clk) begin
    if (rst || profile_rejected) begin
      cfg_r <= cfg_default;
    end else if (profile_bit_valid) begin
      cfg_r <= {cfg_r[(CFG_BITS-2):0], profile_bit};
    end
    if (rst) begin
      crc <= 8'hFF;
    end else if (profile_bit_valid) begin
      crc <= {crc[6:0], 1'b0} ^ ({8{crc[7] ^ profile_bit}} & 8'h07);
    end
  end
  assign cfg = cfg_r;
  assign crc_zero = (crc == 8'h00);
end

if (CFG_SRC == CFG_SRC_MTP) begin : gen_profile_mtp
  reg [5:0] index;
  reg [7:0] shift;
  reg [3:0] bits_left;
  always @ (posedge clk) begin
    if (rst) begin
      index <= 6'd0;
      bits_left <= 4'd0;
    end else if (bits_left != 4'd0) begin
      shift <= {shift[6:0], 1'b0};
      bits_left <= bits_left - 4'd1;
      if (bits_left == 4'd1) index <= index + 6'd1;
    end else if (mtp_read && mtp_valid) begin
      shift <= mtp_data;
      bits_left <= 4'd8;
    end
  end
  assign mtp_read = (state == ST_MTP) && (bits_left == 4'd0);
  assign mtp_address = index;
  assign mtp_finished = (bits_left == 4'd1) && (index == PROFILE_READS - 6'd1);
  assign profile_bit_valid = (bits_left != 4'd0);
  assign profile_bit = shift[7];
end else begin : gen_profile_bus
  assign mtp_read = 1'b0;
  assign mtp_address = 6'd0;
  assign mtp_finished = 1'b0;
  assign profile_bit_valid = read_bit && (ph == PH_LOAD_PROFILE);
  assign profile_bit = bus_rx_bit;
  wire unused_mtp_inputs = &{1'b0, mtp_data, mtp_valid};
end

// AdvA: the EUI-48, most significant byte first in the EEPROM (OUI at 0xFA, DS22124D section 9.0)
if (CFG_SRC == CFG_SRC_EEPROM) begin : gen_adv_eeprom
  reg [47:0] adv_r;
  always @ (posedge clk) begin
    if (rst || eui_rejected) begin
      adv_r <= ADV_ADDRESS;
    end else if (eui_bit_valid) begin
      adv_r <= {adv_r[46:0], bus_rx_bit};
    end
  end
  assign adv_address_cfg = adv_r;
end else begin : gen_adv_compiled
  assign adv_address_cfg = ADV_ADDRESS;
  wire unused_eui_inputs = &{1'b0, eui_bit_valid, eui_rejected};
end

genvar c;
for (c = 0; c < SENSOR_BYTES; c = c + 1) begin : gen_capture
  wire [7:0] cfg_skip = cfg[8*(PROFILE_BYTES-7-4*c) +: 8];  // [7] signed, [5:0] the bits to skip
  wire [7:0] cfg_take = cfg[8*(PROFILE_BYTES-8-4*c) +: 8];  // [4:0] the bits to take
  wire [15:0] cfg_offset = {cfg[8*(PROFILE_BYTES-10-4*c) +: 8], cfg[8*(PROFILE_BYTES-9-4*c) +: 8]};
  tag_capture tag_capture_i (
    .clk(clk),
    .clear(event_start),
    .bit_valid(capture_bit_valid),
    .bit_in(bus_rx_bit),
    .skip(cfg_skip[5:0]),
    .take(cfg_take[4:0]),
    .is_signed(cfg_skip[7]),
    .offset(cfg_offset),
    .value(capture_value[8*c +: 8])
  );
  wire unused_cfg_bits = &{1'b0, cfg_skip[6], cfg_take[7:5]};
end
endgenerate

assign tx_add = eui_ok ? cfg_radio[6] : (TX_ADD != 0);
assign sensor = sensor_r;
assign sensor_failed = sensor_failed_r;
assign profile_ok = profile_ok_r;
assign adv_address_read = eui_ok;
assign channel = cfg_radio[5:0];
assign interval = cfg_interval;
assign test_mode = cfg_test_mode;
assign state_status = state;
assign event_done = (state == ST_TX_WAIT) && iq_valid_last;

wire [3:0] btle_tx_tap_index = 4'd15;     // GAUSS_TABLE = 1: its taps are fixed
wire [15:0] btle_tx_tap_value = 16'd0;

btle_tx #(
  .GAUSS_TABLE(1),
  .ADV_ADDRESS_OTP(ADV_ADDRESS_OTP),
  .COMPANY_ID(COMPANY_ID),
  .BCH_T(BCH_T),
  .SENSOR_BYTES(SENSOR_BYTES)
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
  .channel_number(cfg_radio[5:0]),
  .channel_number_load(tx_start),

  .adv_address(adv_address_cfg),
  .tx_add(tx_add),
  .sensor(sensor_r),

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

generate
if (CFG_SRC < CFG_SRC_EEPROM || CFG_SRC > CFG_SRC_MTP) begin : gen_cfg_src_check
  initial $fatal(1, "tag_core: CFG_SRC must be 0 (EEPROM), 1 (OTP) or 2 (MTP)");
end
if (ADV_ADDRESS_OTP != 0 && CFG_SRC == CFG_SRC_EEPROM) begin : gen_otp_check
  initial $fatal(1, "tag_core: with CFG_SRC = 0 AdvA is the EEPROM's EUI-48: ADV_ADDRESS_OTP must be 0");
end
endgenerate

wire unused_crc_byte = &{1'b0, cfg[7:0]};    // checked as the bits arrive

endmodule
