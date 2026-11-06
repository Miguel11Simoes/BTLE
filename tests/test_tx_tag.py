"""Check the tag transmitter of ble-tx-poc against ble-tx-tag-8's and ble-tx-tag-1byte's, clock by clock, with Icarus Verilog.

Author: Miguel Simões

Run from the repository root with IVERILOG and VVP in PATH (or set their
environment variables).

REF is the btle_tx of ble-tx-tag-8 for SENSOR_BYTES = 2, of ble-tx-tag-1byte for
SENSOR_BYTES = 1 (their revisions: --ref-rev-2, --ref-rev-1; every module renamed
*_ref), GAUSS_TABLE=1, on its (address, data) pair: only the sensor's bytes among
writes of random data to every other address (0..511), which it must ignore. Those
two are the tags validated against ble-tx-min and upstream's model
(docs/Senseworks/TX_TAG_COMPARISON.md). DUT is this branch's btle_tx with
GAUSS_TABLE=1, BCH_T = 8, 12 or 18 and SENSOR_BYTES = 1 or 2, on its direct ports:
AdvA, TxAdd and the sensor. Both have the same AdvA, TxAdd and Company ID. Every
output of btle_tx is compared on every clk clock from the first reset on (case
inequality, plus explicit rejection of unknown valid samples). The sensor's bytes
come from the PDUs of scripts/senseworks/tag_bch.py, whose length on the air the
DUT must also have (tests/test_tx_tag_packet.py checks its waveform against them).

The contract: the ports stable from tx_start to the end of the packet.

Stimulus (seeded, +seed=N), as tests/test_tx_min.py: packets with the sensor all 0s
and all 1s first, random after; random channel, access address, CRC init and
preamble; tx_start, sometimes held for several clocks; while sending, at random:
pairs to any address but the sensor's (REF), access-address and preamble changes,
CRC and channel loads, extra tx_start pulses, and resets of 1 to 3 clocks that
abort the packet. The campaign runs every seed with REF's clkb = clk and with clkb
free at 100, 33.3, 16.1, 10 and 8 MHz, for t = 8, 12 and 18 and both sizes, on two
DUT builds per AdvA: the port and the OTP (ADV_ADDRESS_OTP=1, the six eFuse blocks
on tests/efuse_async_mem_1x8_model.v, the port set to 0: the unprogrammed chip must
read 0, then AdvA is programmed once and sensed after a reset). AdvA: C1:02:03:04:05:06
with TxAdd = 1 and the default Company ID (0xFFFF), and a random static address
whose first bit sent is 1 with TxAdd = 0 and the Company ID 0x1A2B (so that a fault
on that bit, on TxAdd or on the Company ID's byte order shows).

  python3 tests/test_tx_tag.py [--seeds N] [--packets N] [--jobs N] [--mutants]

With --mutants, each deliberate fault must make a run fail with a concrete
mismatch.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/validation"))
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
from result_guard import sim_pass, mutant_caught, positive  # noqa: E402
import tag_bch  # noqa: E402

REF_FILES = ["btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v", "scramble_core.v",
             "gfsk_modulation.v", "bit_repeat_upsample.v", "gauss_filter.v", "vco.v"]
DUT_FILES = REF_FILES
CLKB_HALF_PS = [0, 5000, 15000, 31057, 50000, 62500]  # 0: clkb = clk; else 100, 33.3, 16.1, 10, 8 MHz
MODELS = ("port", "otp")
DEFAULT_ADV_ADDRESS = 0xC10203040506
# The default AdvA goes with the default Company ID (0xFFFF) and TxAdd = 1; the other AdvA (its first bit
# sent a 1, so that leaving that bit out of the code shows) with a Company ID whose two bytes differ (so
# that their order shows) and TxAdd = 0.
TEST_COMPANY_ID = 0x1A2B
SIZES = (1, 2)                                    # SENSOR_BYTES
REF_BRANCH = {1: "ble-tx-tag-1byte", 2: "ble-tx-tag-8"}
MAX_PACKETS = 64

TB = r"""
`timescale 1ns/1ps
module tb_tx_tag;
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
  localparam integer PDU_LEN = `PDU_LEN;          // 21 to 30 bytes
  localparam integer SB = `SB;                    // the bytes of sensor

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
  reg [8:0] r_pair_address = 0;
  reg [7:0] r_pair_data = 0;
  reg [8*SB-1:0] d_sensor = 0;
  reg tx_start = 0;

  `define TX_PORTS(p) \
    .clk(clk), .rst(rst), \
    .gauss_filter_tap_index(tap_index), .gauss_filter_tap_value(tap_value), \
    .cos_table_write_address(cos_address), .cos_table_write_data(cos_data), \
    .sin_table_write_address(sin_address), .sin_table_write_data(sin_data), \
    .preamble(preamble), .access_address(access_address), \
    .crc_state_init_bit(crc_init), .crc_state_init_bit_load(crc_load), \
    .channel_number(channel), .channel_number_load(channel_load), \
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
  wire r_otp_ready;
  btle_tx_ref #(.GAUSS_TABLE(1), .BCH_T(`BCH_T), .COMPANY_ID(`CID), .TX_ADD(`TXADD), .ADV_ADDRESS(ADV))
    ref_i (`TX_PORTS(r), .clkb(clkb), .pdu_octet_mem_data(r_pair_data), .pdu_octet_mem_addr(r_pair_address),
           .adv_address_otp_prog(48'd0), .adv_address_otp_ready(r_otp_ready));
  // OTP builds: AdvA from the eFuse blocks, programmed below; the port at 0 shows it is not used
  reg [47:0] otp_prog = 0;
  wire d_otp_ready;
  wire [47:0] d_adv_sent;
  btle_tx #(.GAUSS_TABLE(1), .BCH_T(`BCH_T), .COMPANY_ID(`CID), .SENSOR_BYTES(SB), .ADV_ADDRESS_OTP(`OTP))
    dut_i (`TX_PORTS(d), .adv_address(`OTP ? 48'h0 : ADV), .tx_add(`TXADD != 0), .sensor(d_sensor),
           .adv_address_otp_prog(otp_prog), .adv_address_otp_ready(d_otp_ready), .adv_address_sent(d_adv_sent));
  wire [43:0] r_out = {r_i, r_q, r_iqv, r_iqvl, r_pb, r_pbv, r_pbvl, r_bu, r_buv, r_buvl, r_g, r_gv, r_gvl};
  wire [43:0] d_out = {d_i, d_q, d_iqv, d_iqvl, d_pb, d_pbv, d_pbvl, d_bu, d_buv, d_buvl, d_g, d_gv, d_gvl};

  // the PDUs of tag_bch.py, PDU_LEN bytes each: packet p is pdus[p * PDU_LEN +: PDU_LEN]
  reg [7:0] pdus [0:`MAX_PACKETS * PDU_LEN - 1];
  initial $readmemh("pdus.hex", pdus);

  integer seed, seed0, n_packets, gap_max;
  integer checked = 0, iq_samples = 0, iq_nonzero = 0, resets = 0, packets_started = 0, packets_sent = 0;
  integer pair_writes_sending = 0, aa_changes = 0, loads = 0, extra_starts = 0, ref_garbage = 0;
  integer p, n, k, a, clocks, aborted, phy_bits;
  reg compare_on = 0;
  reg sending = 0;

  function integer urand(input integer range);
    urand = $unsigned($random(seed)) % range;
  endfunction

  function integer not_sensor_address(input integer dummy);  // any of 0..511 but the sensor's
    integer x;
    begin
      x = urand(512 - SB);
      not_sensor_address = (x >= 12) ? x + SB : x;
    end
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

  // while a packet is sent: REF, pairs to any address but the sensor's; the DUT's ports stay
  always @(posedge clkb) begin
    if (sending && urand(16) == 0) begin
      r_pair_address <= not_sensor_address(0);
      r_pair_data <= $random(seed);
      pair_writes_sending = pair_writes_sending + 1;
    end
  end

  task write_ref(input integer address, input integer data);
    begin
      @(posedge clkb);
      r_pair_address <= address;
      r_pair_data <= data;
      repeat (urand(gap_max + 1)) @(posedge clkb);
    end
  endtask

  task load_taps;  // GAUSS_TABLE=1 does not use them; written as the upstream testbench does
    begin
      for (k = 0; k < 9; k = k + 1) begin
        @(posedge clk); tap_index <= k; tap_value <= 0;
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
    if (n_packets < 2 || n_packets > `MAX_PACKETS) begin $display("ERROR: 2..%0d packets", `MAX_PACKETS); $fatal(1, "bad arguments"); end
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
    for (p = 0; p < n_packets; p = p + 1) begin
      // REF: random data to every other address, around the sensor's bytes, sometimes written twice;
      // DUT: its port changes with them (the contract asks for it stable only from tx_start on)
      for (n = urand(24) + 8; n > 0; n = n - 1) begin
        write_ref(not_sensor_address(0), $random(seed));
        ref_garbage = ref_garbage + 1;
      end
      if (urand(2)) begin
        for (n = 0; n < SB; n = n + 1) write_ref(12 + n, $random(seed));
        @(posedge clk); d_sensor <= $random(seed);
      end
      for (n = 0; n < SB; n = n + 1) begin
        write_ref(12 + n, pdus[p * PDU_LEN + 12 + n]);
        for (k = urand(8); k > 0; k = k - 1) begin
          write_ref(not_sensor_address(0), $random(seed));
          ref_garbage = ref_garbage + 1;
        end
      end
      @(posedge clk);
      for (n = 0; n < SB; n = n + 1) d_sensor[8*n +: 8] <= pdus[p * PDU_LEN + 12 + n];
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

    // the length on the air, DUT alone: 40 + PDU_LEN * 8 + 24 PHY bits, then IDLE
    compare_on <= 0;
    start_packet;
    phy_bits = 0;
    clocks = 0;
    while (!d_iqvl) begin
      @(posedge clk);
      if (d_pbv) phy_bits = phy_bits + 1;
      clocks = clocks + 1;
      if (clocks > 400000) begin $display("ERROR: the last packet never ended"); $fatal(1, "testbench"); end
    end
    repeat (4) @(posedge clk);
    if (phy_bits != 40 + PDU_LEN * 8 + 24 || dut_i.phy_tx_state != 0) begin
      $display("MISMATCH packet length: %0d PHY bits, expected %0d; state %0d", phy_bits, 40 + PDU_LEN * 8 + 24, dut_i.phy_tx_state);
      $fatal(1, "length");
    end
    if (d_adv_sent !== ADV) begin
      $display("MISMATCH adv_address_sent %h, expected %h", d_adv_sent, ADV);
      $fatal(1, "adv_address_sent");
    end

    $display("PASS seed %0d clkb_half_ps %0d: %0d clocks compared, %0d packets sent (%0d started), %0d resets, %0d IQ samples (%0d non-zero), %0d pairs written while sending, %0d REF writes to other addresses, %0d access-address changes, %0d CRC/channel loads, %0d extra tx_start; %0d PHY bits per packet",
             seed0, clkb_half_ps, checked, packets_sent, packets_started, resets, iq_samples, iq_nonzero,
             pair_writes_sending, ref_garbage, aa_changes, loads, extra_starts, phy_bits);
    $finish;
  end
endmodule
"""

# Each fault must be caught for t = 8 and one byte of sensor (the mutants run there); the generator mutants pick
# their t, and the mutants of the second byte run with two bytes (TWO_BYTE_MUTANTS).
MUTANTS = [
    ("btle_tx.v", "a message bit does not enter the LFSR",
     [("({BCH_DEG{bch_lfsr[BCH_DEG-1] ^ octet[0]}} & BCH_G)", "({BCH_DEG{bch_lfsr[BCH_DEG-1]}} & BCH_G)")]),
    ("btle_tx.v", "the parity starts one bit late",
     [("localparam integer PARITY_FIRST_BIT_INDEX = 96 + 8 * SENSOR_BYTES;", "localparam integer PARITY_FIRST_BIT_INDEX = 97 + 8 * SENSOR_BYTES;")]),
    ("btle_tx.v", "the sensor's last byte left out of the message",
     [("((bit_count >= SENSOR_FIRST_BIT) && (bit_count < PARITY_FIRST_BIT))",
       "((bit_count >= SENSOR_FIRST_BIT) && (bit_count < PARITY_FIRST_BIT - 8))")]),
    ("btle_tx.v", "AdvA's first bit left out of the message",
     [("ADVA_FIRST_BIT = 16, ADVA_END_BIT = 64,", "ADVA_FIRST_BIT = 17, ADVA_END_BIT = 64,")]),
    ("btle_tx.v", "one coefficient of g(x) wrong (t = 8)",
     [("64'h6ce707e26b6f9977", "64'h6ce707e26b6f9976")]),
    ("btle_tx.v", "the parity sent lowest coefficient first",
     [("info_bit <= bch_parity_bit ? bch_lfsr[BCH_DEG-1] : octet[0];", "info_bit <= bch_parity_bit ? bch_lfsr[0] : octet[0];")]),
    ("btle_tx.v", "the LFSR never cleared between packets",
     [("  if (phy_tx_state != TX_PDU) begin\n    bch_lfsr <= 0;", "  if (1'b0) begin\n    bch_lfsr <= 0;")]),
    ("btle_tx.v", "the AD structure's length one short",
     [("localparam integer AD_STRUCTURE_LENGTH = 3 + SENSOR_BYTES + PARITY_BYTES;", "localparam integer AD_STRUCTURE_LENGTH = 2 + SENSOR_BYTES + PARITY_BYTES;")]),
    ("btle_tx.v", "the header's length one long",
     [("localparam [7:0] HEADER1 = PAYLOAD_LENGTH[7:0];", "localparam [7:0] HEADER1 = PAYLOAD_LENGTH[7:0] + 8'd1;")]),
    ("btle_tx.v", "the Company ID's bytes swapped",
     [("5'd10:   read_data = COMPANY_ID[7:0];", "5'd10:   read_data = COMPANY_ID[15:8];")]),
    ("btle_tx.v", "the sensor's second byte a copy of the first",
     [("assign sensor_d1 = sensor[15:8];", "assign sensor_d1 = sensor[7:0];")]),
    ("btle_tx.v", "the sensor's first byte not at PDU byte 12",
     [("5'd12:   read_data = sensor[7:0];", "5'd13:   read_data = sensor[7:0];")]),
    ("btle_tx.v", "the TxAdd bit in RxAdd's place",
     [("wire [7:0] header0 = {1'b0, tx_add, 2'b00, 4'b0010};", "wire [7:0] header0 = {tx_add, 1'b0, 2'b00, 4'b0010};")]),
    ("btle_tx.v", "the port tx_add ignored",
     [("wire [7:0] header0 = {1'b0, tx_add, 2'b00, 4'b0010};", "wire [7:0] header0 = {1'b0, 1'b1, 2'b00, 4'b0010};")]),
    ("btle_tx.v", "the last bit one byte early",
     [("localparam integer LAST_PDU_BIT_INDEX = (PAYLOAD_LENGTH + 2) * 8 - 1;",
       "localparam integer LAST_PDU_BIT_INDEX = (PAYLOAD_LENGTH + 1) * 8 - 1;")]),
    ("btle_tx.v", "the byte read one address late",
     [(".read_address(addr),", ".read_address(addr + 5'd1),")]),
    ("btle_tx.v", "AdvA byte 2 taken from the most significant byte",
     [("5'd2:    read_data = adv_address[7:0];", "5'd2:    read_data = adv_address[47:40];")]),
    ("btle_tx.v", "the OTP bytes in the wrong order",
     [(".out(adv_address[8*b +: 8]),", ".out(adv_address[8*(5-b) +: 8]),")]),
    ("btle_tx.v", "the OTP never sensed (reset_n held high)",
     [(".reset_n(~rst),", ".reset_n(1'b1),")]),
    ("crc24.v", "the CRC bits sent in the wrong order",
     [("lfsr[~bit_count[4:0]]", "lfsr[bit_count[4:0] - 5'd8]")]),
    ("scramble.v", "the whitening starts one bit late",
     [("end else if (data_in_valid && data_in_count != 41) begin",
       "end else if (data_in_valid && data_in_count != 40) begin")]),
]
# mutants that only show in the OTP build
OTP_MUTANTS = {"the OTP bytes in the wrong order", "the OTP never sensed (reset_n held high)"}
# mutants that only show with two bytes of sensor
TWO_BYTE_MUTANTS = {"the sensor's second byte a copy of the first"}
# the generator mutants of t = 12 and 18 run on their own t
GENERATOR_MUTANTS = [
    (12, "one coefficient of g(x) wrong (t = 12)", "92'he810da40f70569be7529981", "92'he810da40f70569be7529983"),
    (18, "one coefficient of g(x) wrong (t = 18)", "124'h1bcb6cce6906958aa17f2231050eb39", "124'h1bcb6cce6906958aa17f2231050eb38"),
]


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def reference_files(work: Path, rev: str, sensor_bytes: int) -> list[Path]:
    texts = {f: git("show", f"{rev}:verilog/{f}") for f in REF_FILES}
    names = sorted({m for t in texts.values() for m in re.findall(r"^\s*module\s+(\w+)", t, re.M)})
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b")
    paths = []
    for f, t in texts.items():
        path = work / f"ref{sensor_bytes}_{f}"
        path.write_text(pattern.sub(lambda m: m.group(1) + "_ref", t))
        paths.append(path)
    return paths


def company_id(adv: int) -> int:
    return tag_bch.DEFAULT_COMPANY_ID if adv == DEFAULT_ADV_ADDRESS else TEST_COMPANY_ID


def tx_add_of(adv: int) -> int:
    return 1 if adv == DEFAULT_ADV_ADDRESS else 0


def pdus_hex(t: int, s: int, adv: int, seed: int) -> str:
    """The PDUs of a run: the sensor all 0s and all 1s first, then random (the same for every build)."""
    rng = random.Random(100000 * s + 1000 * t + seed)
    lines = []
    for p in range(MAX_PACKETS):
        sensor = bytes(s) if p == 0 else bytes([0xff] * s) if p == 1 else rng.randbytes(s)
        lines += [f"{b:02x}" for b in tag_bch.tag_pdu(adv, sensor, t, company_id(adv), tx_add_of(adv))]
    return "\n".join(lines) + "\n"


def build(work: Path, name: str, texts: dict[str, str], model: str, adv: int, t: int, s: int, refs: list[Path]) -> Path:
    d = work / name
    d.mkdir()
    files = []
    for f, text in texts.items():
        (d / f).write_text(text)
        files.append(str(d / f))
    if model == "otp":
        files.append(str(ROOT / "tests" / "efuse_async_mem_1x8_model.v"))
    out = d / "tb.vvp"
    pdu_len = 2 + tag_bch.payload_length(t, s)
    result = subprocess.run(
        [os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tb_tx_tag", "-o", str(out),
         f"-DADV=48'h{adv:012x}", f"-DCID=16'h{company_id(adv):04x}", f"-DOTP={1 if model == 'otp' else 0}", f"-DBCH_T={t}",
         f"-DSB={s}", f"-DTXADD={tx_add_of(adv)}", f"-DPDU_LEN={pdu_len}", f"-DMAX_PACKETS={MAX_PACKETS}",
         str(work / "tb_tx_tag.v"), *map(str, refs), *files],
        cwd=d, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"{name}: does not compile:\n{result.stdout}{result.stderr}")
    return out


def simulate(work: Path, vvp: Path, t: int, s: int, adv: int, seed: int, clkb_half_ps: int, packets: int) -> tuple[str, str]:
    """One run: ('PASS'|'CAUGHT'|'ERROR', the verdict line)."""
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=work))
    (run_dir / "pdus.hex").write_text(pdus_hex(t, s, adv, seed))
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(vvp), f"+seed={seed}",
                             f"+clkb_half_ps={clkb_half_ps}", f"+packets={packets}"],
                            cwd=run_dir, capture_output=True, text=True, timeout=3600)
    output = result.stdout + result.stderr
    lines = [l for l in output.splitlines() if l.startswith(("PASS", "MISMATCH", "ERROR"))]
    line = lines[0] if lines else output.strip()[-300:]
    if sim_pass(result.returncode, output, "PASS"):
        return "PASS", line
    if mutant_caught(result.returncode, output):
        return "CAUGHT", line
    return "ERROR", f"exit {result.returncode}: {line}"


def campaign(work: Path, name: str, texts: dict[str, str], refs: dict[int, list[Path]], sizes: tuple[int, ...],
             ts: list[int], models: tuple[str, ...], advs: list[int], seeds: list[int], clocks: list[int],
             packets: int, jobs: int, stop_at_fail: bool) -> dict[str, int]:
    builds = {(b, t, m, a): build(work, f"{name}_s{b}_t{t}_{m}_{a:012x}", texts, m, a, t, b, refs[b])
              for b in sizes for t in ts for m in models for a in advs}
    runs = [(b, t, m, a, s, c) for b in sizes for t in ts for s in seeds for c in clocks for a in advs for m in models]
    counts = {"PASS": 0, "CAUGHT": 0, "ERROR": 0}

    def one(run):
        b, t, m, a, s, c = run
        return run, simulate(work, builds[(b, t, m, a)], t, b, a, s, c, packets)

    def show(run, verdict, line):
        b, t, m, a, s, c = run
        print(f"  S {b} t {t:2} {m:4} AdvA {a:012x} seed {s} clkb_half_ps {c}: {verdict}: {line}", flush=True)

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
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=positive, default=3)
    parser.add_argument("--packets", type=positive, default=10)
    parser.add_argument("--jobs", type=positive, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--ref-rev-1", default="7fb89713", help="ble-tx-tag-1byte's revision")
    parser.add_argument("--ref-rev-2", default="86a194a6", help="ble-tx-tag-8's revision")
    args = parser.parse_args()
    if not 2 <= args.packets <= MAX_PACKETS:
        raise SystemExit(f"--packets must be 2..{MAX_PACKETS}")
    ref_revs = {1: git("rev-parse", f"{args.ref_rev_1}^{{commit}}").strip(),
                2: git("rev-parse", f"{args.ref_rev_2}^{{commit}}").strip()}

    texts = {f: (ROOT / "verilog" / f).read_text() for f in DUT_FILES}
    rng = random.Random(20261104)
    advs = [DEFAULT_ADV_ADDRESS, (0b11 << 46) | rng.getrandbits(46) | 1]   # both random static
    ts = list(tag_bch.TS)

    with tempfile.TemporaryDirectory(prefix="tx-tag-") as directory:
        work = Path(directory)
        (work / "tb_tx_tag.v").write_text(TB)
        refs = {s: reference_files(work, ref_revs[s], s) for s in SIZES}

        seeds = list(range(1, args.seeds + 1))
        for s in SIZES:
            print(f"verilog/ with SENSOR_BYTES = {s} against {REF_BRANCH[s]} {ref_revs[s]}")
        print(f"sizes {list(SIZES)} x t {ts} x {len(seeds)} seeds x {len(CLKB_HALF_PS)} clkb x "
              f"{len(MODELS)} AdvA stores x {len(advs)} AdvA, {args.packets} packets per run")
        counts = campaign(work, "dut", texts, refs, SIZES, ts, MODELS, advs, seeds, CLKB_HALF_PS, args.packets,
                          args.jobs, False)
        total = sum(counts.values())
        print(f"runs: {total}, pass {counts['PASS']}")
        if total == 0 or counts["PASS"] != total:
            raise SystemExit("FAIL")

        if args.mutants:
            mutants = [(f, label, edits, 8) for f, label, edits in MUTANTS]
            mutants += [("btle_tx.v", label, [(old, new)], t) for t, label, old, new in GENERATOR_MUTANTS]
            caught = 0
            for index, (f, label, edits, t) in enumerate(mutants, 1):
                mutated = dict(texts)
                for old, new in edits:
                    if mutated[f].count(old) != 1:
                        raise SystemExit(f"mutant {index}: text not found once in {f}: {old!r}")
                    mutated[f] = mutated[f].replace(old, new)
                print(f"mutant {index} ({f}: {label}):")
                models = ("otp",) if label in OTP_MUTANTS else ("port",)
                sizes = (2,) if label in TWO_BYTE_MUTANTS else (1,)
                c = campaign(work, f"m{index}", mutated, refs, sizes, [t], models, advs, [1, 2], [0, 5000], 4, 1, True)
                if c["CAUGHT"] and not c["ERROR"]:
                    caught += 1
                else:
                    print("  NOT CAUGHT" if not c["ERROR"] else "  ERROR (no concrete mismatch)")
            print(f"mutants caught: {caught}/{len(mutants)}")
            if caught != len(mutants):
                raise SystemExit("FAIL")
        print("PASS")


if __name__ == "__main__":
    main()
