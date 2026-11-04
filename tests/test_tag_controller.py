"""The tag through the controller's registers, as firmware/btle_ll.c drives it, against upstream's Python model.

Author: Miguel Simões

Runs tests/tag_controller_tb.v (btle_controller with baremetal_phy_intf_mode = 0, the boards' path:
the registers of btle_ll, the TX samples to the RF transceiver through clock_domain_conversion_iq)
for t = 8, 12, 18 and GAUSS_TABLE 0 and 1: several sensor readings, each sent on channels 37, 38 and
39 back to back, without a reset in between, as an advertising event does. For every packet, against
python/btlelib.py's btle_tx for the PDU of scripts/senseworks/tag_bch.py (the branch's AdvA and
Company ID):
- the PHY bits (after the CRC and the whitening) and the Gaussian filter's output: equal;
- the I/Q samples of btle_phy's output: equal for the first packet after the reset; for the others,
  the model's turned by one constant angle (the VCO's phase carries over from one packet to the next,
  the model starts each at 0; a GFSK receiver does not see it), within the 8-bit quantization;
- decoded by upstream's Python receiver (btle_rx): the CRC right and the PDU sent;
- the samples to the RF transceiver: the PHY's, one per rf_clk clock (see below);
and one packet per pulse of reg 9.

  python3 tests/test_tag_controller.py [--events N]
"""
import argparse
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from btlelib import btle_tx, btle_rx, bit_to_hex_string, gfsk_modulation_fixed_point, hex_string_to_bit, gauss_fir_gen  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402

MAX_TURN_SPREAD = 0.05   # rad: the spread of the angle between the RTL's and the model's samples


def per_packet(table: np.ndarray, p: int) -> np.ndarray:
    return table[table[:, 0] == p][:, 1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--events", type=int, default=3)
    a = parser.parse_args()
    cad = Path(os.environ.get("OSS_CAD", str(Path.home() / "eda/oss-cad-suite-20260907"))) / "bin"
    text = (ROOT / "verilog/btle_tx.v").read_text()
    adv = int(re.search(r"parameter \[47:0\] ADV_ADDRESS = 48'h([0-9a-fA-F_]+)", text).group(1), 16)
    cid = int(re.search(r"parameter \[15:0\] COMPANY_ID = 16'h([0-9a-fA-F]+)", text).group(1), 16)
    rng = random.Random(20261104)
    sensors = [bytes([0x12, 0x34])] + [rng.randbytes(2) for _ in range(a.events - 1)]
    taps = [int(v) for v in np.int8(np.round(128 * gauss_fir_gen()))][:9]
    files = [str(p) for p in sorted((ROOT / "verilog").glob("*.v")) if not p.name.endswith("_tb.v")
             and p.name not in {"btle_controller_wrapper.v", "sdpram_two_clk_xilinx.v"}]
    total, worst_spread = 0, 0.0
    offsets = [0, 0]
    with tempfile.TemporaryDirectory(prefix="tag-controller-") as temp:
        work = Path(temp)
        (work / "sensors.hex").write_text("".join(f"{b:02x}\n" for s in sensors for b in s))
        (work / "taps.hex").write_text("".join(f"{v & 0xffffffff:08x}\n" for v in taps))
        for t in tag_bch.TS:
            for g in (0, 1):
                sim = work / f"sim_t{t}_g{g}"
                subprocess.run([str(cad / "iverilog"), "-g2012", "-s", "tag_controller_tb", "-o", str(sim),
                                f"-DT={t}", f"-DG={g}", f"-DEVENTS={a.events}",
                                str(ROOT / "tests/tag_controller_tb.v"), *files],
                               check=True, capture_output=True, timeout=300)
                run = subprocess.run([str(cad / "vvp"), "-n", str(sim)], cwd=work, capture_output=True, text=True,
                                     timeout=3600)
                log = run.stdout + run.stderr
                if run.returncode or "PASS:" not in log:
                    raise RuntimeError(f"t={t} GAUSS_TABLE={g}: " + log[-1500:])
                tables = {n: np.loadtxt(work / f"{n}.txt", dtype=int, ndmin=2)
                          for n in ("phy_iq", "ext_iq", "phy_bits", "gauss")}
                for p in range(3 * a.events):
                    where = f"t={t} GAUSS_TABLE={g} packet {p}"
                    sensor, ch = sensors[p // 3], 37 + p % 3
                    packet = tag_bch.tag_pdu(adv, sensor, t, cid)
                    crc_init = hex_string_to_bit("555555")
                    i, q, bits, _ = btle_tx(hex_string_to_bit(packet.hex()), ch, crc_init, "D6BE898E")
                    _, gauss, _, _ = gfsk_modulation_fixed_point(bits)
                    got_bits = per_packet(tables["phy_bits"], p)[:, 0]
                    if not np.array_equal(got_bits, bits):
                        raise RuntimeError(f"{where}: the PHY bits differ from the model's")
                    got_gauss = per_packet(tables["gauss"], p)[:, 0] >> 1   # the VCO's input, as the model's
                    if not np.array_equal(got_gauss, gauss):
                        raise RuntimeError(f"{where}: the Gaussian filter's output differs from the model's")
                    got = per_packet(tables["phy_iq"], p)
                    if got.shape[0] != len(i):
                        raise RuntimeError(f"{where}: {got.shape[0]} samples, {len(i)} expected")
                    if p == 0 and not (np.array_equal(got[:, 0], i) and np.array_equal(got[:, 1], q)):
                        raise RuntimeError(f"{where}: the first packet's I/Q differ from the model's")
                    turn = np.angle((got[:, 0] + 1j * got[:, 1]) * np.conj(i + 1j * q))
                    turn = np.angle(np.exp(1j * (turn - turn[0])))
                    spread = float(np.max(np.abs(turn)))
                    worst_spread = max(worst_spread, spread)
                    if spread > MAX_TURN_SPREAD:
                        raise RuntimeError(f"{where}: the I/Q are not the model's turned by one angle ({spread:.3f} rad)")
                    decoded = btle_rx(got[:, 0], got[:, 1], ch, crc_init, "D6BE898E")
                    if not decoded[1] or bit_to_hex_string(decoded[0]) != packet.hex():
                        raise RuntimeError(f"{where}: upstream's receiver does not decode the PDU sent")
                    rf = per_packet(tables["ext_iq"], p)
                    # One RF sample per rf_clk clock while valid: the PHY's samples, in order. Upstream's
                    # clock_domain_conversion_iq registers the sample on rf_clk and stretches valid on bb_clk,
                    # without aligning the two: depending on the 2:1 phase at which the packet starts, the
                    # window of valid holds the PHY's samples (offset 0) or lags one sample (offset 1: the
                    # first RF sample the value held before the packet, the PHY's last one after the window).
                    if rf.shape[0] != len(i):
                        raise RuntimeError(f"{where}: {rf.shape[0]} RF samples, {len(i)} PHY")
                    if np.array_equal(rf, got):
                        offsets[0] += 1
                    elif np.array_equal(rf[1:], got[:-1]):
                        offsets[1] += 1
                    else:
                        raise RuntimeError(f"{where}: the RF samples are not the PHY's")
                    total += 1
                print(f"t = {t:2}, GAUSS_TABLE = {g}: {3 * a.events} packets through the registers (channels 37, "
                      f"38, 39): bits and Gaussian output equal to the model's, I/Q the model's (turned), decoded "
                      f"with the CRC right, RF samples the PHY's, one packet per pulse", flush=True)
    print(f"PASS: {total} packets; widest turn spread {worst_spread:.4f} rad; RF window at offset 0: {offsets[0]}, "
          f"lagging one sample: {offsets[1]}")


if __name__ == "__main__":
    main()
