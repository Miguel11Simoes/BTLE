#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Gate-level netlist of btle_controller for switching-activity simulation.
# Same mapping as scripts/area/run_area.sh (synth, dfflibmap, abc -liberty on
# Nangate45, RAMs as blackbox macros). Flattened inside each block, but the
# block boundaries measured separately are kept (keep_hierarchy on btle_rx,
# btle_tx, gauss_filter, btle_ll, auxiliary_daemon, clock_domain_conversion_iq),
# so that
# activity can be attributed to blocks by instance path.
#
# Usage: synth_gate_netlist.sh <rtl-dir> <out.v> <module-suffix> [NAME=VALUE ...]
#   <module-suffix> is appended to every non-RAM module name ("" for none), so
#   two netlists can be simulated side by side.

set -euo pipefail
rtl=${1:?rtl dir}; out=${2:?output netlist}; suffix=${3-}; shift 3 || true
OSS_CAD=${OSS_CAD:-$HOME/eda/oss-cad-suite-20260907}
LIBERTY=${LIBERTY:-$HOME/eda/NangateOpenCellLibrary_typical.lib}
export PATH=$OSS_CAD/bin:$PATH

files=$(cd "$rtl" && ls *.v | grep -v '_tb\.v$' | grep -v '^btle_controller_wrapper' \
        | grep -vx -e sdpram_one_clk.v -e sdpram_two_clk.v -e sdpram_two_clk_xilinx.v | sed "s|^|$rtl/|" | tr '\n' ' ')
chp=""; for kv in "$@"; do chp="$chp -chparam ${kv%%=*} ${kv#*=}"; done

yosys -q -l "$out.log" -p "
read_verilog -lib $rtl/sdpram_one_clk.v $rtl/sdpram_two_clk.v
read_verilog $files
hierarchy -check -top btle_controller$chp
setattr -mod -set keep_hierarchy 1 *btle_rx *btle_tx *gauss_filter *btle_ll *auxiliary_daemon *clock_domain_conversion_iq
synth -flatten -top btle_controller
dfflibmap -liberty $LIBERTY
abc -liberty $LIBERTY
opt_clean -purge
rename -enumerate
tee -o $out.stat stat -liberty $LIBERTY
write_verilog -noattr $out.raw.v
"
# Give the parameterised modules plain names and add the suffix, so that the
# netlist is ordinary Verilog and two of them can coexist.
python3 - "$out.raw.v" "$out" "$suffix" <<'EOF'
import re, sys
src, dst, suffix = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
names = sorted(set(re.findall(r'^module\s+(\\\S+|\w+)', s, re.M)))
ram = re.compile(r'^\\?sdpram_')
mapping, used = {}, set()
for n in names:
    if ram.match(n):
        continue
    base = re.sub(r'^\\\$paramod\$[0-9a-f]+\\', '', n)       # \$paramod$<hash>\name
    base = re.sub(r'[^A-Za-z0-9_]', '_', base.lstrip('\\'))
    new, k = base + suffix, 1
    while new in used:
        new = f"{base}_v{k}{suffix}"; k += 1
    used.add(new); mapping[n] = new
def sub(m):
    name = m.group(0)
    return mapping.get(name.strip(), name)
for old, new in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
    if old.startswith('\\'):
        s = s.replace(old + ' ', new + ' ')
    else:
        s = re.sub(r'\b' + re.escape(old) + r'\b', new, s)
open(dst, 'w').write(s)
print(f"{len(mapping)} modules renamed")
EOF
