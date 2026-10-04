"""Check the VCO of ble-tx-pdu (the quarter sine table alone, one port) with Icarus Verilog.

Author: Miguel Simões

The VCO of ble-tx-sin2 without its change detector: the held sine pair is
rewritten in every clock the port is free, instead of when it changes. This
file is tests/test_vco_sin2.py of ble-tx-sin2 with three mutants replaced (the
three that removed parts of the detector).

Run from the repository root with IVERILOG and VVP in PATH (or set their
environment variables). Needs the master and ble-tx-sin4 branches, local or as
origin/<name>.

The VCO of this branch takes at most one sample every two clocks, never in the
clock right after a sample or a reset (the TX gives one every two clocks); the
testbenches keep to that. Every testbench simulates the VCO twice: with the
repository's RAM model (verilog/vco.v as it is) and with a one-port macro model,
which has one address (the write address in a clock with a write, the read
address otherwise) and keeps its output in a clock with a write. The two must
give the same outputs on every clock.

  sweep   against the master VCO: both full tables written, cosine and sine at
          the same address on every clock, as the upstream TX testbench does;
          then every phase address, one sample every two clocks; then signed
          jumps, gaps and a reset. Every clock is compared.
  random  clock-by-clock lockstep against the ble-tx-sin4 VCO, which keeps the
          quarter cosine and sine tables in two memories written on every
          clock. Its tables are kept consistent with this branch's single one:
          each sine write sin[k] = v (k = 1..511) also writes cos[512 - k] = v
          into the sin4 VCO, in the same clock; cos[0] is written to both.
          Random sine writes (a new value at the same address, entries a and b
          of the phase shown, any first-quarter address, addresses outside the
          first quarter), writes of cos[0], cosine writes that this branch
          ignores (other addresses), resets of 1..3 clocks; in stretches samples
          come on random clocks, every other clock (as when transmitting), or
          not at all. The stimulus keeps the contract of the port (the sine pair
          does not change again before it is written) and tracks,
          independently of the design, the clocks in which a write waits; the
          outputs are compared on every clock in which none does, resets
          included. Samples are aimed at entries just written, once they are in
          the memory; valid/last are compared on every clock; every 20 000
          clocks all 512 entries are read back.

  python3 tests/test_vco_sin2.py [--seeds N] [--clocks N] [--mutants]
  python3 tests/test_vco_sin2.py --write-one-port FILE

With --mutants, each of 11 deliberate faults of verilog/vco.v must make a
testbench fail. --write-one-port writes verilog/vco.v with its memory on the
one-port macro model, to run whole-system testbenches on it.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import subprocess
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/validation"))
from result_guard import sim_pass, mutant_caught, positive

DUT_PORTS = """
    .clk(clk), .rst(rst),
    .cos_table_write_address(cos_table_write_address),
    .cos_table_write_data(cos_table_write_data),
    .sin_table_write_address(sin_table_write_address),
    .sin_table_write_data(sin_table_write_data),
    .voltage_signal(voltage_signal),
    .voltage_signal_valid(voltage_signal_valid),
    .voltage_signal_valid_last(voltage_signal_valid_last),
"""

# the DUT with the repository's RAM model, the DUT with the one-port macro
# model, and their comparison on every clock
DUTS = r"""
  wire signed [7:0] cos_dut, sin_dut, cos_mac, sin_mac;
  wire valid_dut, last_dut, valid_mac, last_mac;
  vco dut (DUT_PORTS
    .cos_out(cos_dut), .sin_out(sin_dut),
    .sin_cos_out_valid(valid_dut), .sin_cos_out_valid_last(last_dut));
  vco_macro dut_macro (DUT_PORTS
    .cos_out(cos_mac), .sin_out(sin_mac),
    .sin_cos_out_valid(valid_mac), .sin_cos_out_valid_last(last_mac));

  task check_macro(input integer at);
    begin
      if (cos_dut !== cos_mac || sin_dut !== sin_mac ||
          valid_dut !== valid_mac || last_dut !== last_mac) begin
        $display("FAIL macro at clock %0d: RAM model I/Q=%0d/%0d valid/last=%b/%b; one-port macro I/Q=%0d/%0d valid/last=%b/%b",
                 at, cos_dut, sin_dut, valid_dut, last_dut, cos_mac, sin_mac, valid_mac, last_mac);
        $fatal(1);
      end
    end
  endtask
""".replace("DUT_PORTS", DUT_PORTS)

# The one-port macro: one address, and an output that changes only in a clock
# without a write (then it reads).
MACRO = r"""
`timescale 1ns/1ps
module sin_table_macro #
(
  parameter integer DATA_WIDTH = 8,
  parameter integer ADDRESS_WIDTH = 9
) (
  input wire clk,
  input wire rst,
  input wire [ADDRESS_WIDTH-1:0] write_address,
  input wire [DATA_WIDTH-1:0] write_data,
  input wire write_enable,
  input wire [ADDRESS_WIDTH-1:0] read_address,
  output reg [DATA_WIDTH-1:0] read_data
);
  reg [DATA_WIDTH-1:0] memory [0:(1<<ADDRESS_WIDTH)-1];
  wire [ADDRESS_WIDTH-1:0] address = write_enable ? write_address : read_address;
  always @(posedge clk) begin
    if (write_enable) memory[address] <= write_data;
    else read_data <= memory[address];
  end
endmodule
"""

SWEEP_TB = r"""
`timescale 1ns/1ps
module vco_sin2_sweep_tb;
  reg clk = 0;
  always #5 clk = ~clk;
  reg rst = 1;
  reg [10:0] cos_table_write_address = 0;
  reg signed [7:0] cos_table_write_data = 0;
  reg [10:0] sin_table_write_address = 0;
  reg signed [7:0] sin_table_write_data = 0;
  reg signed [15:0] voltage_signal = 0;
  reg voltage_signal_valid = 0;
  reg voltage_signal_valid_last = 0;
  wire signed [7:0] cos_ref, sin_ref;
  wire valid_ref, last_ref;
  reg signed [7:0] cos_table [0:2047];
  reg signed [7:0] sin_table [0:2047];
  integer i;
  integer clocks = 0;
  integer checked = 0;

DUTS
  vco_reference ref_vco (DUT_PORTS
    .cos_out(cos_ref), .sin_out(sin_ref),
    .sin_cos_out_valid(valid_ref), .sin_cos_out_valid_last(last_ref));

  // the RAM model and the macro agree on every clock, from the end of the reset
  always @(negedge clk) begin
    clocks = clocks + 1;
    if (clocks > 2) check_macro(clocks);
  end

  task check;
    begin
      if (cos_dut !== cos_ref || sin_dut !== sin_ref ||
          valid_dut !== valid_ref || last_dut !== last_ref) begin
        $display("FAIL sweep at check %0d: DUT I/Q=%0d/%0d valid/last=%b/%b; master I/Q=%0d/%0d valid/last=%b/%b",
                 checked, cos_dut, sin_dut, valid_dut, last_dut,
                 cos_ref, sin_ref, valid_ref, last_ref);
        $fatal(1);
      end
      checked = checked + 1;
    end
  endtask

  initial begin
    $readmemh("cos.hex", cos_table);
    $readmemh("sin.hex", sin_table);
    repeat (2) @(negedge clk);
    rst = 0;
    for (i = 0; i < 2048; i = i + 1) begin
      @(negedge clk);
      cos_table_write_address = i;
      cos_table_write_data = cos_table[i];
      sin_table_write_address = i;
      sin_table_write_data = sin_table[i];
    end
    @(negedge clk);
    // every phase address: one sample every two clocks
    for (i = 0; i < 4096; i = i + 1) begin
      voltage_signal = 1;
      voltage_signal_valid = (i % 2 == 0);
      voltage_signal_valid_last = (i == 4094);
      @(negedge clk);
      check();
    end
    // signed jumps and gaps of one or two clocks, and a reset (no sample in
    // the clock after it)
    for (i = 0; i < 1024; i = i + 1) begin
      rst = (i == 513);
      voltage_signal = ((i * 73) % 521) - 260;
      voltage_signal_valid = (i % 5 == 0) || (i % 5 == 2);
      voltage_signal_valid_last = (i % 17 == 0);
      @(negedge clk);
      check();
    end
    $display("PASS sweep: %0d clocks identical to the master VCO, %0d clocks identical with the one-port macro", checked, clocks - 2);
    $finish;
  end
endmodule
""".replace("DUTS", DUTS).replace("DUT_PORTS", DUT_PORTS)

RANDOM_TB = r"""
`timescale 1ns/1ps
module vco_sin2_random_tb;
  reg clk = 0;
  always #5 clk = ~clk;
  reg rst = 1;
  reg [10:0] cos_table_write_address = 0;      // the DUT's cosine pair
  reg signed [7:0] cos_table_write_data = 0;
  reg [10:0] ref_cos_table_write_address = 0;  // the sin4 VCO's cosine pair
  reg signed [7:0] ref_cos_table_write_data = 0;
  reg [10:0] sin_table_write_address = 0;      // the sine pair, to both
  reg signed [7:0] sin_table_write_data = 0;
  reg signed [15:0] voltage_signal = 0;
  reg voltage_signal_valid = 0;
  reg voltage_signal_valid_last = 0;
  wire signed [7:0] cos_ref, sin_ref;
  wire valid_ref, last_ref;

DUTS
  vco_sin4 ref_vco (
    .clk(clk), .rst(rst),
    .cos_table_write_address(ref_cos_table_write_address),
    .cos_table_write_data(ref_cos_table_write_data),
    .sin_table_write_address(sin_table_write_address),
    .sin_table_write_data(sin_table_write_data),
    .voltage_signal(voltage_signal),
    .voltage_signal_valid(voltage_signal_valid),
    .voltage_signal_valid_last(voltage_signal_valid_last),
    .cos_out(cos_ref), .sin_out(sin_ref),
    .sin_cos_out_valid(valid_ref), .sin_cos_out_valid_last(last_ref));

  integer seed = 1, rng = 1;       // rng: the state of $random, started from seed
  integer n_clocks = 200000;
  integer clock_count = 0, compared = 0, skipped = 0;
  integer n_writes = 0, n_cos0 = 0, n_ignored = 0, n_resets = 0, n_sweeps = 0, n_aimed = 0;
  integer n_held = 0, n_reads = 0, n_waits = 0, n_samples = 0;
  // The stimulus' model of the port, independent of the design: the VCO reads
  // in the clock of a sample (entry b, read ahead), in the clock after one
  // (entry a) and in the clock after a reset (entry a); a changed sine pair is
  // written in its clock if the port is free, else it waits.
  reg pend = 0;                    // the sine pair is not written yet
  reg valid_d1 = 0, rst_d1 = 0;
  reg sin_changed = 0;             // the sine pair of the coming clock is new, in the first quarter
  integer mode = 0, mode_left = 0, read_mode = 0, read_left = 0, k, r, n_hold;
  integer next_readback = 20000;
  reg [15:0] phase = 0;            // model of integral_voltage_signal
  reg [10:0] new_sa, target;
  reg [7:0] new_sd, new_cd;
  reg aim_pending = 0;             // aim the next sample allowed at aim_entry
  reg [8:0] aim_entry;

  function integer urand(input integer n);
    begin
      urand = {$random(rng)} % n;
    end
  endfunction

  // may the coming clock carry a sample?
  function sample_allowed(input dummy);
    begin
      sample_allowed = !valid_d1 && !rst_d1 && !rst;
    end
  endfunction

  // one clock: the stimulus set now is sampled at the next rising edge; the
  // outputs are compared at the following falling edge (I/Q with the
  // reference if compare is set and no write waits)
  task step(input compare);
    reg exact, cap, ready;
    begin
      if (voltage_signal_valid && !sample_allowed(0)) begin
        $display("FAIL random seed %0d clock %0d: the stimulus breaks the sample contract", seed, clock_count);
        $fatal(1);
      end
      exact = compare && !pend;
      cap = !((voltage_signal_valid && !rst) || valid_d1 || rst_d1);
      ready = (sin_table_write_address[10:9] == 0) && (pend || sin_changed);
      if (!cap) begin
        n_reads = n_reads + 1;
        if (ready) n_waits = n_waits + 1;
      end
      pend = ready && !cap;
      sin_changed = 0;
      @(posedge clk);
      valid_d1 = !rst && voltage_signal_valid;
      rst_d1 = rst;
      if (rst) phase = 0;
      else if (voltage_signal_valid) begin
        phase = phase + voltage_signal;
        n_samples = n_samples + 1;
      end
      @(negedge clk);
      clock_count = clock_count + 1;
      check_macro(clock_count);
      if (valid_dut !== valid_ref || last_dut !== last_ref) begin
        $display("FAIL random seed %0d clock %0d: valid/last DUT %b/%b sin4 %b/%b",
                 seed, clock_count, valid_dut, last_dut, valid_ref, last_ref);
        $fatal(1);
      end
      if (exact) begin
        if (cos_dut !== cos_ref || sin_dut !== sin_ref) begin
          $display("FAIL random seed %0d clock %0d: I/Q DUT %0d/%0d sin4 %0d/%0d (phase %0d)",
                   seed, clock_count, cos_dut, sin_dut, cos_ref, sin_ref, phase[10:0]);
          $fatal(1);
        end
        compared = compared + 1;
      end else begin
        skipped = skipped + 1;
      end
    end
  endtask

  // no new pairs and no samples until no write waits
  task drain;
    begin
      voltage_signal_valid = 0;
      voltage_signal_valid_last = 0;
      while (pend || valid_d1 || rst_d1) step(1);
    end
  endtask

  // aim the samples' read at quarter entry q (as entry a or b, any quadrant)
  task aim(input [8:0] q);
    reg [1:0] quad;
    reg [8:0] offset;
    begin
      quad = urand(4);
      offset = urand(2) ? (9'd0 - q) : q;
      target = {quad, offset};
      voltage_signal = {urand(32), 11'd0} | ((target - phase[10:0]) & 11'h7ff);
      voltage_signal_valid = 1;
      n_aimed = n_aimed + 1;
    end
  endtask

  // read back all 512 entries (no writes, no waiting write)
  task sweep;
    begin
      drain();
      voltage_signal_valid = 1;
      voltage_signal_valid_last = 0;
      voltage_signal = (16'd0 - phase) & 16'h07ff;
      step(1);
      for (k = 0; k < 514; k = k + 1) begin
        voltage_signal_valid = 0;
        step(1);
        voltage_signal = 1;
        voltage_signal_valid = 1;
        step(1);
      end
      voltage_signal_valid = 0;
      n_sweeps = n_sweeps + 1;
    end
  endtask

  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    rng = seed;
    if (!$value$plusargs("clocks=%d", n_clocks)) n_clocks = 200000;
    repeat (2) @(negedge clk);
    rst = 0;
    for (k = 0; k < 3; k = k + 1) step(0);
    sweep();                                            // before any write: entry 0 only
    while (clock_count < n_clocks) begin
      if (mode_left == 0) begin
        mode = urand(4);                                // 0 mixed, 1 sine stream, 2 cosine writes, 3 idle
        mode_left = 20 + urand(400);
      end
      mode_left = mode_left - 1;
      if (read_left == 0) begin
        read_mode = urand(3);                           // samples: 0 random, 1 every other clock, 2 none
        read_left = 20 + urand(400);
      end
      read_left = read_left - 1;

      if (urand(1000) < 3) begin                        // reset for 1..3 clocks, pairs held
        voltage_signal_valid = 0;
        rst = 1;
        n_hold = 1 + urand(3);
        for (k = 0; k < n_hold; k = k + 1) step(1);
        rst = 0;
        step(1);                                        // no sample in the clock after a reset
        n_resets = n_resets + 1;
      end else if (clock_count >= next_readback) begin
        next_readback = next_readback + 20000;
        sweep();
      end

      // table writes of this clock: a sine pair (with its mirror cos[512 - k]
      // into the sin4 VCO), cos[0] to both, or a cosine write this branch ignores
      new_sa = sin_table_write_address; new_sd = sin_table_write_data;
      r = urand(100);
      if ((mode == 0 && r < 40) || (mode == 1 && r < 90)) begin
        r = urand(100);
        if (r < 15) new_sa = sin_table_write_address;   // a new value at the same address
        else if (r < 25) new_sa = phase[8:0];           // entry a of the phase shown
        else if (r < 35) new_sa = 9'd0 - phase[8:0];    // entry b of the phase shown
        else if (r < 85) new_sa = urand(512);           // first quarter: stored
        else new_sa = urand(2048);                      // anywhere: ignored above 511
        new_sd = urand(256);
      end else if ((mode == 0 && r < 55) || (mode == 2 && r < 40)) begin
        new_cd = urand(256);
        cos_table_write_address = 0; cos_table_write_data = new_cd;
        ref_cos_table_write_address = 0; ref_cos_table_write_data = new_cd;
        n_cos0 = n_cos0 + 1;
      end else if ((mode == 0 && r < 70) || (mode == 2 && r < 90)) begin
        cos_table_write_address = 1 + urand(2047);
        cos_table_write_data = urand(256);
        n_ignored = n_ignored + 1;
      end
      // the contract: a sine pair that waits is held
      if (pend && {new_sa, new_sd} != {sin_table_write_address, sin_table_write_data}) begin
        new_sa = sin_table_write_address; new_sd = sin_table_write_data;
        n_held = n_held + 1;
      end
      sin_changed = (new_sa[10:9] == 0) &&
                    ({new_sa, new_sd} != {sin_table_write_address, sin_table_write_data});
      if (sin_changed && new_sa[8:0] != 0) begin
        ref_cos_table_write_address = 11'd512 - new_sa[8:0];
        ref_cos_table_write_data = new_sd;
      end
      n_writes = n_writes + sin_changed;
      sin_table_write_address = new_sa; sin_table_write_data = new_sd;

      // the sample of this clock, if allowed: aimed at an entry written before
      // (once it is in the memory), or by the pattern of this stretch
      voltage_signal_valid = 0;
      if (sample_allowed(0)) begin
        if (aim_pending && !pend) begin
          aim(aim_entry);
          aim_pending = 0;
        end else begin
          voltage_signal = urand(65536);
          case (read_mode)
            0: voltage_signal_valid = (urand(10) < 6);
            1: voltage_signal_valid = 1;
            default: voltage_signal_valid = 0;
          endcase
        end
      end
      if (sin_changed && urand(2) == 0) begin
        aim_pending = 1;
        aim_entry = new_sa[8:0];
      end
      voltage_signal_valid_last = (urand(50) == 0);

      step(1);
    end
    drain();
    sweep();
    $display("PASS random seed %0d: %0d clocks, I/Q compared on %0d (%0d skipped), %0d samples, %0d sine writes, %0d writes of cos[0], %0d ignored cosine writes, %0d clocks with a read, %0d with a write waiting, %0d changes held back by the contract, %0d reads aimed at a new entry, %0d resets, %0d read-backs of all 512 entries; one-port macro identical on every clock",
             seed, clock_count, compared, skipped, n_samples, n_writes, n_cos0, n_ignored, n_reads, n_waits, n_held, n_aimed, n_resets, n_sweeps);
    $finish;
  end
endmodule
""".replace("DUTS", DUTS).replace("DUT_PORTS", DUT_PORTS)

# Deliberate faults of verilog/vco.v: (name, [(text, replacement), ...]).
MUTANTS = [
    ("entry b read ahead at the current phase, not the next",
     [(".read_address(b_read ? next_b_address : a_address),",
       ".read_address(b_read ? b_address : a_address),")]),
    ("a table write in a clock in which the VCO reads",
     [("wire table_write = !b_read && !voltage_signal_valid_delay1 && !rst_delay && sin_write_ready;",
       "wire table_write = sin_write_ready;")]),
    ("a table write in the clock after a reset",
     [("wire table_write = !b_read && !voltage_signal_valid_delay1 && !rst_delay && sin_write_ready;",
       "wire table_write = !b_read && !voltage_signal_valid_delay1 && sin_write_ready;")]),
    ("no hold of entry a after a write to it",
     [("if (write_hit_a_delay) begin\n    a_hold <= write_data_delay;\n  end else if (b_read) begin",
       "if (b_read) begin"),
      ("a_from_hold <= !a_read && (b_read || write_hit_a_delay || a_from_hold);",
       "a_from_hold <= !a_read && (b_read || a_from_hold);")]),
    ("a write to entry b is not shown",
     [("end else if (write_hit_b_delay) begin\n    b_entry <= write_data_delay;\n  end",
       "end")]),
    ("cos 0 taken in the clock its pair is presented (one clock early)",
     [("cos_write_zero_delay <= (cos_table_write_address == 0);\n"
       "  cos_write_data_delay <= cos_table_write_data;\n"
       "  if (cos_write_zero_delay) begin\n"
       "    cos_zero <= cos_write_data_delay;",
       "cos_write_zero_delay <= (cos_table_write_address == 0);\n"
       "  cos_write_data_delay <= cos_table_write_data;\n"
       "  if (cos_table_write_address == 0) begin\n"
       "    cos_zero <= cos_table_write_data;")]),
    ("cosine and sine swapped in the odd quadrants",
     [("wire signed [IQ_BIT_WIDTH-1:0] cos_sample = odd_quadrant_delay ? a_value : b_value;\n"
       "wire signed [IQ_BIT_WIDTH-1:0] sin_sample = odd_quadrant_delay ? b_value : a_value;",
       "wire signed [IQ_BIT_WIDTH-1:0] cos_sample = b_value;\n"
       "wire signed [IQ_BIT_WIDTH-1:0] sin_sample = a_value;")]),
    ("cos 0 not used at offset 0",
     [("wire signed [IQ_BIT_WIDTH-1:0] b_value = offset_zero_delay ? cos_zero : b_entry;",
       "wire signed [IQ_BIT_WIDTH-1:0] b_value = b_entry;")]),
    ("sine writes outside the first quarter are stored too (wrapped)",
     [("wire sin_write_ready = sin_write_in_quarter;", "wire sin_write_ready = 1'b1;")]),
    ("a write shown with the data of the next clock, not the pair it wrote",
     [("wire [IQ_BIT_WIDTH-1:0] write_data_delay = sin_write_data_delay;",
       "wire [IQ_BIT_WIDTH-1:0] write_data_delay = sin_table_write_data;")]),
    ("the cosine sign ignores the odd quadrants",
     [("assign cos_negative_delay = sin_negative_delay ^ odd_quadrant_delay;",
       "assign cos_negative_delay = sin_negative_delay;")]),
]


def git_show(rev: str, path: str) -> str:
    for name in (rev, f"origin/{rev}"):
        result = subprocess.run(["git", "show", f"{name}:{path}"], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    raise SystemExit(f"cannot read {path} from {rev} or origin/{rev}")


def one_port(vco_text: str) -> str:
    """verilog/vco.v with its memory on the one-port macro model (not included)."""
    text = vco_text.replace("module sin_table_ram #", "module sin_table_ram_unused #", 1)
    if "sin_table_ram # (" not in text:
        raise SystemExit("cannot find the instance of sin_table_ram in verilog/vco.v")
    return text.replace("sin_table_ram # (", "sin_table_macro # (")


def macro_variant(vco_text: str) -> str:
    """The same VCO as module vco_macro, on the one-port macro model."""
    return one_port(vco_text).replace("module vco #", "module vco_macro #", 1)


def build(work: Path, name: str, vco_text: str, top: str, reference: Path) -> Path:
    (work / f"{name}_vco.v").write_text(vco_text)
    (work / f"{name}_vco_macro.v").write_text(macro_variant(vco_text))
    out = work / f"{name}_{top}.vvp"
    subprocess.run(
        [os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", top, "-o", str(out),
         str(work / f"{top}.v"), str(work / f"{name}_vco.v"), str(work / f"{name}_vco_macro.v"),
         str(work / "sin_table_macro.v"), str(reference),
         str(ROOT / "verilog" / "sdpram_one_clk.v")],
        cwd=work, check=True)
    return out


def simulate(work: Path, vvp: Path, *plusargs: str) -> tuple[bool, str]:
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(vvp), *plusargs],
                            cwd=work, capture_output=True, text=True, timeout=600)
    output = result.stdout + result.stderr
    if not sim_pass(result.returncode, output, "PASS") and not mutant_caught(result.returncode, output):
        raise RuntimeError(f"simulator did not complete a valid check (exit {result.returncode}): {output[-500:]}")
    lines = [l for l in (result.stdout + result.stderr).splitlines() if l.startswith(("PASS", "FAIL"))]
    ok = result.returncode == 0 and any(l.startswith("PASS") for l in lines) \
        and not any(l.startswith("FAIL") for l in lines)
    return ok, lines[-1] if lines else (result.stdout + result.stderr).strip()[-300:]


def run_all(work: Path, name: str, vco_text: str, seeds: int, clocks: int, stop_at_fail: bool) -> bool:
    sweep = build(work, name, vco_text, "vco_sin2_sweep_tb", work / "vco_reference.v")
    rand = build(work, name, vco_text, "vco_sin2_random_tb", work / "vco_sin4.v")
    all_ok = True
    ok, line = simulate(work, sweep)
    print(f"  {line}")
    all_ok &= ok
    if stop_at_fail and not ok:
        return False
    for seed in range(1, seeds + 1):
        ok, line = simulate(work, rand, f"+seed={seed}", f"+clocks={clocks}")
        print(f"  {line}")
        all_ok &= ok
        if stop_at_fail and not ok:
            return False
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=positive, default=4)
    parser.add_argument("--clocks", type=positive, default=1000000)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--write-one-port", metavar="FILE",
                        help="write verilog/vco.v with its memory on the one-port macro model "
                             "(model included) to FILE, for a system run, and stop")
    args = parser.parse_args()

    if args.write_one_port:
        text = one_port((ROOT / "verilog" / "vco.v").read_text())
        Path(args.write_one_port).write_text(text + MACRO)
        print(f"wrote {args.write_one_port}")
        return

    count = 2048
    cosine = [round(127 * math.cos(2 * math.pi * i / count)) for i in range(count)]
    sine = [round(127 * math.sin(2 * math.pi * i / count)) for i in range(count)]
    quarter = count // 4
    broken = [k for k in range(1, quarter) if cosine[k] != sine[quarter - k]]
    if broken:
        raise SystemExit(f"test tables: cos[k] != sin[{quarter} - k] at k = {broken[:5]}")
    vco_text = (ROOT / "verilog" / "vco.v").read_text()

    with tempfile.TemporaryDirectory(prefix="vco-sin2-") as directory:
        work = Path(directory)
        (work / "vco_reference.v").write_text(
            git_show("master", "verilog/vco.v").replace("module vco #", "module vco_reference #", 1))
        (work / "vco_sin4.v").write_text(
            git_show("ble-tx-sin4", "verilog/vco.v").replace("module vco #", "module vco_sin4 #", 1))
        (work / "sin_table_macro.v").write_text(MACRO)
        (work / "vco_sin2_sweep_tb.v").write_text(SWEEP_TB)
        (work / "vco_sin2_random_tb.v").write_text(RANDOM_TB)
        for name, values in (("cos.hex", cosine), ("sin.hex", sine)):
            (work / name).write_text("".join(f"{value & 0xff:02x}\n" for value in values))

        print("verilog/vco.v:")
        if not run_all(work, "dut", vco_text, args.seeds, args.clocks, stop_at_fail=False):
            raise SystemExit("FAIL")
        if args.mutants:
            caught = 0
            for index, (label, edits) in enumerate(MUTANTS, 1):
                text = vco_text
                for old, new in edits:
                    if old not in text:
                        raise SystemExit(f"mutant {index}: text not found: {old!r}")
                    text = text.replace(old, new)
                print(f"mutant {index} ({label}):")
                if run_all(work, f"m{index}", text, min(args.seeds, 3), min(args.clocks, 200000),
                           stop_at_fail=True):
                    print("  NOT CAUGHT")
                else:
                    caught += 1
            print(f"mutants caught: {caught}/{len(MUTANTS)}")
            if caught != len(MUTANTS):
                raise SystemExit("FAIL")
        print("PASS")


if __name__ == "__main__":
    main()
