#!/usr/bin/env bash
# Author: Miguel Simões
# SPDX-FileCopyrightText: 2026 Miguel Simões
# SPDX-License-Identifier: Apache-2.0
#
# The senseworks tag (ble-tx-tag-*, 2026-11-04): config.json lays out btle_tx with GAUSS_TABLE=1
# ADV_ADDRESS_OTP=1 and the branch's BCH_T (its default); no AdvData memory, so no sram64 variant.
# From ble-tx-min:
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
# The settings of both configurations, for a flow without unreviewed warnings (the receiver's layout,
# scripts/layout/rx_final_gf180 of ble-rx-micro; scripts/validation/synth_warning_gate.py --librelane):
#   PAD_* empty and LIB the standard cells only: btle_tx is a macro, without pads, so the PDK's I/O
#     cells (which the PDK's configuration adds) are not loaded and the flow does not warn about them;
#   RUN_HEURISTIC_DIODE_INSERTION false: each heuristic diode is a load that pushes its net over the
#     max fanout; the antenna repair after global routing (GRT_ANTENNA_REPAIR_*) leaves no violation;
#   WIRE_LENGTH_THRESHOLD: the long-wire check runs; GPL_CELL_PADDING: a site around each cell;
#   STA_MACRO_PRIORITIZE_NL false: the macros (eFuse blocks, SRAM) are timed by their liberties, as
#     no parasitics come with their netlists.
# And of this transmitter (the experiments of TX_FINAL_DECISIONS.md section 8.1):
#   eFuse blocks 1 and 5 at x = 141.56 and 622.36 (were 146, 618): the core's straps (VDD, then VSS
#     3.3 um apart) on the block's own Metal4 pins (VDD at 14.28 + 20k um, VSS 3.3 um after); between
#     them a strap of one net met a pin of the other, was cut, and its end overlapped the block's
#     ring by less than a via (PDN-0110);
#   the SRAM at (124.6, 480) (was 164, 500): no vertical strap crosses its 0.11 um high VSS rail on
#     Metal3 (x 118.4-207.0 um of the macro, its LEF) or ends on the edge of one of its shapes (PDN-0110),
#     with room above it for the buffers of the top edge's pins;
#   IO_EXCLUDE_PIN_REGION bottom:* (SRAM): the eFuse row is along the bottom edge; with pins there the
#     logic that reads them is placed in the strip below the row, and a net of the AdvA multiplexer
#     detoured there over the max slew at ss (the flip-flops' placement does not; their setup slack
#     falls to 0.2 ns with it);
#   DESIGN_REPAIR_MAX_SLEW_PCT 60 (both; the SRAM's already): the repair's margin on the max slew;
#   CTS_SINK_CLUSTERING 7 flip-flops over 150 um: the fewest clock-tree buffers above the max fanout.
# And of the tag (2026-11-04): RUN_POST_GRT_DESIGN_REPAIR true: the reset net (rst, on the BCH LFSR's flip-flops
#   too) left the repair after placement at 3.2-3.3 ns of slew at ss, over the 3 ns max; repaired again
#   with the global route's parasitics; aoi221_1 excluded as ble-tx-min excluded aoi222_1: one, in the AdvA
#   multiplexer, then drove the only net over the max slew at ss (t = 18, by 1.3 ps); IO_EXCLUDE_PIN_REGION
#   bottom:* (as the SRAM variant): a quarter of the pins fell on the bottom edge, below the eFuse row, and
#   their wires to the input buffers went over the max slew at ss (t = 8, up to 4.8 ns).
set -euo pipefail
label=${1:?usage: run.sh <label> [rtl-rev]}
rev=${2:-HEAD}
variant=${3:-flops}
case $variant in flops) ;; *) echo "variant: flops (the senseworks tag has no AdvData memory: no sram64)" >&2; exit 1;; esac
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

# CONFIG_OVERRIDES (optional): a JSON object merged into config.json (objects key by key, the rest replaced),
# to try a setting without editing the configuration; recorded in provenance.txt
if [ -n "${CONFIG_OVERRIDES:-}" ]; then
  python3 - "$work/config.json" <<'PY'
import json, os, sys
def merge(a, b):
    for k, v in b.items():
        a[k] = merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a
c = json.load(open(sys.argv[1]))
json.dump(merge(c, json.loads(os.environ['CONFIG_OVERRIDES'])), open(sys.argv[1], 'w'), indent=2)
PY
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
fig=$(echo "$label" | tr - _)   # the tag: the renders named after the run, in results/figures/tx-tag
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
msg = f"Magic DRC: {k.group(1) if k else '?'} errors, {len(rects)} located, {len(out)} outside the SRAM {box}"
print(msg)
open(sys.argv[2] + '/../../magic_drc_sram.txt', 'w').write(msg + chr(10))
sys.exit(1 if out or not rects and k and int(k.group(1)) else 0)
PY
fi

# keep the signoff evidence (not the whole run)
R=$(ls -d "$work"/runs/RUN_* | tail -1)
out=$repo/results/layout/$label; mkdir -p "$out/sta"
cp "$work"/{config.json,btle_tx.sdc,btle_tx_pnr.sdc,rtl_commit.txt} "$R/resolved.json" "$R"/final/metrics.{json,csv} "$out/"
[ -e "$work/magic_drc_sram.txt" ] && cp "$work/magic_drc_sram.txt" "$out/"
cp "$R"/*-misc-reportmanufacturability/manufacturability.rpt "$R"/*-openroad-irdropreport/irdrop.rpt "$out/"
for c in "$R"/*-openroad-stapostpnr/*/; do n=$(basename "$c"); cp "$c/summary.rpt" "$out/sta/$n.summary.rpt" 2>/dev/null || true
  cp "$c/checks.rpt" "$out/sta/$n.checks.rpt"; cp "$c/max.rpt" "$out/sta/$n.max.rpt"; cp "$c/min.rpt" "$out/sta/$n.min.rpt"; done
cp "$R"/*-magic-drc/reports/* "$R"/*-klayout-drc/reports/* "$R"/*-netgen-lvs/reports/* "$out/" 2>/dev/null || true
cp "$work/librelane.log" "$R/warning.log" "$out/"
gzip -9 -c "$R/final/gds/btle_tx.gds" > "$out/btle_tx.gds.gz"
gzip -9 -c "$R/final/nl/btle_tx.nl.v" > "$out/btle_tx.nl.v.gz"
gzip -9 "$out"/sta/*.rpt "$out"/librelane.log
mkdir -p "$repo/results/figures/tx-tag"; cp "$work"/${fig}_*.png "$repo/results/figures/tx-tag/"
{
  echo "label=$label"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "rtl=$rev ($(cat "$work/rtl_commit.txt")), btle_tx, variant $variant: $(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["SYNTH_PARAMETERS"]))' "$work/config.json")"
  echo "harness=$(git -C "$repo" rev-parse HEAD), dirty files under scripts/layout: $(git -C "$repo" status --porcelain -- scripts/layout | wc -l)"
  echo "flow=LibreLane Classic, gf180mcuD, gf180mcu_fd_sc_mcu7t5v0, in the eFuse compiler's nix-shell ($(git -C "$EFUSE_DIR/gf180_efuse_compiler" rev-parse HEAD 2>/dev/null))"
  echo "run=$(basename "$R")"
  echo "config_overrides=${CONFIG_OVERRIDES:-none}"
  echo "gds sha256=$(sha256sum "$R/final/gds/btle_tx.gds" | cut -d' ' -f1)"
} > "$out/provenance.txt"
cat "$out/manufacturability.rpt"
