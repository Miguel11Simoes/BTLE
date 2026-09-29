"""Check the VCO of ble-tx-sin8 (one {cos, sin} table memory) with Icarus Verilog.

Author: Miguel Simões

Run from the repository root with IVERILOG and VVP in PATH (or set their
environment variables). Needs the master and ble-tx-sin4 branches, local or as
origin/<name>.

  sweep   the test of tests/test_vco_sin4.py, against the master VCO: both full
          tables written, cosine and sine at the same address on every clock;
          every phase address, signed jumps, gaps and a reset.
  random  clock-by-clock lockstep against the ble-tx-sin4 VCO, whose two quarter
          tables are separate memories written on every clock. Random table
          writes: one table at a time, a new value at the same address, both
          tables at the same address, both at different addresses in the same
          clock, streams of one table, addresses outside the first quarter,
          resets. The stimulus respects the contract of the shared write port:
          at most w + 1 table writes in any w consecutive clocks (two writes to
          the same address in one clock count as one), so at most one write
          waits. The outputs are compared on every clock in which no write can
          be waiting (the stimulus tracks that, independently of the design),
          and reads are aimed at the entries just written. valid/last are
          compared on every clock; every 20 000 clocks all 512 table entries
          are read back.

  python3 tests/test_vco_sin8.py [--seeds N] [--clocks N] [--mutants]

With --mutants, each of 7 deliberate faults of verilog/vco.v must make the
sweep or the random lockstep fail.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]

PORTS = """
    .clk(clk), .rst(rst),
    .cos_table_write_address(cos_table_write_address),
    .cos_table_write_data(cos_table_write_data),
    .sin_table_write_address(sin_table_write_address),
    .sin_table_write_data(sin_table_write_data),
    .voltage_signal(voltage_signal),
    .voltage_signal_valid(voltage_signal_valid),
    .voltage_signal_valid_last(voltage_signal_valid_last),
"""

SWEEP_TB = r"""
`timescale 1ns/1ps
module vco_sin8_sweep_tb;
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
  wire signed [7:0] cos_dut, sin_dut, cos_ref, sin_ref;
  wire valid_dut, last_dut, valid_ref, last_ref;
  reg signed [7:0] cos_table [0:2047];
  reg signed [7:0] sin_table [0:2047];
  integer i;
  integer checked = 0;

  vco dut (PORTS
    .cos_out(cos_dut), .sin_out(sin_dut),
    .sin_cos_out_valid(valid_dut), .sin_cos_out_valid_last(last_dut));
  vco_reference ref_vco (PORTS
    .cos_out(cos_ref), .sin_out(sin_ref),
    .sin_cos_out_valid(valid_ref), .sin_cos_out_valid_last(last_ref));

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
    for (i = 0; i < 2048; i = i + 1) begin
      voltage_signal = 1;
      voltage_signal_valid = 1;
      voltage_signal_valid_last = (i == 2047);
      @(negedge clk);
      check();
    end
    for (i = 0; i < 1024; i = i + 1) begin
      rst = (i == 511);
      voltage_signal = ((i * 73) % 521) - 260;
      voltage_signal_valid = (i % 3 != 0);
      voltage_signal_valid_last = (i % 17 == 0);
      @(negedge clk);
      check();
    end
    $display("PASS sweep: %0d clocks identical to the master VCO", checked);
    $finish;
  end
endmodule
""".replace("PORTS", PORTS)

RANDOM_TB = r"""
`timescale 1ns/1ps
module vco_sin8_random_tb;
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
  wire signed [7:0] cos_dut, sin_dut, cos_ref, sin_ref;
  wire valid_dut, last_dut, valid_ref, last_ref;

  vco dut (PORTS
    .cos_out(cos_dut), .sin_out(sin_dut),
    .sin_cos_out_valid(valid_dut), .sin_cos_out_valid_last(last_dut));
  vco_sin4 ref_vco (PORTS
    .cos_out(cos_ref), .sin_out(sin_ref),
    .sin_cos_out_valid(valid_ref), .sin_cos_out_valid_last(last_ref));

  integer seed = 1, rng = 1;       // rng: the state of $random, started from seed
  integer n_clocks = 200000;
  integer clock_count = 0, compared = 0, skipped = 0;
  integer n_writes = 0, n_same = 0, n_contention = 0, n_resets = 0, n_sweeps = 0, n_aimed = 0;
  integer backlog = 0;             // writes the upstream VCO has done and a one-port memory may not have
  integer quiet = 0;               // clocks without data comparison left (after a reset)
  integer mode = 0, mode_left = 0, k, a, r, n_hold;
  integer next_readback = 20000;
  reg [15:0] phase = 0;            // model of integral_voltage_signal
  reg [10:0] new_ca, new_sa, target;
  reg [7:0] new_cd, new_sd;
  reg cos_in, sin_in, cos_changed, sin_changed;

  function integer urand(input integer n);
    begin
      urand = {$random(rng)} % n;
    end
  endfunction

  // one clock: the stimulus set now is sampled at the next rising edge; the
  // outputs are compared at the following falling edge
  task step(input exact);
    begin
      @(posedge clk);
      if (rst) phase = 0;
      else if (voltage_signal_valid) phase = phase + voltage_signal;
      @(negedge clk);
      clock_count = clock_count + 1;
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

  // aim the read of the clock after next at quarter entry q (any quadrant)
  task aim(input [8:0] q);
    reg [1:0] quad;
    reg [8:0] offset;
    begin
      quad = urand(4);
      offset = quad[0] ? (9'd0 - q) : q;
      target = {quad, offset};
      voltage_signal = {urand(32), 11'd0} | ((target - phase[10:0]) & 11'h7ff);
      voltage_signal_valid = 1;
      n_aimed = n_aimed + 1;
    end
  endtask

  task new_pair(input [10:0] old_address, output [10:0] address, output [7:0] data);
    begin
      r = urand(100);
      if (r < 15) address = old_address;                // a new value at the same address
      else if (r < 80) address = urand(512);            // first quarter: stored
      else address = urand(2048);                       // anywhere: ignored above 511
      data = urand(256);
    end
  endtask

  // read back all 512 entries of both tables (no writes, no waiting write)
  task sweep;
    begin
      voltage_signal_valid = 1;
      voltage_signal_valid_last = 0;
      voltage_signal = (16'd0 - phase) & 16'h07ff;
      step(backlog == 0);
      backlog = 0;
      for (k = 0; k < 514; k = k + 1) begin
        voltage_signal = 1;
        step(1);
      end
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
        mode = urand(4);                                // 0 mixed, 1 cos stream, 2 sin stream, 3 idle
        mode_left = 20 + urand(400);
      end
      mode_left = mode_left - 1;

      if (urand(1000) < 3) begin                        // reset for 1..3 clocks, pairs held
        rst = 1;
        n_hold = 1 + urand(3);
        for (k = 0; k < n_hold; k = k + 1) step(0);
        rst = 0;
        for (k = 0; k < 3; k = k + 1) step(0);          // the first clock after reset rewrites both pairs
        backlog = 0;
        n_resets = n_resets + 1;
      end else if (clock_count >= next_readback) begin
        next_readback = next_readback + 20000;
        for (k = 0; k < 2; k = k + 1) begin             // let a waiting write finish
          step(backlog == 0);
          backlog = (backlog > 0) ? backlog - 1 : 0;
        end
        sweep();
      end

      // table writes of this clock
      new_ca = cos_table_write_address; new_cd = cos_table_write_data;
      new_sa = sin_table_write_address; new_sd = sin_table_write_data;
      r = urand(100);
      case (mode)
        0: begin
          if (r < 30) new_pair(new_ca, new_ca, new_cd);
          else if (r < 60) new_pair(new_sa, new_sa, new_sd);
          else if (r < 72) begin new_pair(new_ca, new_ca, new_cd); new_sa = new_ca; new_sd = urand(256); end
          else if (r < 82) begin new_pair(new_ca, new_ca, new_cd); new_pair(new_sa, new_sa, new_sd); end
        end
        1: begin
          new_pair(new_ca, new_ca, new_cd);
          if (r < 20) new_pair(new_sa, new_sa, new_sd);
        end
        2: begin
          new_pair(new_sa, new_sa, new_sd);
          if (r < 20) new_pair(new_ca, new_ca, new_cd);
        end
        default: ;
      endcase

      // the writes this clock brings, as the upstream VCO counts them
      cos_in = (new_ca[10:9] == 0);
      sin_in = (new_sa[10:9] == 0);
      cos_changed = cos_in && ({new_ca, new_cd} != {cos_table_write_address, cos_table_write_data});
      sin_changed = sin_in && ({new_sa, new_sd} != {sin_table_write_address, sin_table_write_data});
      a = cos_changed + sin_changed;
      if (a == 2 && backlog == 0 && new_ca[8:0] == new_sa[8:0]) a = 1;
      if (a > 2 - backlog) begin                        // keep the contract: drop the sine change
        new_sa = sin_table_write_address; new_sd = sin_table_write_data;
        sin_changed = 0;
        a = cos_changed;
      end
      if (cos_changed && sin_changed) begin
        if (a == 1) n_same = n_same + 1; else n_contention = n_contention + 1;
      end
      n_writes = n_writes + cos_changed + sin_changed;
      cos_table_write_address = new_ca; cos_table_write_data = new_cd;
      sin_table_write_address = new_sa; sin_table_write_data = new_sd;

      // the read of the clock after next: aimed at an entry written now, or random
      r = urand(100);
      if (r < 60 && (cos_changed || sin_changed)) begin
        if (cos_changed && (!sin_changed || urand(2) == 0)) aim(new_ca[8:0]);
        else aim(new_sa[8:0]);
      end else begin
        voltage_signal = urand(65536);
        voltage_signal_valid = (urand(10) < 8);
      end
      voltage_signal_valid_last = (urand(50) == 0);

      step(backlog == 0);
      backlog = backlog + a - 1;
      if (backlog < 0) backlog = 0;
    end
    for (k = 0; k < 2; k = k + 1) begin
      step(backlog == 0);
      backlog = (backlog > 0) ? backlog - 1 : 0;
    end
    sweep();
    $display("PASS random seed %0d: %0d clocks, I/Q compared on %0d (%0d skipped), %0d table writes (%0d same-address pairs, %0d clocks with two addresses), %0d reads aimed at a new entry, %0d resets, %0d read-backs of all 512 entries",
             seed, clock_count, compared, skipped, n_writes, n_same, n_contention, n_aimed, n_resets, n_sweeps);
    $finish;
  end
endmodule
""".replace("PORTS", PORTS)

# Deliberate faults of verilog/vco.v: (name, [(text, replacement), ...]).
MUTANTS = [
    ("no merge: same-address writes take two clocks",
     [("wire same_write_address = (cos_request_address == sin_request_address);",
       "wire same_write_address = 1'b0;")]),
    ("no bypass: every cosine write waits one clock",
     [("wire cos_write_request = cos_write_queued || cos_write_new;",
       "wire cos_write_request = cos_write_queued;"),
      ("if (cos_write_new && (!cos_write || cos_write_queued)) begin",
       "if (cos_write_new) begin")]),
    ("no write on the first clock after reset",
     [("(rst_delay ||\n    {cos_table", "(1'b0 ||\n    {cos_table"),
      ("(rst_delay ||\n    {sin_table", "(1'b0 ||\n    {sin_table")]),
    ("the sine writes on every request, at whichever address the port has",
     [("wire sin_write = sin_write_request && (!cos_write_request || same_write_address ||\n"
       "                                       !cos_write);",
       "wire sin_write = sin_write_request;")]),
    ("the queue drops a pair that arrives while the queued one is written",
     [("if (cos_write_new && (!cos_write || cos_write_queued)) begin",
       "if (cos_write_new && !cos_write) begin")]),
    ("cosine and sine halves swapped on the read",
     [(".read_data({cos_quarter_data, sin_quarter_data})",
       ".read_data({sin_quarter_data, cos_quarter_data})")]),
    ("a change of data alone at the same address is not written",
     [("{cos_table_write_address, cos_table_write_data} != cos_write_pair_delay",
       "cos_table_write_address != cos_write_pair_delay[SIN_COS_ADDR_BIT_WIDTH+IQ_BIT_WIDTH-1:IQ_BIT_WIDTH]")]),
]


def git_show(rev: str, path: str) -> str:
    for name in (rev, f"origin/{rev}"):
        result = subprocess.run(["git", "show", f"{name}:{path}"], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    raise SystemExit(f"cannot read {path} from {rev} or origin/{rev}")


def build(work: Path, name: str, vco_text: str, top: str, reference: Path) -> Path:
    (work / f"{name}_vco.v").write_text(vco_text)
    out = work / f"{name}_{top}.vvp"
    subprocess.run(
        [os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", top, "-o", str(out),
         str(work / f"{top}.v"), str(work / f"{name}_vco.v"), str(reference),
         str(ROOT / "verilog" / "sdpram_one_clk.v")],
        cwd=work, check=True)
    return out


def simulate(work: Path, vvp: Path, *plusargs: str) -> tuple[bool, str]:
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(vvp), *plusargs],
                            cwd=work, capture_output=True, text=True)
    lines = [l for l in (result.stdout + result.stderr).splitlines() if l.startswith(("PASS", "FAIL"))]
    ok = result.returncode == 0 and any(l.startswith("PASS") for l in lines) \
        and not any(l.startswith("FAIL") for l in lines)
    return ok, lines[-1] if lines else (result.stdout + result.stderr).strip()[-300:]


def run_all(work: Path, name: str, vco_text: str, seeds: int, clocks: int, stop_at_fail: bool) -> bool:
    sweep = build(work, name, vco_text, "vco_sin8_sweep_tb", work / "vco_reference.v")
    rand = build(work, name, vco_text, "vco_sin8_random_tb", work / "vco_sin4.v")
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
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--clocks", type=int, default=1000000)
    parser.add_argument("--mutants", action="store_true")
    args = parser.parse_args()

    count = 2048
    cosine = [round(127 * math.cos(2 * math.pi * i / count)) for i in range(count)]
    sine = [round(127 * math.sin(2 * math.pi * i / count)) for i in range(count)]
    vco_text = (ROOT / "verilog" / "vco.v").read_text()

    with tempfile.TemporaryDirectory(prefix="vco-sin8-") as directory:
        work = Path(directory)
        (work / "vco_reference.v").write_text(
            git_show("master", "verilog/vco.v").replace("module vco #", "module vco_reference #", 1))
        (work / "vco_sin4.v").write_text(
            git_show("ble-tx-sin4", "verilog/vco.v").replace("module vco #", "module vco_sin4 #", 1))
        (work / "vco_sin8_sweep_tb.v").write_text(SWEEP_TB)
        (work / "vco_sin8_random_tb.v").write_text(RANDOM_TB)
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
