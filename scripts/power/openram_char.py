"""OpenRAM's SPICE characterization of one SRAM, measured at one clock period.

Author: Miguel Simões

This is OpenRAM's sram_compiler.py with these changes, all in the characterizer:
- it does not search for the minimum period. It measures delay and power at the
  first feasible period (OpenRAM's estimate for the technology, 5 ns in
  FreePDK45, doubled until the macro works), or, with --period, at that period
  without the feasibility runs (the measurement run still checks every value
  read, and fails if the period is too short). Only power is used here
  (summarize_sram_char.py): the energy of an access is (the average power of
  its cycle - that of a deselected cycle) x the period, and hardly depends on
  the period; the binary search for the minimum period would take some ten
  more SPICE runs per port. The .lib's minimum_period is then this period, not
  a minimum;
- with trim_netlist = False in the configuration (the whole netlist simulated,
  every bitcell), OpenRAM's leakage run is made once: OpenRAM would simulate the
  same netlist again as its "trimmed" one. That run gives the supply power
  5-10 ns after a power-up from 0 V, not the settled leakage (sram_leakage.py).

Usage (OpenRAM's Python, in the directory of the configuration):
  python openram_char.py <config.py> [--period NS]
"""
import importlib
import importlib.util
import os
import sys

period = None
argv = sys.argv[1:]
if "--period" in argv:
    i = argv.index("--period")
    period = float(argv[i + 1])
    del argv[i:i + 2]
sys.argv = [sys.argv[0]] + argv

# as sram_compiler.py
sys.path.insert(0, os.path.dirname(importlib.util.find_spec("openram").origin))
from common import make_openram_package  # noqa: E402  (OpenRAM's common.py)
make_openram_package()
import openram  # noqa: E402

(OPTS, args) = openram.parse_args()
if len(args) != 1:
    print(__doc__)
    sys.exit(2)
OPTS.top_process = "openram"
from openram import debug  # noqa: E402
openram.init_openram(config_file=args[0])
openram.setup_bitcell()
openram.print_banner()


delay_module = importlib.import_module("openram.characterizer.delay")
find_feasible_period = delay_module.delay.find_feasible_period
run_power_simulation = delay_module.delay.run_power_simulation


def given_or_feasible_period(self):
    """Replaces delay.find_feasible_period: with --period, that period, no runs."""
    if period is None:
        return find_feasible_period(self)
    self.period = period
    debug.print_raw("CHAR: period {0} ns given, no feasibility runs".format(self.period))
    return [{} for _ in self.all_ports]


def measure_at_feasible_period(self, feasible_delays):
    """Replaces delay.find_min_period: no search, the feasible period (or --period)."""
    debug.print_raw("CHAR: measuring at {0} ns (no minimum-period search)".format(self.period))
    self.targ_read_ports = []
    self.targ_write_ports = []
    return float(self.period)


def leakage_once(self):
    """Replaces delay.run_power_simulation: without trimming, one leakage run."""
    if OPTS.trim_netlist:
        return run_power_simulation(self)
    self.write_power_stimulus(trim=False)
    self.stim.run_sim(self.power_stim_sp)
    leakage_power = delay_module.parse_spice_list("timing", "leakage_power")
    debug.check(leakage_power != "Failed", "Could not measure leakage power.")
    debug.print_raw("CHAR: leakage of the whole array {0} mW (untrimmed netlist)".format(leakage_power * 1e3))
    return (leakage_power * 1e3, leakage_power * 1e3)


delay_module.delay.find_feasible_period = given_or_feasible_period
delay_module.delay.find_min_period = measure_at_feasible_period
delay_module.delay.run_power_simulation = leakage_once

from openram import sram  # noqa: E402
s = sram()
s.save()
openram.end_openram()
