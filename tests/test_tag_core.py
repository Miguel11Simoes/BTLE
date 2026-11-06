"""tag_core of ble-tx-poc, from the sensor's model to upstream's Python receiver: every scenario of the plan's phase 2.

Author: Miguel Simões

tests/tag_core_tb.v runs tag_core with the models of the TMP100 (tests/tmp100_model.v), of the 24AA02E48
(tests/eeprom_24aa02e48_model.v), of a SPI sensor (tests/spi_sensor_model.v), of an ADC and an MTP port, and a monitor
of the I2C bus against the limits of both datasheets (tests/i2c_timing_monitor.v). Each scenario below is one
simulation; for every packet it sends, against what the scenario implies:
- the sensor byte: from what the sensor's model really answered (its log) through the profile's capture
  (tag_profile.py's Capture.code), and, in the nominal scenario, from the temperature itself and back to it;
- the PHY bits: those of python/btlelib.py's btle_tx for the PDU of scripts/senseworks/tag_bch.py, with the AdvA, TxAdd
  and channel the scenario implies;
- upstream's Python receiver (btle_rx) decodes the I/Q, the CRC right, that PDU;
- the BCH code: the PDU is a codeword, and t errors at random are corrected back to it;
- T_advEvent, start to start: exactly 32 * interval + 1 + advDelay ticks (+ 2 with a tick every clock: the sleep's last
  clock is then a tick of its own), advDelay from a model of the LFSR, its seed AdvA's first byte (in the scenarios with
  room for it: an interval longer than the measurement);
- each WAIT of k units lasts between k and k + 1 units, so a device's maximum time is met at any phase of the units;
- the TMP100's log: no read during a conversion, no one-shot written outside shutdown; the EEPROM's log: no write,
  ever, and no START once the profile is read in the scenarios that are not on its bus.
The packets of the scenarios on the default code go to --output (JSON) for scripts/senseworks/check_tag_scapy.py.

Then: the coverage of the state machine (every (phase, state) the design can reach, and every (command, phase) of the bus,
over all the scenarios), and with --mutants the deliberate faults, each of which must fail a scenario with a concrete
mismatch. tag_profile.py's default profile must be the RTL's.

  python3 tests/test_tag_core.py [--only NAME[,NAME]] [--jobs N] [--mutants] [--output FILE]
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
import json
import math
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
from btlelib import btle_tx, btle_rx, hex_string_to_bit, bit_to_hex_string, crc24_core  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402
import tag_profile  # noqa: E402
from tag_profile import Capture, Profile, xfer, wait_ms, END  # noqa: E402

RTL = ["tag_core.v", "tag_bus.v", "tag_capture.v", "btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v",
       "scramble_core.v", "gfsk_modulation.v", "bit_repeat_upsample.v", "gauss_filter.v", "vco.v"]
MODELS = ["tag_core_tb.v", "i2c_slave_model.v", "tmp100_model.v", "eeprom_24aa02e48_model.v", "spi_sensor_model.v",
          "i2c_timing_monitor.v", "efuse_async_mem_1x8_model.v"]
EUI = 0x0004A3123456                     # the EEPROM's EUI-48, DS22124D's example
ROM_ADV = 0xC10203040506                 # tag_core's ADV_ADDRESS
DEFAULT_CID = 0xFFFF
PHASES = {"profile": 0, "eui": 1, "boot": 2, "measure": 3}
ST = dict(READY=0, CLEAR_READ=1, CLEAR_STOP=2, FETCH=3, WAIT=4, START=5, WRITE=6, READ=7, STOP=8, END=9, SLEEP=10,
          DELAY=11, TX=12, TX_WAIT=13, MTP=14, CLEAR_FIRST=15)


class Mismatch(Exception):
    """The design did not do what the scenario implies: a concrete failure."""


@dataclass(frozen=True)
class Build:
    cfg_src: int = 0
    sensor_bytes: int = 1
    bch: int = 8
    adc: int = 0
    bus_div: int = 25
    otp: int = 0
    clk_half_ns: float = 31.25
    command: int = 0
    profile: str = ""                    # DEFAULT_PROFILE, when not the RTL's

    def tick_clocks(self) -> int:
        return 1 if self.bus_div == 1 else 2 * self.bus_div

    def time_scale(self) -> float:
        """How much faster than the FPGA's 32 kHz tick the scenario runs; the models' times divide by it."""
        return 31250.0 / (self.tick_clocks() * 2 * self.clk_half_ns)


@dataclass
class Scenario:
    name: str
    build: Build = Build()
    image: bytes | None = None           # the EEPROM's free half; None: blank
    capture: Capture | None = None       # what the packets' sensor byte must come from, with the TMP100's reads
    captures: list[Capture] | None = None
    temps: list[float] = field(default_factory=lambda: [25.0])
    spi_values: list[int] = field(default_factory=lambda: [0])
    mtp: bytes | None = None
    eui: int = EUI
    adv: int = EUI                       # the AdvA expected
    tx_add: int = 0
    channel: int = 37
    interval: int | None = None          # exact T_advEvent checked when given
    events: int = 3
    max_ms: int = 3000
    plus: dict = field(default_factory=dict)
    i2c_after_boot: bool = True          # False: no START on the bus once booted
    expected_sensors: list[bytes] | None = None
    expect_codes: list[int] | None = None  # the sensor byte of each packet, when known a priori
    resets: bool = False
    rows: bool = True
    profile_ok: int = 1                  # the profile in use is the one read; 0: the default
    test_mode: bool = False
    allow_os_ignored: bool = False       # the boot program did not reach the TMP100: it is still in continuous conversion
    scl_period_ns: float | None = None
    frames: tuple[int, int] | None = None  # the STARTs and STOPs the bus must see


def build_args(build: Build, work: Path, tag: str, texts: dict[str, str] | None) -> Path:
    """Compile once per build (and per mutation); the simulation binary is shared by the scenarios."""
    key = hashlib.sha256(repr((build, tag)).encode()).hexdigest()[:16]
    out = work / f"sim_{key}"
    if out.exists():
        return out
    d = work / f"src_{key}"
    d.mkdir()
    files = []
    for f in RTL:
        path = d / f
        path.write_text(texts[f] if texts and f in texts else (ROOT / "verilog" / f).read_text())
        files.append(str(path))
    files += [str(ROOT / "tests" / f) for f in MODELS]
    defs = [f"-DCFG_SRC={build.cfg_src}", f"-DSB={build.sensor_bytes}", f"-DBCH={build.bch}", f"-DADC={build.adc}",
            f"-DBUS_DIV={build.bus_div}", f"-DOTP={build.otp}", f"-DCLK_HALF_NS={build.clk_half_ns}",
            f"-DCOMMAND={build.command}", f"-DROM_ADV=48'h{ROM_ADV:012x}", f"-DCID=16'h{DEFAULT_CID:04x}"]
    if build.profile:
        defs.append(f"-DPROFILE={build.profile}")
    result = subprocess.run([os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tag_core_tb", "-o", str(out),
                             *defs, *files], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"does not compile:\n{result.stdout}{result.stderr}")
    return out


def eeprom_hex(image: bytes | None, eui: int) -> str:
    mem = bytearray([0xFF] * 256)
    if image is not None:
        mem[:len(image)] = image
    mem[0xFA:0x100] = eui.to_bytes(6, "big")
    return "".join(f"{b:02x}\n" for b in mem)


def temps_hex(temps: list[float]) -> str:
    return "".join(f"{round(t * 16) & 0xFFFF:04x}\n" for t in temps)


def simulate(s: Scenario, sim: Path, work: Path) -> Path:
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=work))
    (run_dir / "eeprom.hex").write_text(eeprom_hex(s.image, s.eui))
    (run_dir / "temps.hex").write_text(temps_hex(s.temps))
    (run_dir / "spi_values.hex").write_text("".join(f"{v:04x}\n" for v in s.spi_values))
    (run_dir / "mtp.hex").write_text("".join(f"{b:02x}\n" for b in (s.mtp or bytes(64))))
    plus = {"events": s.events, "max_ms": s.max_ms, "time_scale": s.build.time_scale(), **s.plus}
    args = [f"+{k}={v}" for k, v in plus.items()]
    result = subprocess.run([os.environ.get("VVP", "vvp"), "-n", str(sim), *args], cwd=run_dir, capture_output=True,
                            text=True, timeout=3000)
    log = result.stdout + result.stderr
    lines = [l for l in log.splitlines() if l.startswith(("PASS", "MISMATCH", "ERROR"))]
    if result.returncode != 0 or not any(l.startswith("PASS") for l in lines):
        mismatch = [l for l in lines if l.startswith("MISMATCH")]
        if mismatch:
            raise Mismatch(mismatch[0])
        raise RuntimeError(f"exit {result.returncode}: {log[-800:]}")
    (run_dir / "verdict.txt").write_text(lines[-1] + "\n")
    return run_dir


def sensor_expected_from_reads(s: Scenario, run: Path, packets: list[dict]) -> list[bytes | None]:
    """The sensor bytes each packet must carry, from the reads in the TMP100's log since the last packet."""
    reads = []
    log = run / "tmp100.log"
    for line in log.read_text().splitlines():
        f = line.split()
        if f[0] == "read":
            reads.append((float(f[1]), int(f[2], 16), int(f[3])))
    expected = []
    previous = -1.0
    captures = s.captures or [s.capture]
    for p in packets:
        window = [r for r in reads if previous < r[0] < p["ns"]]
        previous = p["ns"]
        if window:
            bits = [int(b) for r in window for b in format(r[1], "016b")]
            expected.append(bytes(c.code(bits) for c in captures))
        else:
            expected.append(bytes([0xFF] * len(captures)))
    return expected


def lfsr_sequence(seed: int, n: int) -> list[int]:
    values, l = [], seed
    for _ in range(n):
        values.append(l)
        l = ((l << 1) & 0xFF) | (((l >> 7) ^ (l >> 5) ^ (l >> 4) ^ (l >> 3) ^ int((l & 0x7F) == 0)) & 1)
    return values


def check(s: Scenario, run: Path, rng: random.Random) -> tuple[list[dict], str]:
    b = s.build
    t = b.bch
    events, aborted = [], set()
    for line in (run / "events.txt").read_text().splitlines():
        f = line.split()
        if f[0] == "tx":
            events.append(dict(packet=int(f[1]), ns=float(f[2]), clocks=int(f[3]), sensor=int(f[4], 16),
                               failed=int(f[5]), profile_ok=int(f[6]), eui_ok=int(f[7]), adv=int(f[8], 16),
                               tx_add=int(f[9]), channel=int(f[10])))
        elif f[0] == "reset":
            aborted.add(int(f[1]))
        elif f[0] == "wait":
            k, clocks = int(f[1]), int(f[2])
            if not s.resets and not 32 * k * b.tick_clocks() <= clocks <= 32 * (k + 1) * b.tick_clocks() + b.tick_clocks():
                raise Mismatch(f"WAIT {k} lasted {clocks / b.tick_clocks()} ticks, {32 * k} to {32 * (k + 1)} expected")
    done = [e for e in events if e["packet"] not in aborted]
    if len(done) < s.events - (1 if s.resets else 0):
        raise Mismatch(f"{len(done)} packets completed, {s.events} expected")
    # the packets
    tables = {n: np.loadtxt(run / f"{n}.txt", dtype=int, ndmin=2) for n in ("iq", "bits")}
    if s.expected_sensors is not None:
        expected = list(s.expected_sensors)
    elif s.capture is not None or s.captures is not None:
        expected = sensor_expected_from_reads(s, run, events)
    else:
        expected = [None] * len(events)
    crc_init = hex_string_to_bit("555555")
    rows = []
    n_sensor = b.sensor_bytes
    for k, e in enumerate(events):
        got_sensor = e["sensor"].to_bytes(n_sensor, "little")
        if expected[k] is not None and got_sensor != expected[k]:
            raise Mismatch(f"packet {e['packet']}: sensor {got_sensor.hex()}, expected {expected[k].hex()}")
        if s.expect_codes is not None and e["packet"] not in aborted:
            want = s.expect_codes[k]
            if got_sensor[0] != want:
                raise Mismatch(f"packet {e['packet']}: code {got_sensor[0]}, expected {want}")
        if e["failed"] != int(got_sensor == bytes([0xFF] * n_sensor) and not s.test_mode):
            raise Mismatch(f"packet {e['packet']}: failed flag {e['failed']}, sensor {got_sensor.hex()}")
        if e["profile_ok"] != s.profile_ok:
            raise Mismatch(f"packet {e['packet']}: profile_ok {e['profile_ok']}, expected {s.profile_ok}")
        if e["eui_ok"] != int(b.cfg_src == 0 and s.adv == s.eui):
            raise Mismatch(f"packet {e['packet']}: AdvA read from the EEPROM {e['eui_ok']}, AdvA {e['adv']:012x}")
        if e["adv"] != s.adv or e["tx_add"] != s.tx_add or e["channel"] != s.channel:
            raise Mismatch(f"packet {e['packet']}: AdvA {e['adv']:012x} TxAdd {e['tx_add']} channel {e['channel']}; expected "
                           f"{s.adv:012x} {s.tx_add} {s.channel}")
        if e["packet"] in aborted:
            continue
        pdu = tag_bch.tag_pdu(s.adv, got_sensor, t, DEFAULT_CID, s.tx_add)
        pdu_bits = hex_string_to_bit(pdu.hex())
        i, q, bits, _ = btle_tx(pdu_bits, s.channel, crc_init, "D6BE898E")
        got_bits = tables["bits"][tables["bits"][:, 0] == e["packet"]][:, 1]
        if not np.array_equal(got_bits, bits):
            raise Mismatch(f"packet {e['packet']}: the PHY bits are not those of the PDU {pdu.hex()}")
        got_iq = tables["iq"][tables["iq"][:, 0] == e["packet"]][:, 1:]
        if got_iq.shape[0] != len(i):
            raise Mismatch(f"packet {e['packet']}: {got_iq.shape[0]} samples, {len(i)} expected")
        decoded = btle_rx(got_iq[:, 0], got_iq[:, 1], s.channel, crc_init, "D6BE898E")
        if not decoded[1] or bit_to_hex_string(decoded[0]) != pdu.hex():
            raise Mismatch(f"packet {e['packet']}: upstream's receiver does not decode the PDU sent")
        received = bytes.fromhex(bit_to_hex_string(decoded[0]))
        word = tag_bch.codeword_bits(received, t)
        if tag_bch.decode_bits(word, t) != word:
            raise Mismatch(f"packet {e['packet']}: the PDU is not a codeword")
        bad = list(word)
        for j in rng.sample(range(len(word)), t):
            bad[j] ^= 1
        if tag_bch.decode_bits(bad, t) != word:
            raise Mismatch(f"packet {e['packet']}: {t} errors not corrected")
        if s.rows:
            rows.append(dict(scenario=s.name, t=t, sensor_bytes=n_sensor, tx_add=s.tx_add, channel=s.channel,
                             sensor=got_sensor.hex(), access_address="8e89bed6", pdu=pdu.hex(),
                             crc_bits="".join(str(int(v)) for v in crc24_core(pdu_bits, crc_init))))
    # T_advEvent, exact in ticks
    if s.interval is not None:
        delays = lfsr_sequence(s.adv & 0xFF, len(events) + 1)
        for k in range(1, len(events)):
            ticks = (events[k]["clocks"] - events[k - 1]["clocks"]) / b.tick_clocks()
            want = 32 * s.interval + (2 if b.bus_div == 1 else 1) + delays[k]
            if ticks != want:
                raise Mismatch(f"T_advEvent between packets {k - 1} and {k}: {ticks} ticks, expected {want} "
                               f"(interval {s.interval}, advDelay {delays[k]})")
    # the models' logs
    tmp100 = (run / "tmp100.log").read_text().splitlines()
    if s.capture is not None or s.captures is not None:
        if any(l.startswith("os_ignored") for l in tmp100) and not s.allow_os_ignored:
            raise Mismatch("a one-shot written outside shutdown: " + next(l for l in tmp100 if l.startswith("os_ignored")))
        stale = [l for l in tmp100 if l.startswith("read") and l.split()[3] == "1"]
        if stale:
            raise Mismatch("the temperature read during a conversion: " + stale[0])
    eeprom = (run / "eeprom.log").read_text().splitlines()
    if any(l.startswith("write") for l in eeprom):
        raise Mismatch("the tag wrote to the EEPROM: " + next(l for l in eeprom if l.startswith("write")))
    if not s.i2c_after_boot:
        starts = [float(l.split()[1]) for l in eeprom if l.startswith("start")]
        if starts and events and starts[-1] > events[0]["ns"]:
            raise Mismatch(f"a START on the I2C bus at {starts[-1]} ns, after the first packet")
    verdict = (run / "verdict.txt").read_text().strip()
    if s.scl_period_ns is not None:
        low, high = map(float, re.search(r"SCL period, between ([\d.]+) and ([\d.]+) ns", verdict).groups())
        if low != s.scl_period_ns or high != s.scl_period_ns:
            raise Mismatch(f"SCL period between {low} and {high} ns, expected {s.scl_period_ns}")
    if s.frames is not None:
        got = tuple(map(int, re.search(r"(\d+) STARTs, (\d+) STOPs", verdict).groups()))
        if got != s.frames:
            raise Mismatch(f"{got[0]} STARTs and {got[1]} STOPs on the bus, expected {s.frames[0]} and {s.frames[1]}")
    return rows, verdict


# ------------------------------------------------------------------------------------------------- the scenarios
TMP100_9 = Capture(take=9, signed=True, offset=80)


def frames(events: int) -> tuple[int, int]:
    """The STARTs and STOPs of a boot and of events of the default program. Boot: the bus clear's first STOP (with SCL high,
    a START and a STOP) and its last, the profile (2 STARTs, 1 STOP), the EUI-48 (the same), the boot program. An event:
    the one-shot's frame; the pointer's, closed by the repeated START of the read's."""
    return 6 + 3 * events, 5 + 2 * events


def code9(t: float) -> int:
    return max(0, min(254, math.floor(2 * t) + 80))


def image_of(profile: Profile) -> bytes:
    return profile.image()


def scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    default_image = tag_profile.default_image()
    # nominal: the default profile, the temperature sweep, both saturations, the sign, the truncation
    sweep = [25.0, -40.0, -40.5, -55.0, 0.0, 87.0, 87.5, 125.0, -0.5, 0.25, 20.75, 30.0]
    out.append(Scenario("nominal", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9, temps=sweep,
                        interval=100, events=len(sweep), expect_codes=[code9(t) for t in sweep], scl_period_ns=6250.0,
                        frames=frames(len(sweep))))
    # the default interval of the demonstration, 1 s, in real time: 16 MHz, 64 kHz bus phases
    out.append(Scenario("real_time", Build(bus_div=250), image=default_image, capture=TMP100_9, temps=[21.5, 22.0, 22.5],
                        interval=1000, events=3, max_ms=5000, expect_codes=[code9(t) for t in (21.5, 22.0, 22.5)],
                        scl_period_ns=62500.0))
    # the typical conversion time: the same bytes (the wait is for the maximum)
    out.append(Scenario("conversion_typical", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9,
                        temps=[10.0, 11.0], interval=100, events=2, plus={"conv_mode": 1}))
    # the sensor stops answering, and comes back
    out.append(Scenario("sensor_nack", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9,
                        temps=[20.0, 21.0, 22.0], events=6, plus={"nack_from": 2, "nack_to": 4},
                        expected_sensors=[bytes([code9(20.0)]), bytes([code9(21.0)]), b"\xff", b"\xff",
                                          bytes([code9(22.0)]), bytes([code9(22.0)])]))
    out.append(Scenario("sensor_nack_at_boot", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9,
                        temps=[20.0], events=4, allow_os_ignored=True, plus={"nack_from": 0, "nack_to": 2},
                        expected_sensors=[b"\xff", b"\xff", bytes([code9(20.0)]), bytes([code9(20.0)])]))
    # the profile corrupted, in each way: the default profile, the EUI-48 still the AdvA
    flips = [0, 7, 100, 8 * 31 - 1, 8 * 31]
    for bit in flips:
        bad = bytearray(default_image)
        bad[bit // 8] ^= 0x80 >> (bit % 8)
        out.append(Scenario(f"profile_bit_{bit}", image=bytes(bad), capture=TMP100_9, temps=[20.0, 21.0], events=2, profile_ok=0))
    wrong_version = Profile(tag_profile.tmp100().boot, tag_profile.tmp100().measure, [TMP100_9], version=2).image()
    out.append(Scenario("profile_version", image=wrong_version, capture=TMP100_9, temps=[20.0, 21.0], events=2, profile_ok=0))
    wrong_size = bytearray(default_image)
    wrong_size[1] = 31
    wrong_size[31] = tag_profile.crc8(bytes(wrong_size[:31]))
    out.append(Scenario("profile_size", image=bytes(wrong_size), capture=TMP100_9, temps=[20.0, 21.0], events=2, profile_ok=0))
    out.append(Scenario("profile_blank", image=None, capture=TMP100_9, temps=[20.0, 21.0], events=2, profile_ok=0))
    out.append(Scenario("profile_zero", image=bytes(32), capture=TMP100_9, temps=[20.0, 21.0], events=2, profile_ok=0))
    # no EEPROM at all: the default profile, the compiled AdvA and its TxAdd
    out.append(Scenario("eeprom_absent", image=default_image, capture=TMP100_9, temps=[20.0, 21.0], events=2,
                        adv=ROM_ADV, tx_add=1, profile_ok=0, plus={"eeprom": 0}))
    # SCL held low in the middle of the EUI-48: the compiled AdvA, not half of it; then all well
    out.append(Scenario("eui_interrupted", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9,
                        temps=[20.0, 21.0], events=2, adv=ROM_ADV, tx_add=1,
                        plus={"stuck_state": ST["READ"], "stuck_ph": PHASES["eui"], "stuck_after": 1000,
                              "stuck_clocks": 300000, "i2c_monitor": 0}))
    # other resolutions, intervals, channels: the same RTL, regraved
    for bits, tmin, temps in ((10, -10.0, [20.25, -10.0, 53.5, 60.0]), (12, 10.0, [20.0625, 9.0, 25.875, 30.0])):
        p = tag_profile.tmp100(bits, tmin, interval=1000)
        step = 0.5 / (1 << (bits - 9))
        codes = [max(0, min(254, math.floor((t - tmin) / step))) for t in temps]
        out.append(Scenario(f"tmp100_{bits}_bits", image=p.image(), capture=p.captures[0], temps=temps,
                            events=len(temps), expect_codes=codes, max_ms=4000))
    for channel in (38, 39):
        out.append(Scenario(f"channel_{channel}", image=image_of(tag_profile.tmp100(interval=100, channel=channel)),
                            capture=TMP100_9, temps=[15.0, 16.0], channel=channel, interval=100, events=2))
    # a boot program that writes more: where the measure program starts is the profile's
    long_boot = xfer([0x90, 0x03, 0x40]) + xfer([0x90, 0x01, 0x01]) + wait_ms(75) + END
    out.append(Scenario("long_boot_program", image=Profile(long_boot, tag_profile.tmp100().measure, [TMP100_9],
                                                           interval=100).image(),
                        capture=TMP100_9, temps=[15.0, 16.0], interval=100, events=2))
    # a program that fills the 21 bytes with no END: what follows reads as END
    no_end = xfer([0x90, 0x01, 0x01]) + wait_ms(75) + END
    measure = xfer([0x90, 0x01, 0x81]) + wait_ms(75) + xfer([0x90, 0x00], hold=True) + xfer([0x91], read=2)
    filler = wait_ms(1) * (tag_profile.PROG_BYTES - len(no_end) - len(measure))
    out.append(Scenario("program_full_no_end", image=Profile(no_end, filler + measure, [TMP100_9], interval=100).image(),
                        capture=TMP100_9, temps=[15.0, 16.0], interval=100, events=2))
    # the limits of the interval and of advDelay, in test mode: a counter, no sensor, no bus after boot
    def test_profile(interval: int, **kw) -> Profile:
        return tag_profile.tmp100(interval=interval, test_mode=True, **kw)
    counter = [bytes([k & 0xFF]) for k in range(300)]
    # (the packet lasts 3712 clocks: 74 ticks at BUS_DIV 25, 464 at BUS_DIV 4; the intervals leave room for it)
    out.append(Scenario("test_mode", image=test_profile(5).image(), interval=5, events=8, i2c_after_boot=False,
                        expected_sensors=counter[:8], test_mode=True, temps=[20.0]))
    out.append(Scenario("test_mode_wraps_all_delays", Build(bus_div=4), image=test_profile(16).image(), eui=0x0004A3123400,
                        adv=0x0004A3123400, interval=16, events=300, i2c_after_boot=False, expected_sensors=counter,
                        test_mode=True, plus={"t_out_ns": 30, "i2c_monitor": 0}, temps=[20.0], rows=False, max_ms=5000))
    out.append(Scenario("adv_delay_255_first", image=test_profile(5).image(), eui=0x0004A31234FF, adv=0x0004A31234FF,
                        interval=5, events=4, i2c_after_boot=False, expected_sensors=counter[:4], test_mode=True, temps=[20.0]))
    out.append(Scenario("interval_0", image=test_profile(0).image(), eui=0x0004A3123400, adv=0x0004A3123400, events=4,
                        i2c_after_boot=False, expected_sensors=counter[:4], test_mode=True, temps=[20.0]))
    out.append(Scenario("interval_65535", Build(bus_div=4), image=test_profile(65535).image(), eui=0x0004A3123400,
                        adv=0x0004A3123400, interval=65535, events=2, i2c_after_boot=False, expected_sensors=counter[:2],
                        test_mode=True, plus={"t_out_ns": 30, "i2c_monitor": 0}, temps=[20.0], rows=False, max_ms=5000))
    # an interval shorter than the conversion: back to back, nothing lost, no stale read
    out.append(Scenario("interval_shorter_than_measure", image=image_of(tag_profile.tmp100(interval=20)), capture=TMP100_9,
                        temps=[1.0, 2.0, 3.0, 4.0], events=4, expect_codes=[code9(t) for t in (1.0, 2.0, 3.0, 4.0)]))
    # a reset in each part of an event: the slave may be left holding SDA; the next packets are right
    resets = [("READ", "measure", 0), ("READ", "measure", 150), ("READ", "measure", 400), ("READ", "measure", 700),
              ("WRITE", "measure", 100), ("START", "measure", 30), ("STOP", "measure", 20), ("WAIT", "measure", 2000),
              ("FETCH", "measure", 0), ("TX_WAIT", "measure", 500), ("TX", "measure", 0), ("DELAY", "boot", 0),
              ("SLEEP", "measure", 100), ("DELAY", "measure", 5), ("READ", "profile", 600), ("READ", "eui", 300),
              ("WRITE", "boot", 100), ("WAIT", "boot", 500), ("CLEAR_READ", "profile", 100), ("CLEAR_FIRST", "profile", 10),
              ("WRITE", "measure", 0), ("WRITE", "measure", 300), ("WRITE", "measure", 620)]
    for state, ph, after in resets:
        out.append(Scenario(f"reset_{state.lower()}_{ph}_{after}", image=image_of(tag_profile.tmp100(interval=100)),
                            capture=TMP100_9, temps=[8.0, 6.0, 7.0, 5.0], events=4, resets=True, rows=False,
                            plus={"reset_state": ST[state], "reset_ph": PHASES[ph], "reset_event": 1 if ph == "measure" else 0,
                                  "reset_after": after, "i2c_monitor": 0}))
    # clock stretching: a device that holds SCL; on every bit, and long on the acknowledges
    out.append(Scenario("stretch_every_bit", image=image_of(tag_profile.tmp100(interval=200)), capture=TMP100_9,
                        temps=[33.0, 34.0], events=2, plus={"stretch_ns": 8000, "stretch_every_bit": 1}))
    out.append(Scenario("stretch_long", image=image_of(tag_profile.tmp100(interval=200)), capture=TMP100_9,
                        temps=[33.0, 34.0], events=2, frames=frames(2), plus={"stretch_ns": 40000, "stretch_every_bit": 0}))
    # SCL held low by a device in the middle of a byte the master sends (SDA pulled low): the timeout releases the pins
    out.append(Scenario("write_interrupted", image=image_of(tag_profile.tmp100(interval=300)), capture=TMP100_9, temps=[33.0, 34.0],
                        events=4, plus={"stuck_state": ST["WRITE"], "stuck_ph": PHASES["measure"], "stuck_after": 150,
                                        "stuck_clocks": 800000, "i2c_monitor": 0},
                        expected_sensors=[b"\xff", b"\xff", bytes([code9(33.0)]), bytes([code9(34.0)])]))
    # a line stuck low: the event still goes, with 0xFF, after the timeout; then the bus recovers
    out.append(Scenario("scl_stuck", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9, temps=[40.0, 41.0, 42.0],
                        events=5, plus={"stuck_scl_from": 1, "stuck_scl_to": 3, "i2c_monitor": 0},
                        expected_sensors=[bytes([code9(40.0)]), b"\xff", b"\xff", bytes([code9(41.0)]), bytes([code9(42.0)])]))
    out.append(Scenario("sda_stuck", image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9, temps=[40.0, 41.0, 42.0],
                        events=5, plus={"stuck_sda_from": 1, "stuck_sda_to": 3, "i2c_monitor": 0},
                        expected_sensors=[bytes([code9(40.0)]), b"\xff", b"\xff", bytes([code9(41.0)]), bytes([code9(42.0)])]))
    out.append(Scenario("scl_stuck_at_boot", image=default_image, capture=TMP100_9, temps=[40.0], events=3, adv=ROM_ADV, tx_add=1,
                        profile_ok=0, allow_os_ignored=True, plus={"stuck_scl_from": 0, "stuck_scl_to": 1, "i2c_monitor": 0}, max_ms=6000,
                        expected_sensors=[b"\xff", bytes([code9(40.0)]), bytes([code9(40.0)])]))
    # a sensor that is not on I2C: SPI, modes 0 and 3, with the EEPROM on the same two wires
    max6675 = Capture(take=11, skip=1, offset=-40)   # 16 bits: a dummy 0, 12 bits of 0.25 degC; the window: 0.5 degC, unsigned
    spi0 = Profile(END, xfer(read=2) + END, [max6675], interval=100, spi=True)
    values0 = [(int(t * 4) << 3) for t in (25.0, 0.0, 19.0, 150.0, 20.5)]
    out.append(Scenario("spi_mode0_read_only", Build(command=0), image=spi0.image(), spi_values=values0, events=5, interval=100,
                        i2c_after_boot=False, plus={"tmp100": 0, "i2c_monitor": 0},
                        expected_sensors=[bytes([max6675.code([int(b) for b in format(v, "016b")])]) for v in values0]))
    adt7310 = Capture(take=10, signed=True, offset=80)   # 16 bits: 1/128 degC per bit; the window: 0.5 degC, signed
    spi3 = Profile(END, xfer([0x50], read=2) + END, [adt7310], interval=100, spi=True, spi_cpol=True)
    values3 = [(t * 128) & 0xFFFF for t in (25, -10, -60, 100, 3)]
    out.append(Scenario("spi_mode3_command", Build(command=1), image=spi3.image(), spi_values=values3, events=5, interval=100,
                        i2c_after_boot=False, plus={"tmp100": 0, "i2c_monitor": 0},
                        expected_sensors=[bytes([adt7310.code([int(b) for b in format(v, "016b")])]) for v in values3]))
    # the ADC, by the parameter: the profile's third choice
    adc_capture = Capture(take=9, signed=False, offset=-10)
    adc_profile = Profile(END, xfer(read=2) + END, [adc_capture], interval=100, adc=True)
    adc_values = [0x0000, 0x4000, 0x8000, 0xFFF0, 0x1230]
    out.append(Scenario("adc", Build(adc=1), image=adc_profile.image(), spi_values=adc_values, events=5, interval=100,
                        i2c_after_boot=False, plus={"tmp100": 0, "i2c_monitor": 0},
                        expected_sensors=[bytes([adc_capture.code([int(b) for b in format(v, "016b")])]) for v in adc_values]))
    # (the window of 16 bits, unsigned: its top bit is no sign)
    adc16 = Capture(take=16, signed=False, offset=-32768)
    adc16_profile = Profile(END, xfer(read=2) + END, [adc16], interval=100, adc=True)
    adc16_values = [0x8010, 0x7FF0, 0x8FE0, 0xFFF0]
    out.append(Scenario("adc_unsigned_16_bits", Build(adc=1), image=adc16_profile.image(), spi_values=adc16_values, events=4, interval=100,
                        i2c_after_boot=False, plus={"tmp100": 0, "i2c_monitor": 0},
                        expected_sensors=[bytes([adc16.code([int(b) for b in format(v, "016b")])]) for v in adc16_values]))
    # the variants of the configuration's source
    fast = tag_profile.tmp100(interval=100)
    compiled = tag_profile.verilog_constant(fast.image())
    out.append(Scenario("cfg_otp_rom", Build(cfg_src=1, profile=compiled), image=None, capture=TMP100_9, temps=[12.0, 13.0],
                        adv=ROM_ADV, tx_add=1, interval=100, events=2, profile_ok=0, plus={"eeprom": 0}))
    otp_adv = 0xD1E2A3B4C5F6
    out.append(Scenario("cfg_otp_efuse", Build(cfg_src=1, otp=1, profile=compiled), image=None, capture=TMP100_9, temps=[12.0, 13.0],
                        adv=otp_adv, tx_add=1, interval=100, events=2, profile_ok=0, plus={"eeprom": 0, "otp_prog": f"{otp_adv:012x}"}))
    mtp_image = fast.image() + bytes(32)
    out.append(Scenario("cfg_mtp", Build(cfg_src=2), image=None, mtp=mtp_image, capture=TMP100_9, temps=[12.0, 13.0],
                        adv=ROM_ADV, tx_add=1, interval=100, events=2, plus={"eeprom": 0}))
    mtp_bad = bytearray(mtp_image)
    mtp_bad[10] ^= 0x10
    out.append(Scenario("cfg_mtp_corrupted", Build(cfg_src=2), image=None, mtp=bytes(mtp_bad), capture=TMP100_9, temps=[12.0, 13.0],
                        adv=ROM_ADV, tx_add=1, events=2, profile_ok=0, plus={"eeprom": 0}))
    # two bytes of sensor: two windows over one read
    two = Profile(tag_profile.tmp100().boot, tag_profile.tmp100().measure, [TMP100_9, Capture(take=8, skip=8)], interval=100)
    out.append(Scenario("two_sensor_bytes", Build(sensor_bytes=2), image=two.image(), captures=two.captures, temps=[25.25, -3.0],
                        interval=100, events=2))
    # the other codes
    for bch in (12, 18):
        out.append(Scenario(f"bch_{bch}", Build(bch=bch), image=image_of(tag_profile.tmp100(interval=100)), capture=TMP100_9,
                            temps=[25.0, 26.0], interval=100, events=2, rows=False))
    # the ASIC's clock: 32.768 kHz, tick = bus_en = clk, so SCL at 8.2 kHz and the synchronizers a phase long
    # (with no switch to 16 MHz here, the packet takes 3712 of those clocks: the interval leaves room for it)
    out.append(Scenario("asic_clock", Build(bus_div=1, clk_half_ns=15258.789), image=image_of(tag_profile.tmp100(interval=300)),
                        capture=TMP100_9, temps=[25.0, -20.0, 60.0], interval=300, events=3, max_ms=20000,
                        expect_codes=[code9(t) for t in (25.0, -20.0, 60.0)], plus={"t_out_ns": 900}))
    return out


# ------------------------------------------------------------------------------------------------- the coverage
def required_coverage() -> set[tuple[str, int, int]]:
    need = set()
    for state, ph in [("READY", "profile"), ("CLEAR_FIRST", "profile"), ("CLEAR_READ", "profile"), ("CLEAR_STOP", "profile"), ("FETCH", "profile"),
                      ("START", "profile"), ("WRITE", "profile"), ("READ", "profile"), ("STOP", "profile"), ("END", "profile"),
                      ("MTP", "profile"),
                      ("FETCH", "eui"), ("START", "eui"), ("WRITE", "eui"), ("READ", "eui"), ("STOP", "eui"), ("END", "eui"),
                      ("CLEAR_FIRST", "eui"), ("CLEAR_READ", "eui"), ("CLEAR_STOP", "eui"),
                      ("READY", "boot"), ("CLEAR_FIRST", "boot"), ("CLEAR_READ", "boot"), ("CLEAR_STOP", "boot"), ("FETCH", "boot"), ("WAIT", "boot"),
                      ("START", "boot"), ("WRITE", "boot"), ("READ", "boot"), ("STOP", "boot"), ("END", "boot"), ("SLEEP", "boot"),
                      ("DELAY", "boot"), ("TX", "boot"), ("TX_WAIT", "boot"),
                      ("FETCH", "measure"), ("WAIT", "measure"), ("START", "measure"), ("WRITE", "measure"), ("READ", "measure"),
                      ("STOP", "measure"), ("END", "measure"), ("CLEAR_FIRST", "measure"), ("CLEAR_READ", "measure"), ("CLEAR_STOP", "measure"),
                      ("TX", "measure"), ("TX_WAIT", "measure"), ("SLEEP", "measure"), ("DELAY", "measure")]:
        need.add(("state", PHASES[ph], ST[state]))
    for op in range(4):
        for phase in range(4):
            need.add(("bus", op, phase))
    return need


# ------------------------------------------------------------------------------------------------- the mutants
# (file, what the fault is, edits, scenarios: one of them must fail with a concrete mismatch)
MUTANTS = [
    ("tag_bus.v", "SDA changes with SCL high",
     [("2'd0: if (!adc) sda_oe <= !shift[8];\n          2'd1: if (!adc) scl_oe <= 1'b0;",
       "2'd0: if (!adc) scl_oe <= 1'b0;\n          2'd1: if (!adc) sda_oe <= !shift[8];")], ["nominal"]),
    ("tag_bus.v", "no clock stretching on the bits", [("op_bits  ? (!adc && !scl) :", "op_bits  ? 1'b0 :")], ["stretch_every_bit"]),
    ("tag_bus.v", "the acknowledge read inverted", [("2'd2: if (ack_bit) acked <= !sda;", "2'd2: if (ack_bit) acked <= sda;")], ["nominal"]),
    ("tag_bus.v", "the last byte read acknowledged", [("{8'hFF, !read_ack}", "{8'hFF, 1'b0}")], ["nominal"]),
    ("tag_bus.v", "the bytes sent least significant bit first",
     [("{write_data, 1'b1} :", "{write_data[0], write_data[1], write_data[2], write_data[3], write_data[4], write_data[5], write_data[6], write_data[7], 1'b1} :")], ["nominal"]),
    ("tag_bus.v", "no START: SDA does not fall", [("2'd2: sda_oe <= 1'b1;                // SDA falls with SCL high", "2'd2: ;")], ["nominal"]),
    ("tag_bus.v", "no STOP: SDA stays low", [("2'd2: sda_oe <= 1'b0;                // SDA rises with SCL high", "2'd2: ;")], ["nominal"]),
    ("tag_bus.v", "START with SCL low", [("2'd1: scl_oe <= 1'b0;\n          2'd2: sda_oe <= 1'b1;", "2'd1: ;\n          2'd2: sda_oe <= 1'b1;")], ["nominal"]),
    ("tag_bus.v", "START does not wait for the lines", [("(!spi && !(scl && sda))", "1'b0")], ["sda_stuck"]),
    ("tag_bus.v", "STOP does not wait for SCL", [("(!adc && !spi && !scl));", "1'b0);")], ["stretch_long"]),
    ("tag_bus.v", "SPI: CS_n stays low", [("2'd1: cs_n <= 1'b1;", "2'd1: ;")], ["spi_mode0_read_only"]),
    ("tag_bus.v", "SPI: CS_n does not fall", [("2'd1: cs_n <= 1'b0;", "2'd1: ;")], ["spi_mode0_read_only"]),
    ("tag_bus.v", "SPI: the clock's idle level ignored", [("2'd0: if (cs_n) scl_oe <= !cpol;", "2'd0: if (cs_n) scl_oe <= 1'b1;")], ["spi_mode3_command"]),
    ("tag_bus.v", "SPI: a ninth bit", [("(spi || adc) ? 4'd8 : 4'd9;", "4'd9;")], ["spi_mode3_command"]),
    ("tag_bus.v", "SPI: SDA read instead of MISO", [("assign rx_bit = adc ? adc_bit : (spi ? miso : sda);", "assign rx_bit = adc ? adc_bit : sda;")], ["spi_mode0_read_only"]),
    ("tag_bus.v", "the ADC's result taken before it is done", [("(adc ? !adc_done :", "(adc ? 1'b0 :")], ["adc"]),
    ("tag_bus.v", "the ADC's bits in the wrong order", [("adc_shift <= {adc_shift[14:0], 1'b0};", "adc_shift <= {1'b0, adc_shift[15:1]};")], ["adc"]),
    ("tag_bus.v", "the pins kept low after a timeout", [("if (rst || abort) begin", "if (rst) begin")], ["write_interrupted"]),
    ("tag_capture.v", "a bit more in the window", [("take_left <= take;", "take_left <= take + 5'd1;")], ["nominal"]),
    ("tag_capture.v", "no sign extension", [("{{15{is_signed & bit_in}}, bit_in}", "{15'd0, bit_in}")], ["nominal"]),
    ("tag_capture.v", "the window's sign kept when unsigned", [("{{2{is_signed & window[15]}}, window}", "{{2{window[15]}}, window}")], ["adc_unsigned_16_bits"]),
    ("tag_capture.v", "the offset ignored", [("+ $signed({{2{offset[15]}}, offset});", "+ 18'sd0;")], ["nominal"]),
    ("tag_capture.v", "no saturation at 0", [("assign value = sum[17]            ? 8'd0 :", "assign value = 1'b0               ? 8'd0 :")], ["nominal"]),
    ("tag_capture.v", "no saturation at the top", [("(sum > MAX_VALUE)  ? MAX_VALUE[7:0] :", "1'b0               ? MAX_VALUE[7:0] :")], ["nominal"]),
    ("tag_capture.v", "the top saturates to 255", [("localparam signed [17:0] MAX_VALUE = 18'sd254;", "localparam signed [17:0] MAX_VALUE = 18'sd255;")], ["nominal"]),
    ("tag_capture.v", "skip ignored", [("if (skip_left != 6'd0) begin", "if (1'b0) begin")], ["spi_mode0_read_only"]),
    ("tag_core.v", "the CRC not checked", [("(cfg_size == PROFILE_SIZE) && crc_zero;", "(cfg_size == PROFILE_SIZE);")], ["profile_bit_100"]),
    ("tag_core.v", "the version not checked", [("!failed && (cfg_version == PROFILE_VERSION) &&", "!failed &&")], ["profile_version"]),
    ("tag_core.v", "the size not checked", [("(cfg_size == PROFILE_SIZE) && crc_zero;", "crc_zero;")], ["profile_size"]),
    ("tag_core.v", "a rejected profile kept", [("if (rst || profile_rejected) begin", "if (rst) begin")], ["profile_bit_100", "profile_blank"]),
    ("tag_core.v", "the CRC's polynomial wrong", [("& 8'h07);", "& 8'h1D);")], ["nominal"]),
    ("tag_core.v", "the EUI-48's address wrong", [("loader_step = 8'hFA;", "loader_step = 8'hF9;")], ["nominal"]),
    ("tag_core.v", "the EEPROM's address wrong", [("parameter [6:0] EEPROM_I2C_ADDRESS = 7'h50,", "parameter [6:0] EEPROM_I2C_ADDRESS = 7'h60,")], ["nominal"]),
    ("tag_core.v", "only 7 bytes of the profile read", [("? PROFILE_READS : {3'd0, step[3:1]};", "? {3'd0, step[3:1]} : {3'd0, step[3:1]};")], ["nominal"]),
    ("tag_core.v", "the EUI-48 not kept", [("assign adv_address_cfg = adv_r;", "assign adv_address_cfg = ADV_ADDRESS;")], ["nominal"]),
    ("tag_core.v", "half an EUI-48 kept when its read fails", [("if (rst || eui_rejected) begin", "if (rst) begin")], ["eui_interrupted"]),
    ("tag_core.v", "the EUI-48's bits reversed", [("adv_r <= {adv_r[46:0], bus_rx_bit};", "adv_r <= {bus_rx_bit, adv_r[47:1]};")], ["nominal"]),
    ("tag_core.v", "TxAdd of the profile ignored", [("assign tx_add = eui_ok ? cfg_radio[6] : (TX_ADD != 0);", "assign tx_add = (TX_ADD != 0);")], ["nominal"]),
    ("tag_core.v", "TX_ADD not used without the EUI-48", [("assign tx_add = eui_ok ? cfg_radio[6] : (TX_ADD != 0);", "assign tx_add = cfg_radio[6];")], ["eeprom_absent"]),
    ("tag_core.v", "the channel of the profile ignored", [(".channel_number(cfg_radio[5:0]),", ".channel_number(6'd37),")], ["channel_38"]),
    ("tag_core.v", "the interval of the profile ignored", [("interval_count <= cfg_interval;", "interval_count <= 16'd100;")], ["test_mode"]),
    ("tag_core.v", "the prescaler not restarted", [("      prescale <= 5'd0;\n      interval_count <= cfg_interval;", "      interval_count <= cfg_interval;")], ["nominal", "test_mode"]),
    ("tag_core.v", "the unit not 32 ticks", [("(prescale == 5'd31)", "(prescale == 5'd30)")], ["nominal"]),
    ("tag_core.v", "no advDelay", [("wait_count <= lfsr;", "wait_count <= 8'd0;")], ["nominal"]),
    ("tag_core.v", "the LFSR not stepped", [("            lfsr <= lfsr_next;\n", "")], ["nominal"]),
    ("tag_core.v", "the LFSR's seed not AdvA", [("lfsr <= adv_address_sent[7:0];", "lfsr <= 8'h01;")], ["nominal"]),
    ("tag_core.v", "the LFSR can stick at 0", [("^ (lfsr[6:0] == 7'd0)};", "};")], ["test_mode_wraps_all_delays"]),
    ("tag_core.v", "WAIT one unit short", [("          if (wait_count == 8'd0) begin\n            state <= ST_FETCH;", "          if (wait_count <= 8'd1) begin\n            state <= ST_FETCH;")], ["nominal"]),
    ("tag_core.v", "no clocks in the bus clear", [("if (bus_done) state <= ST_CLEAR_READ;", "if (bus_done) state <= ST_CLEAR_STOP;")], ["reset_read_measure_150", "reset_read_measure_400", "reset_read_measure_700"]),
    ("tag_core.v", "no STOP before the bus clear's clocks", [("if (adv_address_otp_ready) state <= ST_CLEAR_FIRST;", "if (adv_address_otp_ready) state <= ST_CLEAR_READ;")], ["reset_stop_measure_20"]),
    ("tag_core.v", "failed not cleared", [("      ST_END: begin\n        failed <= 1'b0;", "      ST_END: begin")], ["sensor_nack"]),
    ("tag_core.v", "no 0xFF when the sensor does not answer", [("sensor_r <= failed ? {(8*SENSOR_BYTES){1'b1}} : capture_value;", "sensor_r <= capture_value;")], ["sensor_nack"]),
    ("tag_core.v", "the acknowledge ignored", [("if (!bus_spi && !bus_adc && !bus_acked) begin", "if (1'b0) begin")], ["sensor_nack"]),
    ("tag_core.v", "no bus timeout", [("wire bus_timeout = bus_stalled && ms_pulse && (wait_count == 8'd0);", "wire bus_timeout = 1'b0;")], ["scl_stuck"]),
    ("tag_core.v", "the test mode ignored", [("if (cfg_test_mode) begin", "if (1'b0) begin")], ["test_mode"]),
    ("tag_core.v", "the test mode's counter stuck", [("sensor_r <= sensor_r + 1'b1;", "sensor_r <= sensor_r;")], ["test_mode"]),
    ("tag_core.v", "the measure program's start ignored", [("pc <= cfg_bus[4:0];", "pc <= 5'd6;")], ["long_boot_program"]),
    ("tag_core.v", "the profile's SPI choice in force while loading", [("wire bus_spi = cfg_bus[5] && !bus_i2c;", "wire bus_spi = cfg_bus[5];")], ["spi_mode0_read_only"]),
    ("tag_core.v", "the capture not cleared between events", [(".clear(event_start),", ".clear(rst),")], ["nominal"]),
    ("tag_core.v", "tx_start held during the packet", [("wire tx_start = (state == ST_TX);", "wire tx_start = (state == ST_TX) || (state == ST_TX_WAIT);")], ["nominal"]),
    ("tag_core.v", "the second capture reads the first's window", [("cfg[8*(PROFILE_BYTES-7-4*c) +: 8];", "cfg[8*(PROFILE_BYTES-7) +: 8];")], ["two_sensor_bytes"]),
    ("tag_core.v", "the MTP's address stuck", [("if (bits_left == 4'd1) index <= index + 6'd1;", "")], ["cfg_mtp"]),
    ("tag_core.v", "the profile's byte of the MTP's bits in the wrong order", [("assign profile_bit = shift[7];", "assign profile_bit = shift[0];")], ["cfg_mtp"]),
]


def run_scenario(s: Scenario, work: Path, tag: str = "dut", texts: dict[str, str] | None = None):
    rng = random.Random(zlib_hash(s.name))
    sim = build_args(s.build, work, tag, texts)
    run = simulate(s, sim, work)
    rows, verdict = check(s, run, rng)
    cover = set()
    for line in (run / "cover.txt").read_text().splitlines():
        kind, a, b = line.split()
        cover.add((kind, int(a), int(b)))
    return rows, verdict, cover


def zlib_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", help="comma-separated scenario names (or prefixes)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--output", type=Path, help="the packets, for check_tag_scapy.py")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--mutant", help="only the mutants whose description holds this text")
    a = parser.parse_args()
    all_scenarios = scenarios()
    if a.list:
        print("\n".join(s.name for s in all_scenarios))
        return
    m = re.search(r"parameter \[255:0\] DEFAULT_PROFILE = 256'h([0-9a-fA-F_]+)", (ROOT / "verilog/tag_core.v").read_text())
    if not m or bytes.fromhex(m.group(1)) != tag_profile.default_image():
        raise SystemExit("FAIL: tag_core.v's DEFAULT_PROFILE is not tag_profile.py's default")
    print("tag_core.v's DEFAULT_PROFILE is tag_profile.py's default")
    chosen = all_scenarios
    if a.only:
        wanted = a.only.split(",")
        chosen = [s for s in all_scenarios if any(s.name == w or s.name.startswith(w) for w in wanted)]
    with tempfile.TemporaryDirectory(prefix="tag-core-") as temp:
        work = Path(temp)

        def one(s):
            try:
                return s, run_scenario(s, work), None
            except Mismatch as e:
                return s, None, f"MISMATCH {e}"
            except Exception as e:     # noqa: BLE001  a crash is reported, and fails the run
                return s, None, f"ERROR {e}"

        rows, coverage, failures = [], set(), 0
        for s in {sc.build for sc in chosen}:
            build_args(s, work, "dut", None)     # compiled once, before the pool
        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
            for s, result, error in pool.map(one, chosen):
                if error:
                    failures += 1
                    print(f"{s.name}: FAIL: {error}", flush=True)
                else:
                    r, verdict, cover = result
                    rows += r
                    coverage |= cover
                    print(f"{s.name}: {verdict}", flush=True)
        if failures:
            raise SystemExit(f"FAIL: {failures} of {len(chosen)} scenarios")
        print(f"scenarios: {len(chosen)}, pass {len(chosen)}")
        if not a.only:
            missing = sorted(required_coverage() - coverage)
            print(f"coverage: {len(required_coverage())} (phase, state) and (command, bus phase) required, "
                  f"{len(required_coverage()) - len(missing)} reached")
            if missing:
                raise SystemExit(f"FAIL: not reached: {missing}")
        if a.output:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(rows, indent=1) + "\n")
        if a.mutants:
            texts = {f: (ROOT / "verilog" / f).read_text() for f in RTL}
            by_name = {s.name: s for s in all_scenarios}
            caught = errors = 0

            def mutant(index):
                f, label, edits, names = MUTANTS[index]
                mutated = dict(texts)
                for old, new in edits:
                    if mutated[f].count(old) != 1:
                        return index, "ERROR", f"text not found once in {f}: {old!r}"
                    mutated[f] = mutated[f].replace(old, new)
                for name in names:
                    try:
                        run_scenario(by_name[name], work, f"m{index}", mutated)
                    except Mismatch as e:
                        return index, "CAUGHT", f"{name}: {e}"
                    except RuntimeError as e:
                        if "does not compile" in str(e):
                            return index, "ERROR", str(e)[:300]
                        return index, "ERROR", f"{name}: {e}"
                return index, "NOT CAUGHT", ", ".join(names)

            chosen_mutants = [i for i in range(len(MUTANTS)) if not a.mutant or a.mutant in MUTANTS[i][1]]
            with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                for index, verdict, line in pool.map(mutant, chosen_mutants):
                    f, label, _, _ = MUTANTS[index]
                    print(f"mutant {index + 1} ({f}: {label}): {verdict}: {line[:220]}", flush=True)
                    if verdict == "CAUGHT":
                        caught += 1
                    elif verdict == "ERROR":
                        errors += 1
            print(f"mutants caught: {caught}/{len(chosen_mutants)}")
            if caught != len(chosen_mutants):
                raise SystemExit("FAIL")
    print("PASS")


if __name__ == "__main__":
    main()
