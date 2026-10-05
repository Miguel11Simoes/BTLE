"""Check the transmitter of ble-tx-pdu against upstream's, clock by clock, with Icarus Verilog.

Author: Miguel Simões

Run from the repository root with IVERILOG and VVP in PATH (or set their
environment variables). Needs the corrected reference commit recorded in REF_REV.

REF is the corrected master btle_tx (override with --ref-rev; every module renamed
*_ref): the runtime Gaussian FIR, loaded with the project's taps, the VCO with
the full COS and SIN tables, and the packet buffer in a memory with two ports.
DUT is this branch's btle_tx with GAUSS_TABLE=1: the constant taps, the quarter
sine table in a memory with one port, the packet buffer in a memory of 256
bytes with one port on clkb plus a register for byte 256, and the rewritten
counters (bit_repeat_upsample, crc24, scramble, btle_tx). Every output of
btle_tx is compared on every clk clock from the first reset on (case inequality, plus explicit rejection of unknown valid samples).

Stimulus (seeded, +seed=N): the taps and both tables are written as the
upstream TX testbench writes them (cosine and sine at the same address on every
clock), the taps again after every reset (upstream's FIR loses them); then
packets: lengths 255 (byte 256 is sent) and 0 first, random after; each packet
written through the (address, data) pair on clkb, one pair per clkb clock with
random gaps, after pairs to the addresses the packet does not use (up to 511)
and, half of the time, after a first random version of its bytes; random
channel, access address, CRC init and preamble; tx_start, sometimes held for
several clocks; while sending, at random: pairs written to addresses outside
the packet, access-address and preamble changes, CRC and channel loads, table
entries rewritten (with the same values), extra tx_start pulses, and resets of
1 to 3 clocks that abort the packet. Never: a packet byte rewritten while the
packet is being sent (the one case in which the buffer may differ, see
verilog/btle_tx.v).

The campaign runs every seed with clkb = clk and with clkb free at 100, 33.3,
16.1, 10 and 8 MHz, each with the repository's RAM model (verilog/ as it is)
and with one-port macro models of both memories (one address; the output
changes only in a clock that reads; an ERROR line if a clock both writes and
reads).

  python3 tests/test_tx_pdu.py [--seeds N] [--packets N] [--jobs N] [--mutants]
  python3 tests/test_tx_pdu.py --write-one-port FILE

With --mutants, each of 11 deliberate faults must make a run fail with a
concrete mismatch. --write-one-port writes verilog/btle_tx.v with the packet
buffer on the one-port macro model (model included), to run whole-system
testbenches on it (tests/test_vco_sin2.py --write-one-port does the same for
verilog/vco.v).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/validation"))
sys.path.insert(0, str(ROOT / "tests"))
from result_guard import sim_pass, mutant_caught, positive
from test_vco_sin2 import MACRO as VCO_MACRO, one_port as vco_one_port

REF_REV = "6589489b71704d0ff5d8eae499a6522ade0ac680"
TX_FILES = ["btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v", "scramble_core.v",
            "gfsk_modulation.v", "bit_repeat_upsample.v", "gauss_filter.v", "vco.v",
            "sdpram_one_clk.v", "sdpram_two_clk.v"]
DUT_FILES = [f for f in TX_FILES if f != "sdpram_two_clk.v"]
TAPS = [0, 0, 0, 1, 4, 9, 15, 22, 24]  # taps 0..8 of python/btlelib.py (BT = 0.5, 8 samples/symbol)
CLKB_HALF_PS = [0, 5000, 15000, 31057, 50000, 62500]  # 0: clkb = clk; else 100, 33.3, 16.1, 10, 8 MHz

# The one-port macro of the packet buffer: one address (the write address in a
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
module tb_tx_pdu;
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
  btle_tx #(.GAUSS_TABLE(1)) dut_i (`TX_PORTS(d));
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
  integer p, n, k, len, clocks, aborted;
  integer packet_end = 0;
  reg compare_on = 0;
  reg sending = 0;

  function integer urand(input integer range);
    urand = $unsigned($random(seed)) % range;
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
    for (k = 0; k < 2048; k = k + 1) begin         // as the upstream TX testbench: one entry per clock
      @(posedge clk);
      cos_address <= k; cos_data <= cos_t[k];
      sin_address <= k; sin_data <= sin_t[k];
    end
    for (p = 0; p < n_packets; p = p + 1) begin
      len = (p == 0) ? 255 : (p == 1) ? 0 : urand(256);
      packet_end = len + 2;
      for (n = urand(12) + 4; n > 0; n = n - 1)
        write_pair(packet_end + urand(512 - packet_end), $random(seed));
      if (urand(2))
        for (n = 0; n < packet_end; n = n + 1 + urand(4)) write_pair(n, $random(seed));
      for (n = 0; n < packet_end; n = n + 1)
        write_pair(n, (n == 1) ? len : $random(seed));
      if (urand(2)) write_pair(packet_end + urand(512 - packet_end), $random(seed));
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
    if (packets_sent >= 2 && iq_nonzero > 0 && checked > 0) begin
      $display("PASS seed %0d clkb_half_ps %0d: %0d clocks compared, %0d packets sent (%0d started), %0d resets, %0d IQ samples (%0d non-zero), %0d pairs written while sending, %0d access-address changes, %0d CRC/channel loads, %0d table rewrites, %0d extra tx_start",
               seed0, clkb_half_ps, checked, packets_sent, packets_started, resets, iq_samples, iq_nonzero,
               pair_writes_sending, aa_changes, loads, table_rewrites, extra_starts);
      $finish;
    end
    $display("ERROR: campaign too small: %0d packets sent, %0d non-zero samples", packets_sent, iq_nonzero);
    $fatal(1, "testbench");
  end
endmodule
"""

MUTANTS = [
    ("btle_tx.v", "the byte is asked at [clk_count] 113, before its address is set",
     [("localparam [3:0] PDU_READ_CLOCK = 4;", "localparam [3:0] PDU_READ_CLOCK = 1;")]),
    ("btle_tx.v", "byte 256 is not taken from its register",
     [("if (read && read_top) begin", "if (1'b0) begin")]),
    ("btle_tx.v", "the pair is written in the clock that reads too",
     [("wire ram_write = !read && !write_address[ADDRESS_WIDTH-1];",
       "wire ram_write = !write_address[ADDRESS_WIDTH-1];")]),
    ("btle_tx.v", "payload_length taken from the wrong byte",
     [("if (bit_count == 8 && clk_count == 1) begin", "if (bit_count == 16 && clk_count == 1) begin")]),
    ("btle_tx.v", "octet loaded one bit period late",
     [("if (clk_count == 0 && bit_count[2:0] == 0) begin // speed 1/8M",
       "if (clk_count == 0 && bit_count[2:0] == 1) begin // speed 1/8M")]),
    ("bit_repeat_upsample.v", "the last marker occurs one repeat early",
     [("saved_last && (remaining == 1)", "saved_last && (remaining == 2)")]),
    ("crc24.v", "the CRC bits sent in the wrong order",
     [("lfsr[~bit_count[4:0]]", "lfsr[bit_count[4:0] - 5'd8]")]),
    ("crc24.v", "the CRC skips 39 bits, not 40",
     [("if (info_bit_valid && bit_count != 40) begin", "if (info_bit_valid && bit_count != 39) begin")]),
    ("scramble.v", "the whitening starts one bit late",
     [("end else if (data_in_valid && data_in_count != 41) begin",
       "end else if (data_in_valid && data_in_count != 40) begin")]),
    ("gauss_filter.v", "a tap paired with the wrong position",
     [("table_tap(e) * ({1'b0, w[e]} + {1'b0, w[16-e]})", "table_tap(e) * ({1'b0, w[e]} + {1'b0, w[15-e]})")]),
    ("gauss_filter.v", "the sum of the taps added instead of subtracted",
     [("assign table_sum = (half_sum <<< 1) - tap_total(0);", "assign table_sum = (half_sum <<< 1) + tap_total(0);")]),
]


def git_show(rev: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"cannot read {path} from {rev}")
    return result.stdout


def pdu_one_port(btle_tx_text: str) -> str:
    """verilog/btle_tx.v with the packet buffer on the one-port macro model (not included)."""
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


def build(work: Path, name: str, texts: dict[str, str], macros: bool, refs: list[Path]) -> Path:
    d = work / name
    d.mkdir()
    files = []
    for f, t in texts.items():
        if macros and f == "btle_tx.v":
            t = pdu_one_port(t)
        if macros and f == "vco.v":
            t = vco_one_port(t)
        (d / f).write_text(t)
        files.append(str(d / f))
    if macros:
        (d / "macros.v").write_text(PDU_MACRO + VCO_MACRO)
        files.append(str(d / "macros.v"))
    out = d / "tb.vvp"
    result = subprocess.run(
        [os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tb_tx_pdu", "-o", str(out),
         str(work / "tb_tx_pdu.v"), *map(str, refs), *files],
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


def campaign(work: Path, name: str, texts: dict[str, str], refs: list[Path], seeds: list[int],
             clocks: list[int], packets: int, jobs: int, stop_at_fail: bool) -> dict[str, int]:
    builds = {m: build(work, f"{name}_{'macro' if m else 'ram'}", texts, m, refs) for m in (False, True)}
    runs = [(m, s, c) for s in seeds for c in clocks for m in (False, True)]
    counts = {"PASS": 0, "CAUGHT": 0, "ERROR": 0}

    def one(run):
        m, s, c = run
        return run, simulate(work, builds[m], s, c, packets)

    if stop_at_fail:
        for run in runs:
            (m, s, c), (verdict, line) = one(run)
            counts[verdict] += 1
            print(f"  {'macro' if m else 'ram  '} seed {s} clkb_half_ps {c}: {verdict}: {line}")
            if verdict != "PASS":
                break
        return counts
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for (m, s, c), (verdict, line) in pool.map(one, runs):
            counts[verdict] += 1
            print(f"  {'macro' if m else 'ram  '} seed {s} clkb_half_ps {c}: {verdict}: {line}", flush=True)
    return counts


def main() -> None:
    global REF_REV
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=positive, default=3)
    parser.add_argument("--packets", type=positive, default=10)
    parser.add_argument("--jobs", type=positive, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--write-one-port", metavar="FILE",
                        help="write verilog/btle_tx.v with the packet buffer on the one-port macro model "
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
        raise SystemExit("--packets must be at least 2 (the lengths 255 and 0 come first)")

    count = 2048
    cosine = [round(127 * math.cos(2 * math.pi * i / count)) for i in range(count)]
    sine = [round(127 * math.sin(2 * math.pi * i / count)) for i in range(count)]
    texts = {f: (ROOT / "verilog" / f).read_text() for f in DUT_FILES}

    with tempfile.TemporaryDirectory(prefix="tx-pdu-") as directory:
        work = Path(directory)
        (work / "tb_tx_pdu.v").write_text(TB)
        for name, values in (("cos.hex", cosine), ("sin.hex", sine)):
            (work / name).write_text("".join(f"{v & 0xff:02x}\n" for v in values))
        (work / "taps.hex").write_text("".join(f"{v & 0xffff:04x}\n" for v in TAPS))
        refs = reference_files(work)

        seeds = list(range(1, args.seeds + 1))
        print(f"verilog/ against {REF_REV}: {len(seeds)} seeds x {len(CLKB_HALF_PS)} clkb x 2 memory models, "
              f"{args.packets} packets per run")
        counts = campaign(work, "dut", texts, refs, seeds, CLKB_HALF_PS, args.packets, args.jobs, False)
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
                c = campaign(work, f"m{index}", mutated, refs, [1, 2], [0, 5000], 4, 1, True)
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
