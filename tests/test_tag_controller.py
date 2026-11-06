"""The tag of ble-tx-poc-tmp100 in the controller, the boards' path, against upstream's Python model: no firmware in the data path.

Author: Miguel Simões

Runs tests/tag_controller_tb.v: btle_controller with the model of the TMP100 on its I2C bus; off until the firmware's one
write, the rate (register 7), no packet before it; the other AXI-lite registers are only read (the tag's state,
registers 42 to 46), but for the writes that sent a packet on the earlier branches, which must change nothing. For t = 8,
12, 18, every packet, against python/btlelib.py's btle_tx for the PDU of scripts/senseworks/tag_bch.py (TxAdd 1):
- the sensor's two bytes: the temperature the model converted, at 9 bits;
- the PHY bits (after the CRC and the whitening) and the Gaussian filter's output: equal;
- the I/Q samples of btle_phy's output: equal for the first packet after the reset; for the others, the model's
  turned by one constant angle (the VCO's phase carries over from one packet to the next, the model starts each at 0;
  a GFSK receiver does not see it), within the 8-bit quantization;
- decoded by upstream's Python receiver (btle_rx): the CRC right and the PDU sent;
- the samples to the RF transceiver: the PHY's, one per rf_clk clock (see below);
- the registers: the sensor, the channel, TxAdd, the packets counted, none with no reading, AdvA, the rate.

  python3 tests/test_tag_controller.py [--events N]
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from btlelib import btle_tx, btle_rx, bit_to_hex_string, gfsk_modulation_fixed_point, hex_string_to_bit  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402

MAX_TURN_SPREAD = 0.05   # rad: the spread of the angle between the RTL's and the model's samples
ADV = 0xC10203040506     # btle_controller's ADV_ADDRESS
CHANNEL = 38
TICK_DIV = 25            # the tag's speed times 19.5: every time in the model divided by that
RATE = 1                 # 125 ms
TIME_SCALE = (1.0e9 / 32768) / (TICK_DIV * 62.5)


def per_packet(table: np.ndarray, p: int) -> np.ndarray:
    return table[table[:, 0] == p][:, 1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--events", type=int, default=3)
    a = parser.parse_args()
    cad = Path(os.environ.get("OSS_CAD", str(Path.home() / "eda/oss-cad-suite-20260907"))) / "bin"
    temps = [25.0, -3.5, 40.0, 18.0, 19.0][:a.events]
    files = [str(p) for p in sorted((ROOT / "verilog").glob("*.v")) if not p.name.endswith("_tb.v")
             and p.name not in {"btle_controller_wrapper.v", "sdpram_two_clk_xilinx.v"}]
    models = [str(ROOT / "tests" / f) for f in ("tag_controller_tb.v", "i2c_slave_model.v", "tmp100_model.v")]
    total, worst_spread = 0, 0.0
    offsets = [0, 0]
    with tempfile.TemporaryDirectory(prefix="tag-controller-") as temp:
        work = Path(temp)
        (work / "temps.hex").write_text("".join(f"{round(t * 16) & 0xFFFF:04x}\n" for t in temps))
        for t in (8, 12, 18):
            sim = work / f"sim_t{t}"
            subprocess.run([str(cad / "iverilog"), "-g2012", "-s", "tag_controller_tb", "-o", str(sim),
                            f"-DT={t}", f"-DTICK_DIV={TICK_DIV}", f"-DEVENTS={a.events}", f"-DCH={CHANNEL}", f"-DRATE={RATE}",
                            *models, *files],
                           check=True, capture_output=True, timeout=300)
            run = subprocess.run([str(cad / "vvp"), "-n", str(sim), f"+time_scale={TIME_SCALE}"], cwd=work, capture_output=True,
                                 text=True, timeout=3600)
            log = run.stdout + run.stderr
            if run.returncode or "PASS:" not in log:
                raise RuntimeError(f"t={t}: " + log[-1500:])
            tables = {n: np.loadtxt(work / f"{n}.txt", dtype=int, ndmin=2)
                      for n in ("phy_iq", "ext_iq", "phy_bits", "gauss")}
            status = [line.split() for line in (work / "status.txt").read_text().splitlines()]
            for p in range(a.events):
                where = f"t={t} packet {p}"
                # the first packet carries the last continuous conversion, of the first temperature
                temperature = temps[max(p - 1, 0)]
                raw = ((round(temperature * 16) << 4) & 0xFFFF) & 0xFF80    # 9 bits, the rest of the register 0
                packet = tag_bch.tag_pdu(ADV, raw.to_bytes(2, "big"), t, tag_bch.DEFAULT_COMPANY_ID, 1)
                crc_init = hex_string_to_bit("555555")
                i, q, bits, _ = btle_tx(hex_string_to_bit(packet.hex()), CHANNEL, crc_init, "D6BE898E")
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
                decoded = btle_rx(got[:, 0], got[:, 1], CHANNEL, crc_init, "D6BE898E")
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
                # the registers (docs/Architecture/LL_REGISTER_MAP.md)
                reg42, reg43, reg44, reg45, reg46 = (int(v, 16) for v in status[p][1:])
                want42 = raw | (CHANNEL << 16) | (1 << 23)
                if reg42 != want42 or reg43 != p + 1 or reg44 != 0:
                    raise RuntimeError(f"{where}: registers 42..44 {reg42:08x} {reg43} {reg44}, expected {want42:08x} {p + 1} 0")
                if reg45 != ADV & 0xFFFFFFFF or reg46 != (ADV >> 32) | (RATE << 16):
                    raise RuntimeError(f"{where}: registers 45, 46 {reg45:08x} {reg46:08x}")
                total += 1
            print(f"t = {t:2}: {a.events} packets, off until the rate is written (channel {CHANNEL}): bits and "
                  f"Gaussian output equal to the model's, I/Q the model's (turned), decoded with the CRC right, RF samples "
                  f"the PHY's, the registers right", flush=True)
    print(f"PASS: {total} packets; widest turn spread {worst_spread:.4f} rad; RF window at offset 0: {offsets[0]}, "
          f"lagging one sample: {offsets[1]}")


if __name__ == "__main__":
    main()
