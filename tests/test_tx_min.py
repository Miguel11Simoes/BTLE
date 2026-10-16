"""Check the Legacy Advertising transmitter of ble-tx-min against upstream's, clock by clock, with Icarus Verilog.

Author: Miguel Simões

Run from the repository root with IVERILOG and VVP in PATH (or set their
environment variables).

REF is the corrected master btle_tx (REF_REV, override with --ref-rev; every
module renamed *_ref): the runtime Gaussian FIR loaded with the project's taps,
the VCO with the full COS and SIN tables, and the packet buffer in a memory of
512 bytes with two ports. DUT is this branch's btle_tx with GAUSS_TABLE=1: the
constant taps, the ROM VCO of ble-tx-rom, and the Legacy Advertising packet
buffer: the header in two registers, AdvA (PDU bytes 2..7) fixed per chip in
ADV_ADDRESS, AdvData (bytes 8..38) in a 32 x 8 memory with one port on clkb, or
in flip-flops (ADV_DATA_FLOPS=1). Every output of btle_tx is compared on every
clk clock from the first reset on (case inequality, plus explicit rejection of
unknown valid samples).

The contract: a PDU of at most 39 bytes (payload length L <= 37) whose bytes
2..7 are the chip's AdvA, written before tx_start. Each build has its own AdvA:
the project's (01:02:03:04:05:06) and a random one.

Stimulus (seeded, +seed=N): the taps and both tables written as the upstream TX
testbench writes them, the taps again after every reset; then packets: lengths
37 (the longest: AdvA and 31 bytes of AdvData) and 6 (AdvA alone) first,
random 0..37 after; each written through the (address, data) pair on clkb, one
pair per clkb clock with random gaps, after pairs to addresses the packet does
not use (up to 511) and, half of the time, after a first random version of all
its bytes (bytes 2..7 included: the DUT must ignore them, as REF ends with the
chip's AdvA there); random channel, access address, CRC init and preamble;
tx_start, sometimes held for several clocks; while sending, at random: pairs
to addresses outside the packet, access-address and preamble changes, CRC and
channel loads, table entries rewritten (same values), extra tx_start pulses,
and resets of 1 to 3 clocks that abort the packet. Never: a packet byte
rewritten while the packet is sent.

Then, outside the contract, the DUT alone: a header with L = 38..255 must send
the header as written, 37 payload bytes and the CRC (40 + 39 * 8 + 24 = 376
PHY bits), and end in IDLE.

The campaign runs every seed with clkb = clk and with clkb free at 100, 33.3,
16.1, 10 and 8 MHz, on four DUT builds per AdvA: the repository's RAM model,
the one-port macro model of the AdvData memory (one address; the output
changes only in a clock that reads; an ERROR line if a clock both writes and
reads), AdvData in flip-flops, and AdvA from the OTP (ADV_ADDRESS_OTP=1, the
six eFuse blocks on tests/efuse_async_mem_1x8_model.v, ADV_ADDRESS set to 0):
the unprogrammed chip must read 0, then AdvA is programmed once (51.25 us)
and sensed after a reset, before the first packet.

  python3 tests/test_tx_min.py [--seeds N] [--packets N] [--jobs N] [--mutants]
  python3 tests/test_tx_min.py --write-one-port FILE

With --mutants, each deliberate fault must make a run fail with a concrete
mismatch. --write-one-port writes verilog/btle_tx.v with the AdvData memory on
the one-port macro model (model included), for whole-system testbenches.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/validation"))
sys.path.insert(0, str(ROOT / "tests"))
from result_guard import sim_pass, mutant_caught, positive

REF_REV = "fca6ac64fb28cd57a496cb45af62cf9e0f9209d5"  # master after the lint closure
TX_FILES = ["btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v", "scramble_core.v",
            "gfsk_modulation.v", "bit_repeat_upsample.v", "gauss_filter.v", "vco.v",
            "sdpram_one_clk.v", "sdpram_two_clk.v"]
DUT_FILES = [f for f in TX_FILES if f != "sdpram_two_clk.v"]
TAPS = [0, 0, 0, 1, 4, 9, 15, 22, 24]  # taps 0..8 of python/btlelib.py (BT = 0.5, 8 samples/symbol)
CLKB_HALF_PS = [0, 5000, 15000, 31057, 50000, 62500]  # 0: clkb = clk; else 100, 33.3, 16.1, 10, 8 MHz
MODELS = ("ram", "macro", "flops", "otp")
PROJECT_ADV_ADDRESS = 0x010203040506

# The one-port macro of the AdvData memory: one address (the write address in a
# clock with a write, the read address in a clock with a read), the output
# changed only by a read.
PDU_MACRO = r"""
`timescale 1ns/1ps
module pdu_buffer_macro #
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
  output reg [DATA_WIDTH-1:0] read_data
);
  reg [DATA_WIDTH-1:0] memory [0:(1<<ADDRESS_WIDTH)-1];
  always @(posedge clk) begin
    if (write_enable && read_enable) begin
      $display("ERROR pdu_buffer_macro: a write and a read in one clock at %0t", $time);
      read_data <= {DATA_WIDTH{1'bx}};
    end else if (write_enable) begin
      memory[write_address] <= write_data;
    end else if (read_enable) begin
      read_data <= memory[read_address];
    end
  end
endmodule
"""

TB = r"""
`timescale 1ns/1ps
module tb_tx_min;
  reg clk = 0;
  always #31.25 clk = ~clk;                       // clk: 16 MHz
  reg clkb_free = 0;
  integer clkb_half_ps;
  initial begin : clkb_generator
    if (!$value$plusargs("clkb_half_ps=%d", clkb_half_ps)) clkb_half_ps = 0;
    if (clkb_half_ps > 0) begin
      #7.3;
      forever #(clkb_half_ps / 1000.0) clkb_free = ~clkb_free;
    end
  end
  wire clkb = (clkb_half_ps > 0) ? clkb_free : clk;

  localparam [47:0] ADV = `ADV;                   // the chip's AdvA
  localparam integer MAX_L = 37;

  reg rst = 1;
  reg [3:0] tap_index = 15;
  reg signed [15:0] tap_value = 0;
  reg [10:0] cos_address = 0, sin_address = 0;
  reg signed [7:0] cos_data = 0, sin_data = 0;
  reg [7:0] preamble = 8'haa;
  reg [31:0] access_address = 32'h8e89bed6;
  reg [23:0] crc_init = 24'h555555;
  reg crc_load = 0, channel_load = 0;
  reg [5:0] channel = 37;
  reg [8:0] pair_address = 0;
  reg [7:0] pair_data = 0;
  reg tx_start = 0;

  `define TX_PORTS(p) \
    .clk(clk), .rst(rst), .clkb(clkb), \
    .gauss_filter_tap_index(tap_index), .gauss_filter_tap_value(tap_value), \
    .cos_table_write_address(cos_address), .cos_table_write_data(cos_data), \
    .sin_table_write_address(sin_address), .sin_table_write_data(sin_data), \
    .preamble(preamble), .access_address(access_address), \
    .crc_state_init_bit(crc_init), .crc_state_init_bit_load(crc_load), \
    .channel_number(channel), .channel_number_load(channel_load), \
    .pdu_octet_mem_data(pair_data), .pdu_octet_mem_addr(pair_address), \
    .tx_start(tx_start), \
    .i(p``_i), .q(p``_q), .iq_valid(p``_iqv), .iq_valid_last(p``_iqvl), \
    .phy_bit(p``_pb), .phy_bit_valid(p``_pbv), .phy_bit_valid_last(p``_pbvl), \
    .bit_upsample(p``_bu), .bit_upsample_valid(p``_buv), .bit_upsample_valid_last(p``_buvl), \
    .bit_upsample_gauss_filter(p``_g), .bit_upsample_gauss_filter_valid(p``_gv), \
    .bit_upsample_gauss_filter_valid_last(p``_gvl)
  `define TX_WIRES(p) \
    wire signed [7:0] p``_i, p``_q; wire p``_iqv, p``_iqvl, p``_pb, p``_pbv, p``_pbvl, p``_bu, p``_buv, p``_buvl; \
    wire signed [15:0] p``_g; wire p``_gv, p``_gvl;
  `TX_WIRES(r)
  `TX_WIRES(d)
  btle_tx_ref ref_i (`TX_PORTS(r));
  // OTP builds: AdvA from the eFuse blocks, programmed below; ADV_ADDRESS 0 shows it is not used
  reg [47:0] otp_prog = 0;
  wire d_otp_ready;
  btle_tx #(.GAUSS_TABLE(1), .ADV_ADDRESS(`OTP ? 48'h0 : ADV), .ADV_DATA_FLOPS(`FLOPS), .ADV_ADDRESS_OTP(`OTP))
    dut_i (`TX_PORTS(d), .adv_address_otp_prog(otp_prog), .adv_address_otp_ready(d_otp_ready));
  wire [43:0] r_out = {r_i, r_q, r_iqv, r_iqvl, r_pb, r_pbv, r_pbvl, r_bu, r_buv, r_buvl, r_g, r_gv, r_gvl};
  wire [43:0] d_out = {d_i, d_q, d_iqv, d_iqvl, d_pb, d_pbv, d_pbvl, d_bu, d_buv, d_buvl, d_g, d_gv, d_gvl};

  reg signed [7:0] cos_t [0:2047];
  reg signed [7:0] sin_t [0:2047];
  reg signed [15:0] taps [0:8];
  initial begin
    $readmemh("cos.hex", cos_t);
    $readmemh("sin.hex", sin_t);
    $readmemh("taps.hex", taps);
  end

  integer seed, seed0, n_packets, gap_max;
  integer checked = 0, iq_samples = 0, iq_nonzero = 0, resets = 0, packets_started = 0, packets_sent = 0;
  integer pair_writes_sending = 0, aa_changes = 0, loads = 0, table_rewrites = 0, extra_starts = 0;
  integer p, n, k, len, clocks, aborted, phy_bits, overlong;
  integer packet_end = 0;
  reg compare_on = 0;
  reg sending = 0;

  function integer urand(input integer range);
    urand = $unsigned($random(seed)) % range;
  endfunction

  // byte n of a packet of length len: AdvA at bytes 2..7, random elsewhere
  function [7:0] packet_byte(input integer n, input integer len);
    if (n == 1) packet_byte = len;
    else if (n >= 2 && n <= 7) packet_byte = ADV >> (8 * (n - 2));
    else packet_byte = $random(seed);
  endfunction

  // every output on every clk clock, from the first reset on
  always @(posedge clk) begin
    if (compare_on) begin
      checked = checked + 1;
      if (r_out !== d_out) begin
        $display("MISMATCH at %0t ns (packet %0d): ref I/Q %0d/%0d valid/last %b/%b bit %b%b%b upsample %b%b%b gauss %0d %b%b; dut I/Q %0d/%0d valid/last %b/%b bit %b%b%b upsample %b%b%b gauss %0d %b%b",
                 $time, p, r_i, r_q, r_iqv, r_iqvl, r_pb, r_pbv, r_pbvl, r_bu, r_buv, r_buvl, r_g, r_gv, r_gvl,
                 d_i, d_q, d_iqv, d_iqvl, d_pb, d_pbv, d_pbvl, d_bu, d_buv, d_buvl, d_g, d_gv, d_gvl);
        $fatal(1, "first difference");
      end
      if ((^{r_iqv,d_iqv,r_iqvl,d_iqvl}) === 1'bx ||
          (r_iqv && (^{r_i,r_q}) === 1'bx) || (d_iqv && (^{d_i,d_q}) === 1'bx))
        $fatal(1, "UNKNOWN valid transmitter output");
      if (r_iqv) begin
        iq_samples = iq_samples + 1;
        if (r_i != 0 || r_q != 0) iq_nonzero = iq_nonzero + 1;
      end
    end
  end

  // while a packet is sent: pairs to addresses the packet does not use
  always @(posedge clkb) begin
    if (sending && urand(16) == 0) begin
      pair_address <= packet_end + urand(512 - packet_end);
      pair_data <= $random(seed);
      pair_writes_sending = pair_writes_sending + 1;
    end
  end

  task write_pair(input integer address, input integer data);
    begin
      @(posedge clkb);
      pair_address <= address;
      pair_data <= data;
      repeat (urand(gap_max + 1)) @(posedge clkb);
    end
  endtask

  task load_taps;  // upstream's FIR loses its taps at every reset
    begin
      for (k = 0; k < 9; k = k + 1) begin
        @(posedge clk); tap_index <= k; tap_value <= taps[k];
      end
      @(posedge clk); tap_index <= 15; tap_value <= 0;
    end
  endtask

  task reset_clocks(input integer n);
    begin
      @(posedge clk); rst <= 1; tx_start <= 0; crc_load <= 0; channel_load <= 0;
      repeat (n) @(posedge clk);
      rst <= 0;
      resets = resets + 1;
      load_taps;
    end
  endtask

  task rewrite_table_entry;  // the same value again, at a random address
    begin
      k = urand(2048);
      cos_address <= k; cos_data <= cos_t[k];
      sin_address <= k; sin_data <= sin_t[k];
      table_rewrites = table_rewrites + 1;
    end
  endtask

  task start_packet;
    begin
      @(posedge clk);
      channel <= urand(40);
      access_address <= $random(seed);
      crc_init <= $random(seed);
      preamble <= $random(seed);
      repeat (urand(4)) @(posedge clk);
      tx_start <= 1; crc_load <= 1; channel_load <= 1;
      @(posedge clk);
      crc_load <= 0; channel_load <= 0;
      repeat (urand(3)) @(posedge clk);            // tx_start sometimes held for a few clocks
      tx_start <= 0;
    end
  endtask

  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    seed0 = seed;
    if (!$value$plusargs("packets=%d", n_packets)) n_packets = 10;
    if (!$value$plusargs("gap=%d", gap_max)) gap_max = 2;
    if (n_packets < 2) begin $display("ERROR: at least 2 packets"); $fatal(1, "bad arguments"); end
    p = -1;
    repeat (3) @(posedge clk);
    compare_on <= 1;                               // rst has been high since time 0
    repeat (5) @(posedge clk);
    rst <= 0;
    resets = resets + 1;
    load_taps;
    if (`OTP) begin                                // an unprogrammed chip, then AdvA programmed once
      if (dut_i.btle_tx_pdu_buffer_i.adv_address !== 48'h0 || d_otp_ready !== 1'b1) begin
        $display("MISMATCH unprogrammed OTP: reads %h (ready %b), expected 0 (ready 1)", dut_i.btle_tx_pdu_buffer_i.adv_address, d_otp_ready);
        $fatal(1, "otp");
      end
      otp_prog <= ADV;
      repeat (820) @(posedge clk);               // 51.25 us >= Tprog (50 us)
      otp_prog <= 0;
      reset_clocks(2);                             // the fuses are sensed after a reset
      if (d_otp_ready !== 1'b1) begin $display("MISMATCH OTP not ready after reset"); $fatal(1, "otp"); end
    end
    for (k = 0; k < 2048; k = k + 1) begin         // as the upstream TX testbench: one entry per clock
      @(posedge clk);
      cos_address <= k; cos_data <= cos_t[k];
      sin_address <= k; sin_data <= sin_t[k];
    end
    for (p = 0; p < n_packets; p = p + 1) begin
      len = (p == 0) ? MAX_L : (p == 1) ? 6 : urand(MAX_L + 1);
      packet_end = len + 2;
      for (n = urand(12) + 4; n > 0; n = n - 1)
        write_pair(packet_end + urand(512 - packet_end), $random(seed));
      if (urand(2))
        for (n = 0; n < packet_end; n = n + 1 + urand(4)) write_pair(n, $random(seed));
      for (n = 0; n < packet_end; n = n + 1)
        write_pair(n, packet_byte(n, len));
      if (urand(2)) write_pair(packet_end + urand(512 - packet_end), $random(seed));
      start_packet;
      packets_started = packets_started + 1;
      sending = 1;
      aborted = 0;
      clocks = 0;
      while (!r_iqvl && !aborted) begin
        @(posedge clk);
        clocks = clocks + 1;
        tx_start <= 0; crc_load <= 0; channel_load <= 0;
        if (clocks > 400000) begin $display("ERROR: packet %0d never ended", p); $fatal(1, "testbench"); end
        if (urand(400) == 0) begin access_address <= $random(seed); preamble <= $random(seed); aa_changes = aa_changes + 1; end
        if (urand(3000) == 0) begin crc_init <= $random(seed); channel <= urand(40); crc_load <= urand(2); channel_load <= 1; loads = loads + 1; end
        if (urand(150) == 0) rewrite_table_entry;
        if ((ref_i.phy_tx_state == 1 || ref_i.phy_tx_state == 2) && urand(500) == 0) begin tx_start <= 1; extra_starts = extra_starts + 1; end
        if (p > 1 && urand(30000) == 0) begin
          sending = 0;
          reset_clocks(1 + urand(3));
          aborted = 1;
        end
      end
      sending = 0;
      if (!aborted) packets_sent = packets_sent + 1;
      repeat (urand(4) == 0 ? 0 : urand(64)) @(posedge clk);
    end
    repeat (200) @(posedge clk);
    if (!(packets_sent >= 2 && iq_nonzero > 0 && checked > 0)) begin
      $display("ERROR: campaign too small: %0d packets sent, %0d non-zero samples", packets_sent, iq_nonzero);
      $fatal(1, "testbench");
    end

    // outside the contract, the DUT alone: a header length above 37
    compare_on <= 0;
    overlong = MAX_L + 1 + urand(255 - MAX_L);
    for (n = 0; n < MAX_L + 2; n = n + 1) write_pair(n, packet_byte(n, overlong));
    start_packet;
    phy_bits = 0;
    clocks = 0;
    while (!d_iqvl) begin
      @(posedge clk);
      if (d_pbv) phy_bits = phy_bits + 1;
      clocks = clocks + 1;
      if (clocks > 400000) begin $display("ERROR: the overlong packet never ended"); $fatal(1, "testbench"); end
    end
    repeat (4) @(posedge clk);
    if (phy_bits != 40 + (MAX_L + 2) * 8 + 24 || dut_i.phy_tx_state != 0) begin
      $display("MISMATCH overlong header (L = %0d): %0d PHY bits, expected %0d; state %0d",
               overlong, phy_bits, 40 + (MAX_L + 2) * 8 + 24, dut_i.phy_tx_state);
      $fatal(1, "overlong");
    end

    $display("PASS seed %0d clkb_half_ps %0d: %0d clocks compared, %0d packets sent (%0d started), %0d resets, %0d IQ samples (%0d non-zero), %0d pairs written while sending, %0d access-address changes, %0d CRC/channel loads, %0d table rewrites, %0d extra tx_start; overlong L = %0d: %0d PHY bits",
             seed0, clkb_half_ps, checked, packets_sent, packets_started, resets, iq_samples, iq_nonzero,
             pair_writes_sending, aa_changes, loads, table_rewrites, extra_starts, overlong, phy_bits);
    $finish;
  end
endmodule
"""

MUTANTS = [
    ("btle_tx.v", "the byte is asked at [clk_count] 113, before its address is set",
     [("localparam [3:0] PDU_READ_CLOCK = 4;", "localparam [3:0] PDU_READ_CLOCK = 1;")]),
    ("btle_tx.v", "AdvA byte 2 taken from the most significant byte",
     [("default: adv_address_byte = adv_address[7:0];", "default: adv_address_byte = adv_address[47:40];")]),
    ("btle_tx.v", "header byte 1 read from the register of byte 0",
     [("read_data <= read_address[0] ? header1 : header0;", "read_data <= header0;")]),
    ("btle_tx.v", "the AdvData memory written in the clock that reads too",
     [(".write_enable(write_adv_data && !read),", ".write_enable(write_adv_data),")]),
    ("btle_tx.v", "byte 38, the last AdvData byte, not stored",
     [("is_adv_data = (a >= 8) && (a <= 38);", "is_adv_data = (a >= 8) && (a <= 37);")]),
    ("btle_tx.v", "the AdvData flip-flops read one byte off",
     [("assign adv_data_read = adv_data[read_address[4:0]];", "assign adv_data_read = adv_data[read_address[4:0] + 5'd1];")]),
    ("btle_tx.v", "the last bit one byte late",
     [("if (bit_count == {payload_length + 6'd1, 3'b111}) begin", "if (bit_count == {payload_length + 6'd2, 3'b111}) begin")]),
    ("btle_tx.v", "the length saturates at 36, not 37",
     [("localparam [5:0] MAX_PAYLOAD_LENGTH = 6'd37;", "localparam [5:0] MAX_PAYLOAD_LENGTH = 6'd36;")]),
    ("btle_tx.v", "payload_length taken from the wrong byte",
     [("if (bit_count == 8 && clk_count == 1) begin", "if (bit_count == 16 && clk_count == 1) begin")]),
    ("btle_tx.v", "octet loaded one bit period late",
     [("if (clk_count == 0 && bit_count[2:0] == 0) begin // speed 1/8M",
       "if (clk_count == 0 && bit_count[2:0] == 1) begin // speed 1/8M")]),
    ("bit_repeat_upsample.v", "the last marker occurs one repeat early",
     [("saved_last && (remaining == 1)", "saved_last && (remaining == 2)")]),
    ("crc24.v", "the CRC bits sent in the wrong order",
     [("lfsr[~bit_count[4:0]]", "lfsr[bit_count[4:0] - 5'd8]")]),
    ("scramble.v", "the whitening starts one bit late",
     [("end else if (data_in_valid && data_in_count != 41) begin",
       "end else if (data_in_valid && data_in_count != 40) begin")]),
    ("gauss_filter.v", "the sum of the taps added instead of subtracted",
     [("assign table_sum = (half_sum <<< 1) - tap_total(0);", "assign table_sum = (half_sum <<< 1) + tap_total(0);")]),
    ("btle_tx.v", "the OTP bytes in the wrong order",
     [(".out(adv_address[8*b +: 8]),", ".out(adv_address[8*(5-b) +: 8]),")]),
    ("btle_tx.v", "the OTP never sensed (reset_n held high)",
     [(".reset_n(~rst),", ".reset_n(1'b1),")]),
]


def git_show(rev: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"cannot read {path} from {rev}")
    return result.stdout


def pdu_one_port(btle_tx_text: str) -> str:
    """verilog/btle_tx.v with the AdvData memory on the one-port macro model (not included)."""
    text = btle_tx_text.replace("module pdu_buffer_ram #", "module pdu_buffer_ram_unused #", 1)
    if "pdu_buffer_ram # (" not in text:
        raise SystemExit("cannot find the instance of pdu_buffer_ram in verilog/btle_tx.v")
    return text.replace("pdu_buffer_ram # (", "pdu_buffer_macro # (")


def reference_files(work: Path) -> list[Path]:
    texts = {f: git_show(REF_REV, f"verilog/{f}") for f in TX_FILES}
    names = sorted({m for t in texts.values() for m in re.findall(r"^\s*module\s+(\w+)", t, re.M)})
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b")
    paths = []
    for f, t in texts.items():
        path = work / ("ref_" + f)
        path.write_text(pattern.sub(lambda m: m.group(1) + "_ref", t))
        paths.append(path)
    return paths


def build(work: Path, name: str, texts: dict[str, str], model: str, adv: int, refs: list[Path]) -> Path:
    d = work / name
    d.mkdir()
    files = []
    for f, t in texts.items():
        if model == "macro" and f == "btle_tx.v":
            t = pdu_one_port(t)
        (d / f).write_text(t)
        files.append(str(d / f))
    if model == "macro":
        (d / "macros.v").write_text(PDU_MACRO)
        files.append(str(d / "macros.v"))
    if model == "otp":
        files.append(str(ROOT / "tests" / "efuse_async_mem_1x8_model.v"))
    out = d / "tb.vvp"
    result = subprocess.run(
        [os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tb_tx_min", "-o", str(out),
         f"-DADV=48'h{adv:012x}", f"-DFLOPS={1 if model == 'flops' else 0}", f"-DOTP={1 if model == 'otp' else 0}",
         str(work / "tb_tx_min.v"), *map(str, refs), *files],
        cwd=d, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"{name}: does not compile:\n{result.stdout}{result.stderr}")
    return out


def simulate(work: Path, vvp: Path, seed: int, clkb_half_ps: int, packets: int) -> tuple[str, str]:
    """One run: ('PASS'|'CAUGHT'|'ERROR', the verdict line)."""
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(vvp), f"+seed={seed}",
                             f"+clkb_half_ps={clkb_half_ps}", f"+packets={packets}"],
                            cwd=work, capture_output=True, text=True, timeout=3600)
    output = result.stdout + result.stderr
    lines = [l for l in output.splitlines() if l.startswith(("PASS", "MISMATCH", "ERROR"))]
    line = lines[0] if lines else output.strip()[-300:]
    if sim_pass(result.returncode, output, "PASS"):
        return "PASS", line
    if mutant_caught(result.returncode, output):
        return "CAUGHT", line
    return "ERROR", f"exit {result.returncode}: {line}"


def campaign(work: Path, name: str, texts: dict[str, str], refs: list[Path], advs: list[int], seeds: list[int],
             clocks: list[int], packets: int, jobs: int, stop_at_fail: bool) -> dict[str, int]:
    builds = {(m, a): build(work, f"{name}_{m}_{a:012x}", texts, m, a, refs) for m in MODELS for a in advs}
    runs = [(m, a, s, c) for s in seeds for c in clocks for a in advs for m in MODELS]
    counts = {"PASS": 0, "CAUGHT": 0, "ERROR": 0}

    def one(run):
        m, a, s, c = run
        return run, simulate(work, builds[(m, a)], s, c, packets)

    def show(run, verdict, line):
        m, a, s, c = run
        print(f"  {m:5} AdvA {a:012x} seed {s} clkb_half_ps {c}: {verdict}: {line}", flush=True)

    if stop_at_fail:
        for run in runs:
            run, (verdict, line) = one(run)
            counts[verdict] += 1
            show(run, verdict, line)
            if verdict != "PASS":
                break
        return counts
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for run, (verdict, line) in pool.map(one, runs):
            counts[verdict] += 1
            show(run, verdict, line)
    return counts


def main() -> None:
    global REF_REV
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=positive, default=3)
    parser.add_argument("--packets", type=positive, default=10)
    parser.add_argument("--jobs", type=positive, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--write-one-port", metavar="FILE",
                        help="write verilog/btle_tx.v with the AdvData memory on the one-port macro model "
                             "(model included) to FILE, for a system run, and stop")
    parser.add_argument("--ref-rev", default=REF_REV, help="corrected TX reference revision")
    args = parser.parse_args()
    REF_REV = args.ref_rev

    if args.write_one_port:
        text = pdu_one_port((ROOT / "verilog" / "btle_tx.v").read_text())
        Path(args.write_one_port).write_text(text + PDU_MACRO)
        print(f"wrote {args.write_one_port}")
        return
    if args.packets < 2:
        raise SystemExit("--packets must be at least 2 (the lengths 37 and 6 come first)")

    count = 2048
    cosine = [round(127 * math.cos(2 * math.pi * i / count)) for i in range(count)]
    sine = [round(127 * math.sin(2 * math.pi * i / count)) for i in range(count)]
    texts = {f: (ROOT / "verilog" / f).read_text() for f in DUT_FILES}
    advs = [PROJECT_ADV_ADDRESS, random.Random(20261016).getrandbits(48)]

    with tempfile.TemporaryDirectory(prefix="tx-min-") as directory:
        work = Path(directory)
        (work / "tb_tx_min.v").write_text(TB)
        for name, values in (("cos.hex", cosine), ("sin.hex", sine)):
            (work / name).write_text("".join(f"{v & 0xff:02x}\n" for v in values))
        (work / "taps.hex").write_text("".join(f"{v & 0xffff:04x}\n" for v in TAPS))
        refs = reference_files(work)

        seeds = list(range(1, args.seeds + 1))
        print(f"verilog/ against {REF_REV}: {len(seeds)} seeds x {len(CLKB_HALF_PS)} clkb x {len(MODELS)} AdvData "
              f"models x {len(advs)} AdvA, {args.packets} packets per run")
        counts = campaign(work, "dut", texts, refs, advs, seeds, CLKB_HALF_PS, args.packets, args.jobs, False)
        total = sum(counts.values())
        print(f"runs: {total}, pass {counts['PASS']}")
        if total == 0 or counts["PASS"] != total:
            raise SystemExit("FAIL")

        if args.mutants:
            caught = 0
            for index, (f, label, edits) in enumerate(MUTANTS, 1):
                mutated = dict(texts)
                for old, new in edits:
                    if old not in mutated[f]:
                        raise SystemExit(f"mutant {index}: text not found in {f}: {old!r}")
                    mutated[f] = mutated[f].replace(old, new)
                print(f"mutant {index} ({f}: {label}):")
                c = campaign(work, f"m{index}", mutated, refs, advs[1:], [1, 2], [0, 5000], 4, 1, True)
                if c["CAUGHT"] and not c["ERROR"]:
                    caught += 1
                else:
                    print("  NOT CAUGHT" if not c["ERROR"] else "  ERROR (no concrete mismatch)")
            print(f"mutants caught: {caught}/{len(MUTANTS)}")
            if caught != len(MUTANTS):
                raise SystemExit("FAIL")
        print("PASS")


if __name__ == "__main__":
    main()
