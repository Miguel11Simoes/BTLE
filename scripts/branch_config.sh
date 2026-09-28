#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Prints the configuration a branch is measured in: every optional area
# reduction that its btle_controller declares, switched on.
#
#   A1  ENABLE_IQ_CAPTURE=0   no diagnostic IQ-capture RAM
#   A2  LL_MINIMAL=1          minimal Link Layer (no UART HCI, 1 PPS, debug registers)
#   B2  GAUSS_TABLE=1         fixed-tap Gaussian table instead of the runtime FIR
#
# B1 (the shared demodulator) is not a parameter: a branch has it in its RTL or
# not. So upstream-baseline and ble-rx-dm print nothing, ble-tx-table prints
# "GAUSS_TABLE=1", and ble-opt prints all three, in the order above.
#
# Usage: scripts/branch_config.sh <verilog-dir>

set -euo pipefail
rtl=${1:?usage: branch_config.sh <verilog-dir>}
[ -f "$rtl/btle_controller.v" ] || { echo "no btle_controller.v in $rtl" >&2; exit 1; }

# parameter names declared in the header of btle_controller (as run_area.sh reads them)
declared=$(awk '$0 ~ "^[[:space:]]*module[[:space:]]+btle_controller([^a-zA-Z0-9_]|$)" {f=1}
                f && /parameter/ {for (i=1;i<=NF;i++) if ($i ~ /^[A-Za-z_][A-Za-z0-9_]*$/ && $(i+1) == "=") print $i}
                f && /^[[:space:]]*\)[[:space:]]*\(/ {exit}' "$rtl/btle_controller.v")
params=""
for kv in ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1; do
  if grep -qx "${kv%%=*}" <<< "$declared"; then params="$params $kv"; fi
done
echo "${params# }"
