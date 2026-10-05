"""Check the VCO with fixed tables (ble-tx-rom: a ROM; ble-tx-cordic: a CORDIC) with Icarus Verilog.

Author: Miguel Simões

This branch's verilog/vco.v gives the project's COS and SIN tables (python/btlelib.py:
round(127 cos), round(127 sin) of 2 pi k / 2048) from the first eighth of the wave,
fixed: a ROM of 257 pairs on ble-tx-rom, an exact CORDIC on ble-tx-cordic. The table
writes are ignored. It is checked against the master VCO, whose two memories are
written with those tables as the upstream TX testbench writes them (cosine and sine at
the same address on every clock), on every clock: cos_out, sin_out, valid and last.

  sweep   after the tables, the phase steps by +1, then by -1, then by 7, on every
          clock, 2 048 clocks each: every phase, in both directions and in strides.
  random  random 16-bit voltage samples on random clocks, on every clock, every other
          clock or none, in stretches; random valid_last; resets of 1..3 clocks; the
          held table pair moves on to random addresses with the project's values, as
          upstream rewrites it on every clock. Every clock is compared, resets included.

No output may be unknown once the tables are written.

  python3 tests/test_vco_fixed.py [--seeds N] [--clocks N] [--mutants]

Run from the repository root with IVERILOG and VVP in PATH (or set their environment
variables). Needs the master branch, local or as origin/master. With --mutants, each
deliberate fault of verilog/vco.v (the ROM's or the CORDIC's, by what the file holds)
must make a testbench fail.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/validation"))
from result_guard import sim_pass, mutant_caught, positive

TB = r"""
`timescale 1ns/1ps
module vco_fixed_tb;
  reg clk = 0;
  always #5 clk = ~clk;
  reg rst = 1;
  reg [10:0] cos_table_write_address = 0, sin_table_write_address = 0;
  reg signed [7:0] cos_table_write_data = 0, sin_table_write_data = 0;
  reg signed [15:0] voltage_signal = 0;
  reg voltage_signal_valid = 0, voltage_signal_valid_last = 0;
  wire signed [7:0] cos_ref, sin_ref, cos_dut, sin_dut;
  wire valid_ref, last_ref, valid_dut, last_dut;

  vco_reference ref_i (.clk(clk), .rst(rst),
    .cos_table_write_address(cos_table_write_address), .cos_table_write_data(cos_table_write_data),
    .sin_table_write_address(sin_table_write_address), .sin_table_write_data(sin_table_write_data),
    .voltage_signal(voltage_signal), .voltage_signal_valid(voltage_signal_valid),
    .voltage_signal_valid_last(voltage_signal_valid_last),
    .cos_out(cos_ref), .sin_out(sin_ref), .sin_cos_out_valid(valid_ref), .sin_cos_out_valid_last(last_ref));
  vco dut (.clk(clk), .rst(rst),
    .cos_table_write_address(cos_table_write_address), .cos_table_write_data(cos_table_write_data),
    .sin_table_write_address(sin_table_write_address), .sin_table_write_data(sin_table_write_data),
    .voltage_signal(voltage_signal), .voltage_signal_valid(voltage_signal_valid),
    .voltage_signal_valid_last(voltage_signal_valid_last),
    .cos_out(cos_dut), .sin_out(sin_dut), .sin_cos_out_valid(valid_dut), .sin_cos_out_valid_last(last_dut));

  reg signed [7:0] cos_t [0:2047];
  reg signed [7:0] sin_t [0:2047];
  integer seed = 1, seed0 = 1, clocks = 100000, clock_count = 0, compared = 0, samples = 0, resets = 0, pairs = 0;
  integer k, n, mode = 0, left = 0;
  reg compare = 0;
  reg [8*6-1:0] stage = "sweep";

  function integer urand(input integer range);
    begin urand = $unsigned($random(seed)) % range; end
  endfunction

  task check;
    begin
      if (cos_dut !== cos_ref || sin_dut !== sin_ref || valid_dut !== valid_ref || last_dut !== last_ref ||
          ^{cos_dut, sin_dut, valid_dut, last_dut} === 1'bx) begin
        $display("FAIL %0s seed %0d at clock %0d: master I/Q=%0d/%0d valid/last=%b/%b; this VCO I/Q=%0d/%0d valid/last=%b/%b",
                 stage, seed0, clock_count, cos_ref, sin_ref, valid_ref, last_ref, cos_dut, sin_dut, valid_dut, last_dut);
        $fatal(1);
      end
      compared = compared + 1;
    end
  endtask

  task step;  // one clock; compare 1 ns after the edge, when both have registered it
    begin
      @(posedge clk); #1;
      clock_count = clock_count + 1;
      if (compare) check;
      samples = samples + voltage_signal_valid;
    end
  endtask

  task hold_pair(input integer address);  // the held pair, with the project's values
    begin
      cos_table_write_address = address; cos_table_write_data = cos_t[address];
      sin_table_write_address = address; sin_table_write_data = sin_t[address];
    end
  endtask

  initial begin
    if ($value$plusargs("seed=%d", seed)) ;
    if ($value$plusargs("clocks=%d", clocks)) ;
    seed0 = seed;
    $readmemh("cos.hex", cos_t);
    $readmemh("sin.hex", sin_t);
    @(posedge clk); #1; step; step;
    rst = 0;
    for (k = 0; k < 2048; k = k + 1) begin hold_pair(k); step; end
    hold_pair(0); step;
    compare = 1;
    // sweep: every phase, both directions, and strides
    voltage_signal_valid = 1;
    voltage_signal = 1;  for (k = 0; k < 2048; k = k + 1) step;
    voltage_signal = -1; for (k = 0; k < 2048; k = k + 1) step;
    voltage_signal = 7;  for (k = 0; k < 2048; k = k + 1) step;
    voltage_signal_valid = 0; step; step;
    $display("PASS sweep: 6 144 phase steps, %0d clocks compared", compared);
    stage = "random";
    // random
    while (clock_count < clocks) begin
      if (left == 0) begin mode = urand(4); left = 10 + urand(500); end
      left = left - 1;
      if (urand(1000) < 3) begin                       // a reset of 1..3 clocks
        voltage_signal_valid = 0; rst = 1;
        n = 1 + urand(3);
        for (k = 0; k < n; k = k + 1) step;
        rst = 0; resets = resets + 1;
      end
      if (urand(100) < 30) begin hold_pair(urand(2048)); pairs = pairs + 1; end
      voltage_signal = urand(65536);
      case (mode)
        0: voltage_signal_valid = (urand(10) < 6);
        1: voltage_signal_valid = 1;
        2: voltage_signal_valid = (clock_count % 2 == 0);
        default: voltage_signal_valid = 0;
      endcase
      voltage_signal_valid_last = (urand(50) == 0);
      step;
    end
    voltage_signal_valid = 0; step; step;
    $display("PASS random seed %0d: %0d clocks, %0d compared, %0d samples, %0d resets, %0d table pairs held",
             seed0, clock_count, compared, samples, resets, pairs);
    $finish;
  end
endmodule
"""

COMMON_MUTANTS = [
    ("the fold above 256 off by one (511 - o instead of 512 - o)",
     [("wire [8:0] folded = upper ? -offset : offset;", "wire [8:0] folded = upper ? ~offset : offset;")]),
    ("cosine and sine not swapped in the odd quadrants",
     [("wire [6:0] cos_magnitude = quadrant[0] ? a : b;\nwire [6:0] sin_magnitude = quadrant[0] ? b : a;",
       "wire [6:0] cos_magnitude = b;\nwire [6:0] sin_magnitude = a;")]),
    ("the cosine sign ignores the odd quadrants",
     [("wire cos_negative = quadrant[0] ^ quadrant[1];", "wire cos_negative = quadrant[1];")]),
    ("the outputs one clock early (not registered)",
     [("always @ (posedge clk) begin\n  cos_out <= cos_negative", "always @* begin\n  cos_out = cos_negative"),
      ("\n  sin_out <= sin_negative", "\n  sin_out = sin_negative")]),
    ("valid one clock early",
     [("sin_cos_out_valid <= voltage_signal_valid_delay1;", "sin_cos_out_valid <= voltage_signal_valid;")]),
    ("the phase from the wrong bits of the integral",
     [("wire [SIN_COS_ADDR_BIT_WIDTH-1:0] phase = integral_voltage_signal[(SIN_COS_ADDR_BIT_WIDTH-1) : 0];",
       "wire [SIN_COS_ADDR_BIT_WIDTH-1:0] phase = integral_voltage_signal[SIN_COS_ADDR_BIT_WIDTH : 1];")]),
]


def rom_mutants(text: str) -> list:
    s = round(127 * math.sin(2 * math.pi * 168 / 2048))
    c = round(127 * math.cos(2 * math.pi * 168 / 2048))
    entry = f"9'd168: begin s_rom = 7'd{s}; c_rom = 7'd{c}; end"
    return [("one ROM entry off by one (|sin| at offset 168)",
             [(entry, f"9'd168: begin s_rom = 7'd{s + 1}; c_rom = 7'd{c}; end")])] + COMMON_MUTANTS


def cordic_mutants(text: str) -> list:
    import re
    last = int(re.search(r"x_rounded = x(\d+) \+", text).group(1))
    a1 = re.search(r"z1 = up0 \? z0 - (\d+)'sd(\d+)", text)
    return [
        (f"one iteration fewer ({last - 1})",
         [(f"x_rounded = x{last} +", f"x_rounded = x{last - 1} +"), (f"y_rounded = y{last} +", f"y_rounded = y{last - 1} +")]),
        ("the rounding left out (truncation)",
         [(f"x_rounded = x{last} + ", f"x_rounded = x{last} + 0 * "), (f"y_rounded = y{last} + ", f"y_rounded = y{last} + 0 * ")]),
        ("the direction of iteration 5 inverted",
         [("wire up5 = !z5[", "wire up5 = z5[")]),
        ("iteration 2 shifts by 3",
         [("x3 = up2 ? x2 - (y2 >>> 2) : x2 + (y2 >>> 2);", "x3 = up2 ? x2 - (y2 >>> 3) : x2 + (y2 >>> 3);")]),
        ("the start vector without the CORDIC gain",
         [(re.search(r"wire signed \[\d+:0\] x0 = \d+'sd\d+;", text).group(0),
           re.sub(r"'sd\d+;", "'sd32512;", re.search(r"wire signed \[\d+:0\] x0 = \d+'sd\d+;", text).group(0)))]),
    ] + COMMON_MUTANTS


def git_show(rev: str, path: str) -> str:
    for name in (rev, f"origin/{rev}"):
        result = subprocess.run(["git", "show", f"{name}:{path}"], cwd=ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    raise SystemExit(f"cannot read {path} from {rev} or origin/{rev}")


def build(work: Path, name: str, vco_text: str) -> Path:
    (work / f"{name}_vco.v").write_text(vco_text)
    out = work / f"{name}.vvp"
    subprocess.run([os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "vco_fixed_tb", "-o", str(out),
                    str(work / "vco_fixed_tb.v"), str(work / f"{name}_vco.v"), str(work / "vco_reference.v"),
                    str(work / "sdpram_one_clk.v")], cwd=work, check=True)
    return out


def simulate(work: Path, vvp: Path, *plusargs: str) -> tuple[bool, str]:
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(vvp), *plusargs],
                            cwd=work, capture_output=True, text=True, timeout=1200)
    output = result.stdout + result.stderr
    if not sim_pass(result.returncode, output, "PASS random") and not mutant_caught(result.returncode, output):
        raise RuntimeError(f"simulator did not complete a valid check (exit {result.returncode}): {output[-500:]}")
    lines = [l for l in output.splitlines() if l.startswith(("PASS", "FAIL"))]
    ok = result.returncode == 0 and any(l.startswith("PASS random") for l in lines) \
        and not any(l.startswith("FAIL") for l in lines)
    return ok, " | ".join(lines[-2:]) if lines else output.strip()[-300:]


def run_all(work: Path, name: str, vco_text: str, seeds: int, clocks: int, stop_at_fail: bool) -> bool:
    vvp = build(work, name, vco_text)
    all_ok = True
    for seed in range(1, seeds + 1):
        ok, line = simulate(work, vvp, f"+seed={seed}", f"+clocks={clocks}")
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
    args = parser.parse_args()

    count = 2048
    cosine = [round(127 * math.cos(2 * math.pi * i / count)) for i in range(count)]
    sine = [round(127 * math.sin(2 * math.pi * i / count)) for i in range(count)]
    vco_text = (ROOT / "verilog" / "vco.v").read_text()
    if "s_rom" in vco_text:
        mutants = rom_mutants(vco_text)
    elif "x_rounded" in vco_text:
        mutants = cordic_mutants(vco_text)
    else:
        raise SystemExit("verilog/vco.v is neither the ROM nor the CORDIC VCO")

    with tempfile.TemporaryDirectory(prefix="vco-fixed-") as directory:
        work = Path(directory)
        (work / "vco_reference.v").write_text(
            git_show("master", "verilog/vco.v").replace("module vco #", "module vco_reference #", 1))
        (work / "sdpram_one_clk.v").write_text(git_show("master", "verilog/sdpram_one_clk.v"))
        (work / "vco_fixed_tb.v").write_text(TB)
        for name, values in (("cos.hex", cosine), ("sin.hex", sine)):
            (work / name).write_text("".join(f"{value & 0xff:02x}\n" for value in values))

        print("verilog/vco.v:")
        if not run_all(work, "dut", vco_text, args.seeds, args.clocks, stop_at_fail=False):
            raise SystemExit("FAIL")
        if args.mutants:
            caught = 0
            for index, (label, edits) in enumerate(mutants, 1):
                text = vco_text
                for old, new in edits:
                    if old not in text:
                        raise SystemExit(f"mutant {index}: text not found: {old!r}")
                    text = text.replace(old, new)
                print(f"mutant {index} ({label}):")
                if run_all(work, f"m{index}", text, min(args.seeds, 2), min(args.clocks, 100000), stop_at_fail=True):
                    print("  NOT CAUGHT")
                else:
                    caught += 1
            print(f"mutants caught: {caught}/{len(mutants)}")
            if caught != len(mutants):
                raise SystemExit("FAIL")
        print("PASS")


if __name__ == "__main__":
    main()
