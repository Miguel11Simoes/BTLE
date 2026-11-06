"""The tag's whole TX waveform against upstream's Python model, its loopback through upstream's receiver and its BCH code.

Author: Miguel Simões

For t = 8, 12 and 18, one and two bytes of sensor, channels 37, 38, 39
(advertising) and 0, 10 (other whitening), the sensor all 0s, all 1s and random
values, TxAdd 0 and 1, and both Gaussian filters (GAUSS_TABLE 0 with the taps
loaded, 1 with the fixed taps): the RTL btle_tx under upstream's TX testbench
(verilog/btle_tx_tb.v, which puts AdvA, TxAdd and the sensor of the PDU on the
tag's ports), against python/btlelib.py's btle_tx for the PDU of
scripts/senseworks/tag_bch.py:
- every I and Q sample equal (upstream's testbench check, and again here);
- upstream's Python receiver (btle_rx, no noise) decodes the RTL's waveform with
  the CRC right and returns that PDU;
- the PDU received is a codeword of the BCH code (decoding it changes nothing),
  and with t bit errors at random among AdvA, the sensor and the parity it is
  decoded back to the PDU sent; with t + 1 errors the decoder does not return
  the PDU sent as if it had been sent (it finds no codeword, or another one);
- the packets (access address, PDU, CRC) are written to --output (JSON) for
  scripts/senseworks/check_tag_scapy.py, an independent parser.

  python3 tests/test_tx_tag_packet.py [--output FILE]
"""
import argparse
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from btlelib import btle_tx, btle_rx, hex_string_to_bit, bit_to_hex_string, gauss_fir_gen, sin_cos_gen, crc24_core  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/validation"))
from result_guard import bad_lines  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402

ACCESS_ADDRESS = "D6BE898E"   # 0x8E89BED6 as btlelib takes it (advertising channels)
DATA_ACCESS_ADDRESS = "1B0A8560"  # the other channels, as tests/test_tx_packet.py (btlelib picks the preamble from it)
CRC_INIT = "555555"


def set_default(text: str, param: str, value: int) -> str:
    out, n = re.subn(r"(parameter integer " + re.escape(param) + r" = )\d+", r"\g<1>" + str(value), text)
    if n != 1:
        raise RuntimeError(f"parameter {param} not found once")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--random-sensors", type=int, default=3)
    a = parser.parse_args()
    cad = Path(os.environ.get("OSS_CAD", str(Path.home() / "eda/oss-cad-suite-20260907"))) / "bin"
    rng = random.Random(20261104)
    channels = (37, 38, 39, 0, 10)
    rows = []
    with tempfile.TemporaryDirectory(prefix="btle-tx-tag-packet-") as temp:
        work = Path(temp)
        adv = 0xC10203040506                 # a random static address
        vectors = work / "vectors"
        vectors.mkdir()
        taps = np.int8(np.round(128 * gauss_fir_gen()))
        cos, sin = sin_cos_gen(64)
        for name, data in [("gauss_filter_tap", taps), ("cos_table", cos), ("sin_table", sin)]:
            np.savetxt(vectors / (name + ".txt"), data, fmt="%d")
        for t, s in ((t, s) for t in tag_bch.TS for s in tag_bch.SENSOR_SIZES):
            sensors = [bytes(s), bytes([0xff] * s)] + [rng.randbytes(s) for _ in range(a.random_sensors)]
            for gauss_table in (0, 1):
                rtl = work / f"rtl_t{t}_s{s}_g{gauss_table}"
                shutil.copytree(ROOT / "verilog", rtl, ignore=shutil.ignore_patterns("*.txt", "*.vcd"))
                tb = rtl / "btle_tx_tb.v"
                tb.write_text(set_default(re.sub(r"^\s*\$dump(?:file|vars)\b[^;]*;", "", tb.read_text(), flags=re.M),
                                          "SENSOR_BYTES", s))
                f = rtl / "btle_tx.v"
                f.write_text(set_default(set_default(f.read_text(), "BCH_T", t), "GAUSS_TABLE", gauss_table))
                files = [str(p) for p in rtl.glob("*.v") if not p.name.endswith("_tb.v")
                         and p.name not in {"btle_controller_wrapper.v", "sdpram_two_clk_xilinx.v"}]
                sim = work / f"sim_t{t}_s{s}_g{gauss_table}"
                subprocess.run([str(cad / "iverilog"), "-s", "btle_tx_tb", "-o", str(sim), str(tb), *files],
                               check=True, capture_output=True, timeout=120)
                for ch in channels:
                    for index, sensor in enumerate(sensors):
                        tx_add = index % 2
                        packet = tag_bch.tag_pdu(adv, sensor, t, tx_add=tx_add)
                        pdu = hex_string_to_bit(packet.hex())
                        aa = ACCESS_ADDRESS if ch >= 37 else DATA_ACCESS_ADDRESS
                        crc_init = hex_string_to_bit(CRC_INIT)
                        i, q, _, _ = btle_tx(pdu, ch, crc_init, aa)
                        (vectors / "btle_config.txt").write_text(f"{len(pdu):x}\n{ch:x}\n{CRC_INIT}\n{aa}\n")
                        (vectors / "btle_tx_test_input.txt").write_text("".join(f"{v:02x}\n" for v in packet))
                        for name, data in [("i", i), ("q", q)]:
                            np.savetxt(vectors / f"btle_tx_test_output_{name}_ref.txt", data, fmt="%d")
                        run = subprocess.run([str(cad / "vvp"), "-n", str(sim)], cwd=vectors, capture_output=True,
                                             text=True, timeout=60)
                        log = run.stdout + run.stderr
                        if run.returncode or bad_lines(log) or not all(f"output {c} Test PASS." in log for c in "IQ"):
                            raise RuntimeError(f"TX t={t} S={s} GAUSS_TABLE={gauss_table} channel={ch} sensor={sensor.hex()} "
                                               f"exit={run.returncode}: " + log[-2500:])
                        actual_i = np.loadtxt(vectors / "btle_tx_test_output_i.txt", dtype=np.int16)
                        actual_q = np.loadtxt(vectors / "btle_tx_test_output_q.txt", dtype=np.int16)
                        np.testing.assert_array_equal(actual_i, i)
                        np.testing.assert_array_equal(actual_q, q)
                        decoded = btle_rx(actual_i, actual_q, ch, crc_init, aa)
                        if not decoded[1] or bit_to_hex_string(decoded[0]) != packet.hex():
                            raise RuntimeError(f"loopback t={t} channel={ch}: CRC {decoded[1]}")
                        received = bytes.fromhex(bit_to_hex_string(decoded[0]))
                        word = tag_bch.codeword_bits(received, t)
                        if tag_bch.decode_bits(word, t) != word:
                            raise RuntimeError(f"t={t}: the PDU received is not a codeword")
                        n = len(word)
                        bad = list(word)
                        for k in rng.sample(range(n), t):
                            bad[k] ^= 1
                        if tag_bch.decode_bits(bad, t) != word:
                            raise RuntimeError(f"t={t}: {t} errors not corrected")
                        worse = list(word)
                        for k in rng.sample(range(n), t + 1):
                            worse[k] ^= 1
                        beyond = tag_bch.decode_bits(worse, t)
                        if beyond == word:
                            raise RuntimeError(f"t={t}: {t + 1} errors returned the word sent")
                        crc_bits = "".join(str(int(b)) for b in crc24_core(pdu, crc_init))  # in the order sent
                        rows.append(dict(t=t, sensor_bytes=s, tx_add=tx_add, gauss_table=gauss_table, channel=ch, sensor=sensor.hex(),
                                         access_address="8e89bed6" if ch >= 37 else "60850a1b", pdu=packet.hex(), crc_bits=crc_bits,
                                         samples=len(actual_i), phy_bits=40 + len(packet) * 8 + 24,
                                         loopback_crc=True, codeword=True, corrected_t=True,
                                         beyond_t="detected" if beyond is None else "other codeword",
                                         result="PASS"))
                print(f"t = {t:2}, S = {s}, GAUSS_TABLE = {gauss_table}: {len(channels) * len(sensors)} packets: the RTL's I/Q "
                      f"equal to the model's, CRC-valid loopback, a codeword, {t} errors corrected", flush=True)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"PASS: {len(rows)} complete tag TX waveforms")


if __name__ == "__main__":
    main()
