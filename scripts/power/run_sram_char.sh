#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Read, write and deselected-cycle energies of SRAM macros: OpenRAM in FreePDK45
# (the macros of scripts/area/run_openram.sh), its netlist characterized with
# SPICE (ngspice or Xyce from OpenRAM's conda; nominal corner, one input slew and one
# output load) instead of the analytical model. The analytical .lib of
# run_openram.sh gives a clock the same power whether the macro reads, writes
# or is deselected (OpenRAM's analytical model writes one estimate of the whole
# array, every gate at 100 MHz, into all four), so it cannot tell an access
# from an idle clock.
#
# Per macro, OpenRAM's measures, each the average supply power over one clock
# cycle (mW), with the other port deselected:
#   port 0 (RW)  write, read, and deselected (csb0 high, web0 low or high)
#   port 1 (R)   read, and deselected                      (1RW1R only)
# and OpenRAM's leakage of the whole array (all ports deselected, clock low): the
# supply power 5-10 ns after a power-up from 0 V, which is not the macro's leakage
# (sram_leakage.py; run_sram_leakage.sh measures it once the macro has settled).
# summarize_sram_char.py turns them into the energy of each access, relative to
# a deselected clock of the same port, and with the settled leakage (--leakage)
# into the energy of a deselected clock, at the period of the measurement:
# openram_char.py measures at the feasible period, without the minimum-period
# search, or at PERIOD_NS without the feasibility runs.
#
# The whole netlist is simulated, every bitcell. OpenRAM's default trims it to
# the bitcells of the outer rows and columns (trim_netlist), which keeps the
# periphery but leaves the other bitlines and wordlines without most of their
# load, and adds the leakage of the cells it removes as a constant, so its
# access energies come out low (by about a fifth on the 256 x 8 one-port macro,
# run sram-char-trimmed); TRIM=1 keeps that default (faster).
#
# Macro names as in run_openram.sh: sram_<1rw|1rw1r>_<word bits>x<words>.
# Usage (WSL/Linux, repository root): scripts/power/run_sram_char.sh <label> <macro ...>
# Env: OPENRAM_PY  python with OpenRAM (default ~/venvs/openram/bin/python)
#      PERIOD_NS   measure at this period, without the feasibility runs (a period
#                  too short fails the measurement run, which checks every read)
#      TRIM=1      OpenRAM's trimmed netlist
#      SPICE       ngspice (default, OpenRAM's reference for FreePDK45) or xyce. Xyce, as
#                  OpenRAM drives it, is faster but not usable here (run sram-char-xyce):
#                  on the whole 256 x 8 one-port netlist its access energies are within 4 %
#                  of ngspice's, but on the 512 x 8 one its leakage comes out at 3.5 mW
#                  and a write of a 0 draws 3.8 mW, artefacts
#      THREADS     OpenRAM's num_sim_threads (default 2; the MPI processes of xyce)
# Output: results/power/<label>/ (refuses to overwrite): char.json and summary.md
#         (summarize_sram_char.py, which explains them),
#         provenance.txt, and per macro the .lib and the log (compressed)

set -euo pipefail
label=${1:?usage: run_sram_char.sh <label> <macro ...>}
shift
macros=("$@")
[ ${#macros[@]} -gt 0 ] || { echo "no macro" >&2; exit 1; }
for m in "${macros[@]}"; do
  [[ $m =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)$ ]] || { echo "bad macro name $m" >&2; exit 1; }
done
PY=${OPENRAM_PY:-$HOME/venvs/openram/bin/python}
repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/power
out=$repo/results/power/$label
[ -e "$out" ] && { echo "$out exists; choose a new label" >&2; exit 1; }
mkdir -p "$out"
work=$(mktemp -d /tmp/btle_sramchar.XXXXXX)

unset OPENRAM_HOME
P=$("$PY" -c "import os, importlib.util; print(os.path.dirname(importlib.util.find_spec('openram').origin))")
export OPENRAM_TECH=$P/technology
period_arg=${PERIOD_NS:+--period $PERIOD_NS}
trim=False; [ "${TRIM:-0}" = 1 ] && trim=True
spice=${SPICE:-ngspice}; threads=${THREADS:-2}
case $spice in ngspice|xyce) ;; *) echo "SPICE must be ngspice or xyce" >&2; exit 1;; esac

{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git -C "$repo" rev-parse HEAD)"
  echo "openram=$("$PY" -c 'import importlib.metadata as m; print(m.version("openram"))' 2>/dev/null || true) ($P)"
  echo "simulator=$spice (num_sim_threads=$threads); OpenRAM's conda has: $("$P/miniconda/bin/ngspice" -v 2>/dev/null | grep -m1 -i 'revision' || true); $("$P/miniconda/bin/Xyce" -v 2>/dev/null | head -1 || true)"
  echo "tech=freepdk45, nominal corner only (TT, 1.0 V, 25 C), check_lvsdrc=False, netlist_only=True,"
  echo "     analytical_delay=False (SPICE), trim_netlist=$trim, load_scales=[1] slew_scales=[1],"
  if [ -n "${PERIOD_NS:-}" ]; then echo "     period: $PERIOD_NS ns, given"; else echo "     period: the feasible one"; fi
  echo "macros=${macros[*]}"
} > "$out/provenance.txt"

macro() {  # $1 = name
  [[ $1 =~ ^sram_(1rw|1rw1r)_([0-9]+)x([0-9]+)$ ]]
  local ports=${BASH_REMATCH[1]} ws=${BASH_REMATCH[2]} nw=${BASH_REMATCH[3]} d=$work/$1 nr=0
  [ "$ports" = 1rw1r ] && nr=1
  mkdir -p "$d"
  cat > "$d/cfg.py" <<EOF
word_size = $ws
num_words = $nw
num_rw_ports = 1
num_r_ports = $nr
num_w_ports = 0
tech_name = "freepdk45"
nominal_corner_only = True
process_corners = ["TT"]
supply_voltages = [1.0]
temperatures = [25]
check_lvsdrc = False
netlist_only = True
analytical_delay = False
trim_netlist = $trim
spice_name = "$spice"
num_sim_threads = $threads
load_scales = [1]
slew_scales = [1]
output_path = "$d/out"
output_name = "$1"
EOF
  if (cd "$d" && timeout 21600 "$PY" "$here/openram_char.py" cfg.py $period_arg) > "$out/$1.log" 2>&1 \
       && [ -s "$d/out/$1_TT_1p0V_25C.lib" ]; then
    cp "$d/out/$1_TT_1p0V_25C.lib" "$out/"
    echo "$1: done"
  else
    echo "$1: FAILED (see $1.log)"; return 1
  fi
}

pids=()
for m in "${macros[@]}"; do macro "$m" & pids+=($!); done
status=0
for p in "${pids[@]}"; do wait "$p" || status=1; done

python3 "$here/summarize_sram_char.py" "$out" "${macros[@]}" > "$out/summary.md" || status=1
cat "$out/summary.md"
gzip -9 "$out"/*.log "$out"/*.lib 2>/dev/null || true
rm -rf "$work"
exit $status
