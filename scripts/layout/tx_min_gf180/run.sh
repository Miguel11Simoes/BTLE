#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# Layout of btle_tx (ble-tx-min, GAUSS_TABLE=1 ADV_DATA_FLOPS=1 ADV_ADDRESS_OTP=1) in GF180MCU-D with the
# six eFuse blocks of AdvA, LibreLane Classic flow in the Nix environment of the GF180MCU eFuse compiler.
#
# Usage (WSL/Linux, repository root): scripts/layout/tx_min_gf180/run.sh <label> [rtl-rev] [flops|sram64]
#   flops (default): AdvData in 31 bytes of flip-flops (ADV_DATA_FLOPS=1), config.json
#   sram64: AdvData in the PDK's SRAM gf180mcu_fd_ip_sram__sram64x8m8wm1 (ADV_DATA_FLOPS=0, 32 of its
#           64 words), config_sram64.json: pdu_buffer_ram of btle_tx.v replaced by pdu_buffer_ram_gf180.v
# Needs: EFUSE_DIR (default ~/eda/efuse) with gf180_efuse_compiler/ (its nix-shell, the wafer.space PDK
# in gf180mcu/) and out/macros/efuse_array_async_1x8/ from `./efuse.py 1 8 --async-efuse
# --digital-wrapper=async` (results/otp/gf180-efuse/provenance.txt); docker with the nixstore volume.
# Output: $EFUSE_DIR/out/<label>/ (the LibreLane run), then copied to results/layout/<label>/.
set -euo pipefail
label=${1:?usage: run.sh <label> [rtl-rev]}
rev=${2:-HEAD}
variant=${3:-flops}
case $variant in flops|sram64) ;; *) echo "variant: flops or sram64" >&2; exit 1;; esac
EFUSE_DIR=${EFUSE_DIR:-$HOME/eda/efuse}
repo=$(git rev-parse --show-toplevel)
here=$repo/scripts/layout/tx_min_gf180
work=$EFUSE_DIR/out/$label
[ -e "$work" ] && { echo "$work exists; choose a new label" >&2; exit 1; }
[ -e "$repo/results/layout/$label" ] && { echo "results/layout/$label exists" >&2; exit 1; }
mkdir -p "$work/src"
git -C "$repo" archive "$rev" verilog | tar -x -C "$work/src" --strip-components=1
git -C "$repo" rev-parse "$rev^{commit}" > "$work/rtl_commit.txt"
cp "$here/btle_tx.sdc" "$here/render.py" "$work/"; cat "$here/btle_tx.sdc" "$here/btle_tx_pnr_extra.sdc" > "$work/btle_tx_pnr.sdc"
if [ "$variant" = sram64 ]; then
  cp "$here/config_sram64.json" "$work/config.json"; cp "$here/pdn_cfg.tcl" "$work/"
  awk '/^module pdu_buffer_ram/{skip=1} !skip{print} skip&&/^endmodule/{skip=0}' "$work/src/btle_tx.v" > "$work/btle_tx.v"
  mv "$work/btle_tx.v" "$work/src/btle_tx.v"; cp "$here/pdu_buffer_ram_gf180.v" "$work/src/"
  grep -q "^module pdu_buffer_ram" "$work/src/btle_tx.v" && { echo "pdu_buffer_ram not removed" >&2; exit 1; }
else
  cp "$here/config.json" "$work/"
fi

# the compiler's nix-shell, as its own flow runs it (results/otp/gf180-efuse/provenance.txt)
in_nix() {
  docker run --rm -v nixstore:/nix -v "$EFUSE_DIR/gf180_efuse_compiler":/work -v "$EFUSE_DIR/out":/out nixos/nix:latest sh -c "
    cp /work/nix.conf /etc/nix/nix.conf
    mkdir -p /src && cp -a /work/. /src/ && cd /src && chown -R root:root /src
    mkdir -p /src/.bin && printf '#!/bin/sh\necho \" total   100000K\"\n' > /src/.bin/pmap && chmod +x /src/.bin/pmap
    nix-shell --run 'export PATH=/src/.bin:\$PATH; $1'"
}
L=/src/gf180mcu/gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyp
fig=tx_min_gf180; [ "$variant" = sram64 ] && fig=tx_min_gf180_sram64
in_nix "cd /out/$label && librelane --pdk-root /src/gf180mcu --pdk gf180mcuD --manual-pdk config.json > librelane.log 2>&1; echo \$? > librelane.exit
  G=\$(ls -d runs/RUN_*/final/gds | tail -1)/btle_tx.gds; export QT_QPA_PLATFORM=offscreen
  python3 render.py \$G $L ${fig}_gds.png 1600
  python3 render.py \$G $L ${fig}_efuse.png 1400 20 30 250 135
  python3 render.py \$G $L ${fig}_efuse_pdn.png 1400 20 30 250 135 Metal4,Metal5,Via4
  chmod -R a+rwX /out/$label"
[ "$(cat "$work/librelane.exit")" = 0 ] || { tail -40 "$work/librelane.log"; exit 1; }

# sram64: Magic's deck flags the GlobalFoundries SRAM's own layout (ERROR_ON_MAGIC_DRC is off); the
# foundry's KLayout deck is the signoff. Every Magic error must lie inside the SRAM, none elsewhere.
if [ "$variant" = sram64 ]; then
  python3 - "$work/config.json" "$(ls -d "$work"/runs/RUN_* | tail -1)" <<'PY'
import glob, json, re, sys
c = json.load(open(sys.argv[1]))
(x, y), = [v['location'] for m in c['MACROS'].values() for k, v in m['instances'].items() if k.endswith('sram_i')]
box = (x, y, x + 431.86, y + 232.88)          # gf180mcu_fd_ip_sram__sram64x8m8wm1, LEF SIZE
rpt = open(glob.glob(sys.argv[2] + '/*-magic-drc/reports/drc.magic.rpt')[0]).read()
rects = [tuple(map(float, r)) for r in re.findall(r'^\s*([-\d.]+)um ([-\d.]+)um ([-\d.]+)um ([-\d.]+)um', rpt, re.M)]
out = [r for r in rects if not (box[0] <= r[0] and r[2] <= box[2] and box[1] <= r[1] and r[3] <= box[3])]
k = re.search(r'COUNT: (\d+)', rpt)
print(f"Magic DRC: {k.group(1) if k else '?'} errors, {len(rects)} located, {len(out)} outside the SRAM {box}")
sys.exit(1 if out or not rects and k and int(k.group(1)) else 0)
PY
fi

# keep the signoff evidence (not the whole run)
R=$(ls -d "$work"/runs/RUN_* | tail -1)
out=$repo/results/layout/$label; mkdir -p "$out/sta"
cp "$work"/{config.json,btle_tx.sdc,btle_tx_pnr.sdc,rtl_commit.txt} "$R/resolved.json" "$R"/final/metrics.{json,csv} "$out/"
cp "$R"/*-misc-reportmanufacturability/manufacturability.rpt "$R"/*-openroad-irdropreport/irdrop.rpt "$out/"
for c in "$R"/*-openroad-stapostpnr/*/; do n=$(basename "$c"); cp "$c/summary.rpt" "$out/sta/$n.summary.rpt" 2>/dev/null || true
  cp "$c/checks.rpt" "$out/sta/$n.checks.rpt"; cp "$c/max.rpt" "$out/sta/$n.max.rpt"; cp "$c/min.rpt" "$out/sta/$n.min.rpt"; done
cp "$R"/*-magic-drc/reports/* "$R"/*-klayout-drc/reports/* "$R"/*-netgen-lvs/reports/* "$out/" 2>/dev/null || true
cp "$work/librelane.log" "$R/warning.log" "$out/"
gzip -9 -c "$R/final/gds/btle_tx.gds" > "$out/btle_tx.gds.gz"
gzip -9 -c "$R/final/nl/btle_tx.nl.v" > "$out/btle_tx.nl.v.gz"
gzip -9 "$out"/sta/*.rpt "$out"/librelane.log
mkdir -p "$repo/results/figures/tx-min"; cp "$work"/${fig}_*.png "$repo/results/figures/tx-min/"
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "rtl=$rev ($(cat "$work/rtl_commit.txt")), btle_tx, variant $variant: $(grep -o '"SYNTH_PARAMETERS": \[[^]]*\]' "$work/config.json")"
  echo "harness=$(git -C "$repo" rev-parse HEAD), dirty files under scripts/layout: $(git -C "$repo" status --porcelain -- scripts/layout | wc -l)"
  echo "flow=LibreLane Classic, gf180mcuD, gf180mcu_fd_sc_mcu7t5v0, in the eFuse compiler's nix-shell ($(git -C "$EFUSE_DIR/gf180_efuse_compiler" rev-parse HEAD 2>/dev/null))"
  echo "run=$(basename "$R")"
  echo "gds sha256=$(sha256sum "$R/final/gds/btle_tx.gds" | cut -d' ' -f1)"
} > "$out/provenance.txt"
cat "$out/manufacturability.rpt"
