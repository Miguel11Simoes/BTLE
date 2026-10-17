#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The transmitter with its AdvData memory on the GF180MCU SRAM (variant sram64 of run.sh), against master
# (tests/test_tx_min.py: every output on every clock, four builds, six clkb frequencies, and --mutants),
# with GlobalFoundries' simulation model of gf180mcu_fd_ip_sram__sram64x8m8wm1 (fetched at a fixed commit;
# the PDK's copy of the model is empty). pdu_buffer_ram_gf180_sim.v is pdu_buffer_ram_gf180.v with the
# macro's inputs held 1 ns: the model samples them 100 ps after the clock, zero-delay RTL changes them at
# the clock; the layout's hold repair gives them their hold (the Liberty's 0.5-1.1 ns).
#
# Usage (WSL/Linux, repository root): scripts/layout/tx_min_gf180/sim_sram64.sh [ref-rev] [extra test_tx_min args]
set -euo pipefail
ref=${1:-fca6ac64fb28cd57a496cb45af62cf9e0f9209d5}; shift || true
repo=$(git rev-parse --show-toplevel); here=$repo/scripts/layout/tx_min_gf180
SRAM_REPO=https://github.com/google/globalfoundries-pdk-ip-gf180mcu_fd_ip_sram.git
SRAM_REV=9c41192
work=$(mktemp -d /tmp/btle_sram64.XXXXXX)
git clone -q "$SRAM_REPO" "$work/ip" && git -C "$work/ip" checkout -q "$SRAM_REV"
model=$work/ip/cells/gf180mcu_fd_ip_sram__sram64x8m8wm1/gf180mcu_fd_ip_sram__sram64x8m8wm1.v
git clone -q "$repo" "$work/tree"; cd "$work/tree"; git checkout -q "$(git -C "$repo" rev-parse HEAD)"
git branch -q -f master "$(git -C "$repo" rev-parse "$ref")" 2>/dev/null || true
F=verilog/btle_tx.v
awk '/^module pdu_buffer_ram/{skip=1} !skip{print} skip&&/^endmodule/{skip=0}' $F > "$work/btle_tx.v"
{ cat "$work/btle_tx.v"; cat "$here/pdu_buffer_ram_gf180_sim.v"; echo; tr '\r' '\n' < "$model"; } > $F
echo "model $SRAM_REPO $SRAM_REV sha256 $(sha256sum "$model" | cut -c1-16)"
"${PY:-python3}" tests/test_tx_min.py --jobs "${JOBS:-16}" --ref-rev "$ref" "$@"
