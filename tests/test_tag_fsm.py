"""tag_fsm of ble-tx-poc-gen, from each sensor's model to upstream's Python receiver.

Author: Miguel Simões

tests/tag_fsm_tb.v runs tag_fsm with the models of its four sensors (tests/tmp100_model.v, tmp114_model.v, max31875_model.v,
tmp126_model.v), written from their datasheets, one on the bus at a time, the pins sel choosing its profile, and a monitor
of the I2C bus (tests/i2c_timing_monitor.v). Each scenario below is one simulation; for every packet it sends, against what
the scenario implies:
- the sensor's two bytes: what the sensor's model really answered (its log), and, where the scenario knows them, from the
  temperature itself and back to it, with the conversion of that sensor, as the gateway does;
- the PHY bits: those of python/btlelib.py's btle_tx for the PDU of scripts/senseworks/tag_bch.py;
- upstream's Python receiver (btle_rx) decodes the I/Q, the CRC right, that PDU;
- the BCH code: the PDU is a codeword, and t errors at random are corrected back to it;
- T_advEvent, start to start: exactly the period less advDelay, in ticks and in time, advDelay from a model of the LFSR
  XOR AdvA's first byte;
- the sensor: in shutdown at every packet; no read during a conversion; its configuration at the end the one written.
The packets of the scenarios on the default code go to --output (JSON) for scripts/senseworks/check_tag_scapy.py.
verilog/tag_profiles.v must be what scripts/senseworks/tag_profile.py generates. The generality past the four: a build
with another table in place of the fourth, a SPI mode 0 sensor with no command (tests/spi_sensor_model.v).

Then: the coverage of the tables (every slot on the bus of every profile, over all the scenarios), and with --mutants the
deliberate faults, in the RTL and in the generator, each of which must fail a scenario with a concrete mismatch.

  python3 tests/test_tag_fsm.py [--only NAME[,NAME]] [--jobs N] [--mutants] [--output FILE] [--resume FILE]

With --resume, each result is appended to FILE, and a later run with the same RTL, models and test takes it from there: a
campaign survives the loss of its machine (WSL restarted while this was written). The log prints every result either way.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import threading

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from btlelib import btle_tx, btle_rx, hex_string_to_bit, bit_to_hex_string, crc24_core  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/senseworks"))
import tag_bch  # noqa: E402
import tag_profile  # noqa: E402

RTL = ["tag_fsm.v", "tag_profiles.v", "btle_tx.v", "crc24.v", "crc24_core.v", "scramble.v", "scramble_core.v", "gfsk_modulation.v",
       "bit_repeat_upsample.v", "gauss_filter.v", "vco.v"]
MODELS = ["tag_fsm_tb.v", "i2c_slave_model.v", "tmp100_model.v", "tmp114_model.v", "max31875_model.v", "tmp126_model.v",
          "spi_sensor_model.v", "i2c_timing_monitor.v", "efuse_async_mem_1x8_model.v"]
ROM_ADV = 0xC10203040506                 # tag_fsm's ADV_ADDRESS
CID = 0xFFFF
REAL_TICK_NS = 1.0e9 / 32768
SENSORS = tag_profile.DEFAULT
OTHER_TABLES = ["tmp100", "tmp114", "max31875", "max6675"]


class Mismatch(Exception):
    """The design did not do what the scenario implies: a concrete failure."""


@dataclass(frozen=True)
class Kind:
    """What a reading of each sensor looks like."""
    per_degree: int        # units of the 16-bit word per degC
    low_mask: int          # the low bits a reading always has at 0
    first_is_last: bool    # the first event's write only puts it in shutdown: the first packet is its last continuous conversion
    config: str            # the configuration at the end, after the conversion
    os_ignored_max: int


KINDS = {"tmp100": Kind(256, 0xFF80, True, "0081", 1), "tmp114": Kind(128, 0xFFFF, False, "000c", 0),
         "max31875": Kind(256, 0xFF80, True, "0120", 1), "tmp126": Kind(128, 0xFFFC, False, "000e", 0)}


@dataclass(frozen=True)
class Build:
    tick_div: int = 25
    bch: int = 8
    otp: int = 0
    adv: int = ROM_ADV
    channel: int = 37
    clk_half_ns: float = 31.25
    tables: tuple[str, ...] = tuple(SENSORS)

    def tick_ns(self) -> float:
        return self.tick_div * 2 * self.clk_half_ns

    def time_scale(self) -> float:
        """How much faster than the real tick the scenario runs; the models' times divide by it."""
        return REAL_TICK_NS / self.tick_ns()


@dataclass
class Scenario:
    name: str
    sensor: str = "tmp100"
    build: Build = Build()
    temps: list[float] = field(default_factory=lambda: [25.0])
    adv: int | None = None               # the AdvA expected: the build's unless programmed
    rate: int = 1
    events: int = 3
    max_ms: int = 3000
    plus: dict = field(default_factory=dict)
    expected: list[int] | None = None    # each packet's two bytes, when known a priori
    period: bool = True                  # T_advEvent checked
    rows: bool = True
    sensor_checks: bool = True           # the model's log
    from_reads: bool = True              # each packet what the log says was read
    scl_period_ns: float | None = None
    frames: tuple[int, int] | None = None  # the STARTs and STOPs the bus must see
    gap_ticks: tuple[int, int] | None = None  # between these packets, at least so many ticks more: the tag was off

    def sel(self) -> int:
        return list(self.build.tables).index(self.sensor)


def raw_of(sensor: str, t: float) -> int:
    """What the sensor answers for a temperature: its register, the bits it does not give at 0."""
    k = KINDS[sensor]
    return (int(round(t * k.per_degree)) & 0xFFFF) & k.low_mask


def after_first(sensor: str, temps: list[float]) -> list[int]:
    if KINDS[sensor].first_is_last:
        return [raw_of(sensor, temps[0])] + [raw_of(sensor, t) for t in temps]
    return [raw_of(sensor, t) for t in temps]


def build_sim(build: Build, work: Path, tag: str, texts: dict[str, str] | None) -> Path:
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
        if f == "tag_profiles.v" and build.tables != tuple(SENSORS):
            path.write_text(tag_profile.verilog(list(build.tables)))
        else:
            path.write_text(texts[f] if texts and f in texts else (ROOT / "verilog" / f).read_text())
        files.append(str(path))
    files += [str(ROOT / "tests" / f) for f in MODELS]
    defs = [f"-DTICK_DIV={build.tick_div}", f"-DBCH={build.bch}", f"-DOTP={build.otp}",
            f"-DCHANNEL={build.channel}", f"-DCLK_HALF_NS={build.clk_half_ns}", f"-DROM_ADV=48'h{build.adv:012x}",
            f"-DCID=16'h{CID:04x}"]
    result = subprocess.run([os.environ.get("IVERILOG", "iverilog"), "-g2012", "-s", "tag_fsm_tb", "-o", str(out),
                             *defs, *files], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"does not compile:\n{result.stdout}{result.stderr}")
    return out


def simulate(s: Scenario, sim: Path, work: Path) -> Path:
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=work))
    (run_dir / "temps.hex").write_text("".join(f"{round(t * 16) & 0xFFFF:04x}\n" for t in s.temps))
    (run_dir / "spi_values.hex").write_text("".join(f"{v:04x}\n" for v in s.plus.get("values", [0])))
    plus = {"events": s.events, "max_ms": s.max_ms, "time_scale": s.build.time_scale(), "rate": s.rate, "sel": s.sel(),
            **{k: v for k, v in s.plus.items() if k != "values"}}
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


def lfsr_sequence(n: int) -> list[int]:
    values, l = [], 0
    for _ in range(n):
        values.append(l)
        l = ((l << 1) & 0xFF) | (((l >> 7) ^ (l >> 5) ^ (l >> 4) ^ (l >> 3) ^ int((l & 0x7F) == 0)) & 1)
    return values


def check(s: Scenario, run: Path, rng: random.Random) -> tuple[list[dict], str]:
    b = s.build
    t = b.bch
    adv_expected = s.adv if s.adv is not None else b.adv
    events, aborted, reset_index = [], set(), None
    for line in (run / "events.txt").read_text().splitlines():
        f = line.split()
        if f[0] == "tx":
            events.append(dict(packet=int(f[1]), ns=float(f[2]), ticks=int(f[3]), sensor=int(f[4], 16), adv=int(f[5], 16),
                               shutdown=int(f[6]), channel=int(f[7])))
        elif f[0] == "reset":
            reset_index = int(f[1])
            if int(f[4]):
                aborted.add(int(f[1]))
    done = [e for e in events if e["packet"] not in aborted]
    if len(done) < s.events - len(aborted):
        raise Mismatch(f"{len(done)} packets completed, {s.events} expected")
    # what the sensor answered
    kind = KINDS.get(s.sensor)
    log_file = run / f"{s.sensor}.log"
    log = log_file.read_text().splitlines() if log_file.exists() else []
    reads = [(float(l.split()[1]), int(l.split()[2], 16), int(l.split()[3])) for l in log if l.startswith("read")]
    tables = {n: np.loadtxt(run / f"{n}.txt", dtype=int, ndmin=2) for n in ("iq", "bits")}
    crc_init = hex_string_to_bit("555555")
    rows = []
    previous = -1.0
    for k, e in enumerate(events):
        window = [r for r in reads if previous < r[0] < e["ns"]]
        previous = e["ns"]
        settled = reset_index is None or e["packet"] < reset_index or e["packet"] > reset_index + 1  # the first after it may be wrong
        if s.expected is not None and settled:
            if e["sensor"] != s.expected[k]:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, expected {s.expected[k]:04x}")
        elif s.from_reads and settled and kind:
            want = window[-1][1] if window else 0xFFFF
            if e["sensor"] != want:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, the sensor answered {want:04x}")
            if e["sensor"] != 0xFFFF and e["sensor"] & ~kind.low_mask & 0xFFFF:
                raise Mismatch(f"packet {e['packet']}: sensor {e['sensor']:04x}, its low bits are 0 in a reading")
        if s.sensor_checks and kind and window and settled and not e["shutdown"]:
            raise Mismatch(f"packet {e['packet']}: the sensor is not in shutdown")
        if e["adv"] != adv_expected or e["channel"] != b.channel:
            raise Mismatch(f"packet {e['packet']}: AdvA {e['adv']:012x} channel {e['channel']}; expected {adv_expected:012x} {b.channel}")
        if e["packet"] in aborted:
            continue
        sensor = e["sensor"].to_bytes(2, "big")
        pdu = tag_bch.tag_pdu(adv_expected, sensor, t, CID, 1)
        pdu_bits = hex_string_to_bit(pdu.hex())
        i, q, bits, _ = btle_tx(pdu_bits, b.channel, crc_init, "D6BE898E")
        got_bits = tables["bits"][tables["bits"][:, 0] == e["packet"]][:, 1]
        if not np.array_equal(got_bits, bits):
            raise Mismatch(f"packet {e['packet']}: the PHY bits are not those of the PDU {pdu.hex()}")
        got_iq = tables["iq"][tables["iq"][:, 0] == e["packet"]][:, 1:]
        if got_iq.shape[0] != len(i):
            raise Mismatch(f"packet {e['packet']}: {got_iq.shape[0]} samples, {len(i)} expected")
        decoded = btle_rx(got_iq[:, 0], got_iq[:, 1], b.channel, crc_init, "D6BE898E")
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
        if s.rows and t == 8:
            rows.append(dict(scenario=s.name, t=t, sensor_bytes=2, tx_add=1, channel=b.channel, sensor=sensor.hex(),
                             access_address="8e89bed6", pdu=pdu.hex(),
                             crc_bits="".join(str(int(v)) for v in crc24_core(pdu_bits, crc_init))))
    # T_advEvent, exact in ticks and in time
    if s.period:
        delays = lfsr_sequence(len(events) + 1)
        for k in range(1, len(events)):
            ticks = events[k]["ticks"] - events[k - 1]["ticks"]
            want = (1 << (11 + s.rate)) - (delays[k - 1] ^ (adv_expected & 0xFF))
            if s.gap_ticks and k == s.gap_ticks[0]:
                if ticks < s.gap_ticks[1]:
                    raise Mismatch(f"{ticks} ticks across the time off, at least {s.gap_ticks[1]} expected")
                continue
            if ticks != want:
                raise Mismatch(f"T_advEvent between packets {k - 1} and {k}: {ticks} ticks, expected {want}")
            ns = events[k]["ns"] - events[k - 1]["ns"]
            if abs(ns - want * b.tick_ns()) > 1:
                raise Mismatch(f"T_advEvent between packets {k - 1} and {k}: {ns} ns, {want * b.tick_ns()} expected")
    # the model's log
    verdict = (run / "verdict.txt").read_text().strip()
    if s.sensor_checks and kind:
        partial = [l for l in log if l.startswith("partial")]
        if partial and reset_index is None:
            raise Mismatch(f"a frame not of whole words: {partial[0]}")
        no_pointer = [l for l in log if l.startswith("no_pointer")]
        if no_pointer and reset_index is None:
            raise Mismatch(f"a read with no pointer written: {no_pointer[0]}")
        written = [l for l in log if l.startswith("write_readonly")]
        if written and reset_index is None:
            raise Mismatch(f"a byte written with the pointer on the temperature: {written[0]}")
        ignored = [l for l in log if l.startswith("os_ignored")]
        allowed = kind.os_ignored_max + (1 if reset_index is not None else 0)
        if len(ignored) > allowed:
            raise Mismatch(f"{len(ignored)} one-shots written outside shutdown: {ignored[-1]}")
        stale = [r for r in reads if r[2] and r[0] > (events[0]["ns"] if events else 0)]
        if stale:
            raise Mismatch(f"the temperature read during a conversion at {stale[0][0]} ns")
        if reads and f"config {kind.config}," not in verdict:
            raise Mismatch(f"the configuration at the end is not {kind.config}: {verdict}")
    if s.scl_period_ns is not None:
        low, high = map(float, re.search(r"SCL period, between ([\d.]+) and ([\d.]+) ns", verdict).groups())
        if abs(low - s.scl_period_ns) > 1 or abs(high - s.scl_period_ns) > 1:
            raise Mismatch(f"SCL period between {low} and {high} ns, expected {s.scl_period_ns}")
    if s.frames is not None:
        got = tuple(map(int, re.search(r"(\d+) STARTs, (\d+) STOPs", verdict).groups()))
        if got != s.frames:
            raise Mismatch(f"{got[0]} STARTs and {got[1]} STOPs on the bus, expected {s.frames[0]} and {s.frames[1]}")
    return rows, verdict


# ------------------------------------------------------------------------------------------------- the scenarios
def spots(sensor: str, n: int) -> list[int]:
    """n places in the sensor's table where its slots are on the bus, spread over them."""
    table = tag_profile.table(tag_profile.sensors()[sensor])
    busy = [k for k, c in enumerate(table) if c != tag_profile.IDLE]
    return [busy[k * (len(busy) - 1) // (n - 1)] for k in range(n)]


def scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    sweep = [25.0, -40.0, -40.5, -55.0, 0.0, 87.0, 87.5, 125.0, -0.5, 30.0]
    for sensor in SENSORS:
        spi = sensor == "tmp126"
        monitor = {"i2c_monitor": 0} if spi else {}
        # the temperature's range, the sign, a period of each end of the rates; the bus's timing
        n = len(after_first(sensor, sweep))
        out.append(Scenario(f"{sensor}_nominal", sensor, temps=sweep, events=n, expected=after_first(sensor, sweep), plus=monitor,
                            scl_period_ns=6250.0 if sensor == "tmp100" else None))
        out.append(Scenario(f"{sensor}_one_second", sensor, rate=4, temps=[21.5, 22.0], events=2, expected=after_first(sensor, [21.5, 22.0])[:2],
                            plus=monitor, max_ms=4000))
        out.append(Scenario(f"{sensor}_conversion_typical", sensor, temps=[10.0, 11.0], events=2, plus={"conv_mode": 1, **monitor},
                            expected=after_first(sensor, [10.0, 11.0])[:2]))
        # no sensor, and a sensor that stops answering and comes back: 0xFFFF, the packets go on
        out.append(Scenario(f"{sensor}_absent", sensor, temps=[20.0], events=3, plus={"present": 0, **monitor}, expected=[0xFFFF] * 3))
        out.append(Scenario(f"{sensor}_nack", sensor, temps=[20.0, 21.0, 22.0, 23.0], events=6, plus={"nack_from": 2, "nack_to": 4, **monitor}))
        # a reset anywhere in the frames, and in the packet: at most one packet wrong, then right, the sensor as configured
        temps = [8.0, 6.0, 7.0, 5.0, 4.0, 3.0, 2.0]
        for slot in spots(sensor, 16):
            for phase in (0, 2):
                out.append(Scenario(f"{sensor}_reset_s{slot}_p{phase}", sensor, temps=temps, events=5, rows=False, period=False,
                                    plus={"reset_packet": 1, "reset_t": slot * 4 + phase, "i2c_monitor": 0}))
        out.append(Scenario(f"{sensor}_reset_in_packet", sensor, temps=temps, events=5, rows=False, period=False,
                            plus={"reset_packet": 1, "reset_t": -1, "i2c_monitor": 0}))
    # a line stuck low: nothing hangs, the packets go on
    out.append(Scenario("scl_stuck", temps=[40.0, 41.0, 42.0], events=6, plus={"stuck_scl_from": 1, "stuck_scl_to": 3, "i2c_monitor": 0}))
    out.append(Scenario("sda_stuck", temps=[40.0, 41.0, 42.0], events=6, from_reads=False,
                        expected=[raw_of("tmp100", 40.0), 0x0000, 0x0000, raw_of("tmp100", 40.0), raw_of("tmp100", 41.0), raw_of("tmp100", 42.0)],
                        plus={"stuck_sda_from": 1, "stuck_sda_to": 3, "i2c_monitor": 0}))
    # the channel, the codes: parameters; AdvA in the eFuse blocks; AdvA's first byte is advDelay's XOR: the two ends
    for channel in (38, 39):
        out.append(Scenario(f"channel_{channel}", build=Build(channel=channel), temps=[15.0, 16.0], events=2))
    for bch in (12, 18):
        out.append(Scenario(f"bch_{bch}", build=Build(bch=bch), temps=[25.0, 26.0], events=2, rows=False))
    otp_adv = 0xD1E2A3B4C5F6
    out.append(Scenario("adv_efuse", build=Build(otp=1), temps=[12.0, 13.0], events=3, adv=otp_adv, plus={"otp_prog": f"{otp_adv:012x}"}))
    out.append(Scenario("adv_first_byte_00", build=Build(adv=0xC10203040500), temps=[12.0], events=3))
    out.append(Scenario("adv_first_byte_ff", build=Build(adv=0xC102030405FF), temps=[12.0], events=3))
    # every rate; the conversion fits in the shortest; start to start exact in each
    for rate in range(1, 8):
        out.append(Scenario(f"rate_{rate}", rate=rate, temps=[-5.0, 1.0, 2.0], events=3, max_ms=4000,
                            expected=after_first("tmp100", [-5.0, 1.0])))
    # off: nothing on the bus or on the air; back on, the same
    out.append(Scenario("rate_off_and_on", rate=4, temps=[1.0, 2.0, 3.0], events=4, max_ms=4000,
                        plus={"off_after": 2, "off_ticks": 100000, "on_rate": 4}, gap_ticks=(2, 100000)))
    # the test mode: a counter, no bus; all the delays and the wrap of the LFSR
    out.append(Scenario("test_mode", temps=[20.0], events=8, plus={"test_mode": 1, "i2c_monitor": 0},
                        expected=list(range(1, 9)), sensor_checks=False, from_reads=False))
    out.append(Scenario("test_mode_wraps_all_delays", temps=[20.0], events=260, plus={"test_mode": 1, "i2c_monitor": 0},
                        expected=list(range(1, 261)), rows=False, sensor_checks=False, from_reads=False, max_ms=6000))
    # past the four: another table in the fourth place, SPI mode 0, no command, nothing but a read: the same RTL
    values = [(int(t * 4) << 3) for t in (25.0, 0.0, 19.0, 150.0, 20.5)]
    out.append(Scenario("other_table_spi_mode0", "max6675", build=Build(tables=tuple(OTHER_TABLES)), temps=[20.0], events=5,
                        expected=values, from_reads=False, sensor_checks=False,
                        plus={"spi_model": 1, "i2c_monitor": 0, "values": values}))
    # the ASIC's clock: 32.768 kHz, a tick per clock; the sensors of each bus
    # (with no switch to 16 MHz here, the packet takes 3840 of those clocks: a period of 1 s leaves room for it)
    for sensor in ("tmp100", "tmp126"):
        monitor = {"i2c_monitor": 0} if sensor == "tmp126" else {}
        out.append(Scenario(f"{sensor}_asic_clock", sensor, build=Build(tick_div=1, clk_half_ns=15258.789), rate=4, temps=[25.0, -20.0, 60.0],
                            events=3, max_ms=8000, expected=after_first(sensor, [25.0, -20.0, 60.0])[:3], plus={"t_out_ns": 900, **monitor}))
    return out


# ------------------------------------------------------------------------------------------------- the coverage
def required_coverage() -> set[tuple[str, int, int]]:
    need = set()
    for sel, sensor in enumerate(SENSORS):
        for k, c in enumerate(tag_profile.table(tag_profile.sensors()[sensor])):
            if c != tag_profile.IDLE:
                need.add(("slot", sel, k))
    return need


# ------------------------------------------------------------------------------------------------- the mutants
# (file, what the fault is, edits, scenarios: one of them must fail with a concrete mismatch)
MUTANTS = [
    ("tag_profile.py", "TMP100: no shutdown", [("i2c_write(0x48, [0x01, 0x81])", "i2c_write(0x48, [0x01, 0x80])")], ["tmp100_nominal"]),
    ("tag_profile.py", "TMP100: no one-shot", [("i2c_write(0x48, [0x01, 0x81])", "i2c_write(0x48, [0x01, 0x01])")], ["tmp100_nominal"]),
    ("tag_profile.py", "TMP100: the wait too short", [("wait_ms(75)", "wait_ms(40)")], ["tmp100_nominal"]),
    ("tag_profile.py", "TMP100: the pointer not back on the temperature", [("i2c_write(0x48, [0x00])", "i2c_write(0x48, [0x01])")], ["tmp100_nominal"]),
    ("tag_profile.py", "TMP114: no one-shot", [("[0x03, 0x00, 0x1C]", "[0x03, 0x00, 0x0C]")], ["tmp114_nominal"]),
    ("tag_profile.py", "TMP114: the wait too short", [("tmp114 = i2c_write(0x48, [0x03, 0x00, 0x1C]) + wait_ms(7.5)", "tmp114 = i2c_write(0x48, [0x03, 0x00, 0x1C]) + wait_ms(2)")], ["tmp114_nominal"]),
    ("tag_profile.py", "TMP114: the read's pointer wrong", [("byte_slots(pointer) + [W1]", "byte_slots(0x03) + [W1]")], ["tmp114_nominal"]),
    ("tag_profile.py", "MAX31875: no shutdown", [("[0x01, 0x01, 0x21]", "[0x01, 0x00, 0x21]")], ["max31875_nominal"]),
    ("tag_profile.py", "MAX31875: no one-shot", [("[0x01, 0x01, 0x21]", "[0x01, 0x01, 0x20]")], ["max31875_nominal"]),
    ("tag_profile.py", "MAX31875: 10 bits", [("[0x01, 0x01, 0x21]", "[0x01, 0x01, 0x41]")], ["max31875_nominal"]),
    ("tag_profile.py", "TMP126: no one-shot", [("[0x0003, 0x001E]", "[0x0003, 0x000E]")], ["tmp126_nominal"]),
    ("tag_profile.py", "TMP126: the wait too short", [("tmp126 = spi_frame([0x0003, 0x001E]) + wait_ms(7.5)", "tmp126 = spi_frame([0x0003, 0x001E]) + wait_ms(2)")], ["tmp126_nominal"]),
    ("tag_profile.py", "TMP126: the read's command a write", [("spi_frame([0x0100], read_bits=16)", "spi_frame([0x0000], read_bits=16)")], ["tmp126_nominal"]),
    ("tag_profile.py", "the last byte read acknowledged", [("slots += [W0] if k < count - 1 else [W1]", "slots += [W0]")], ["tmp100_nominal"]),
    ("tag_profile.py", "a byte read not kept", [("[KEEP if k in keep else W1] * 8", "[KEEP if k == 0 else W1] * 8")], ["tmp100_nominal"]),
    ("tag_fsm.v", "SPI: SDA not released once SCLK has risen", [("(is_bit && code[0] && !(spi && phase[1]))", "(is_bit && code[0])")], ["tmp126_nominal"]),
    ("tag_fsm.v", "SPI: SDA pulled low in the STOP, the sensor still driving it", [("(!spi && ((is_start", "(1'b1 && ((is_start")], ["tmp126_nominal"]),
    ("tag_fsm.v", "CS_n stays high", [("assign cs_n = !(spi && cs_low);", "assign cs_n = 1'b1;")], ["tmp126_nominal"]),
    ("tag_fsm.v", "CS_n low with I2C too", [("assign cs_n = !(spi && cs_low);", "assign cs_n = !cs_low;")], ["tmp100_nominal"]),
    ("tag_fsm.v", "CS_n rises after the STOP's clock", [("cs_low <= (code != 3'd0) && !is_stop;", "cs_low <= (code != 3'd0);")], ["tmp126_nominal"]),
    ("tag_fsm.v", "SPI mode 0 ignored", [("wire scl_low = cpol0 ? !(is_bit && !low_phase) : scl_low_i2c;", "wire scl_low = scl_low_i2c;")], ["other_table_spi_mode0"]),
    ("tag_fsm.v", "the pins sel ignored", [(".sel(sel),", ".sel(2'd0),")], ["tmp114_nominal"]),
    ("tag_fsm.v", "sampled with SCL low", [("is_bit && code[1] && (phase == 2'd2)", "is_bit && code[1] && (phase == 2'd0)")], ["tmp100_nominal"]),
    ("tag_fsm.v", "the bytes swapped on the air", [(".sensor({sensor_r[7:0], sensor_r[15:8]})", ".sensor(sensor_r)")], ["tmp100_nominal"]),
    ("tag_fsm.v", "SDA changes with SCL high", [("(is_bit && low_phase);", "(is_bit && !low_phase);")], ["tmp100_nominal"]),
    ("tag_fsm.v", "no START: SDA does not fall", [("(is_start && (phase != 2'd0))", "1'b0")], ["tmp100_nominal"]),
    ("tag_fsm.v", "no STOP: SDA stays low", [("(is_stop && !phase[1])", "is_stop")], ["tmp100_nominal"]),
    ("tag_fsm.v", "SCL does not fall after START", [("(is_start && (phase == 2'd3))", "1'b0")], ["tmp100_nominal"]),
    ("tag_fsm.v", "no advDelay", [("t <= {t_high, lfsr ^ adv_address_sent[7:0]};", "t <= {t_high, 8'd0};")], ["tmp100_nominal"]),
    ("tag_fsm.v", "advDelay not XOR AdvA", [("lfsr ^ adv_address_sent[7:0]", "lfsr")], ["tmp100_nominal"]),
    ("tag_fsm.v", "the LFSR not stepped", [("if (wrap) lfsr <= ", "if (1'b0) lfsr <= ")], ["tmp100_nominal"]),
    ("tag_fsm.v", "the LFSR stepped every tick", [("if (wrap) lfsr <= ", "lfsr <= ")], ["tmp100_nominal"]),
    ("tag_fsm.v", "the LFSR can stick at 0", [("^ (lfsr[6:0] == 7'd0)};", "};")], ["tmp100_nominal"]),
    ("tag_fsm.v", "the LFSR's feedback short of 256 states", [("lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3] ^", "lfsr[7] ^ lfsr[5] ^ lfsr[4] ^")], ["test_mode_wraps_all_delays"]),
    ("tag_fsm.v", "the tick a clock short", [("localparam integer DIV_LAST_INT = TICK_DIV - 1;", "localparam integer DIV_LAST_INT = TICK_DIV - 2;")], ["tmp100_nominal"]),
    ("tag_fsm.v", "off ignored", [("wire off = (rate == 3'd0);", "wire off = 1'b0;")], ["rate_off_and_on", "test_mode"]),
    ("tag_fsm.v", "off still sends", [("assign tx_start = wrap && tick && !off;", "assign tx_start = tick && (wrap || (off && (t[7:0] == 8'd0)));")], ["rate_off_and_on"]),
    ("tag_fsm.v", "the test mode's bus not silent", [("&t[17:12] && !test_mode && !off;", "&t[17:12] && !off;")], ["test_mode"]),
    ("tag_fsm.v", "the test mode's counter stuck", [("else if (test_mode && wrap) sensor_r <= sensor_r + 1'b1;", "")], ["test_mode"]),
    ("tag_fsm.v", "the test mode's counter not cleared", [("if (test_mode && off) begin", "if (1'b0) begin")], ["test_mode"]),
    ("tag_fsm.v", "the channel ignored", [(".channel_number(CHANNEL),", ".channel_number(6'd37),")], ["channel_38"]),
] + [
    ("tag_fsm.v", f"rate {rate} wrong", [(f"(rate == 3'd{rate}) ? 6'b{bits}", f"(rate == 3'd{rate}) ? 6'b{other}")], [f"rate_{rate}"])
    for rate, bits, other in ((2, "111110", "111100"), (3, "111100", "111000"), (4, "111000", "110000"), (5, "110000", "100000"),
                              (6, "100000", "000000"), (7, "000000", "100000"))
] + [
    ("tag_fsm.v", "rate 1 wrong", [("6'b111111;    // 125 ms", "6'b111110;    // 125 ms")], ["rate_1"]),
]


class Resume:
    """The results so far, valid only for the same RTL, models, generator and test."""

    def __init__(self, path: Path | None):
        self.path, self.done, self.lock = path, {}, threading.Lock()
        files = [ROOT / "verilog" / f for f in RTL] + [ROOT / "tests" / f for f in MODELS] + [Path(__file__), Path(tag_profile.__file__)]
        self.key = hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()
        if path and path.exists():
            for line in path.read_text().splitlines():
                try:
                    r = json.loads(line)
                except ValueError:      # the last line of a run that was cut
                    continue
                if r["key"] == self.key:
                    self.done[r["name"]] = r["value"]

    def get(self, name: str):
        return self.done.get(name)

    def put(self, name: str, value) -> None:
        if self.path:
            with self.lock, self.path.open("a") as f:
                f.write(json.dumps(dict(key=self.key, name=name, value=value)) + "\n")


def mutated_profiles(text: str) -> str:
    """The tables a mutated generator makes."""
    namespace = {"__name__": "tag_profile_mutant", "__file__": "tag_profile_mutant"}
    sys.modules.setdefault("tag_profile_mutant", type(sys)("tag_profile_mutant"))
    sys.modules["tag_profile_mutant"].__dict__.update(namespace)
    exec(compile(text, "tag_profile_mutant", "exec"), sys.modules["tag_profile_mutant"].__dict__)
    return sys.modules["tag_profile_mutant"].__dict__["verilog"](SENSORS)


def run_scenario(s: Scenario, work: Path, tag: str = "dut", texts: dict[str, str] | None = None):
    rng = random.Random(int(hashlib.sha256(s.name.encode()).hexdigest()[:8], 16))
    sim = build_sim(s.build, work, tag, texts)
    run = simulate(s, sim, work)
    rows, verdict = check(s, run, rng)
    cover = set()
    for line in (run / "cover.txt").read_text().splitlines():
        kind, a, b = line.split()
        cover.add((kind, int(a), int(b)))
    return rows, verdict, cover


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", help="comma-separated scenario names (or prefixes)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--mutants", action="store_true")
    parser.add_argument("--output", type=Path, help="the packets, for check_tag_scapy.py")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--mutant", help="only the mutants whose description holds this text")
    parser.add_argument("--resume", type=Path, help="keep the results here, and take those of an earlier run")
    a = parser.parse_args()
    all_scenarios = scenarios()
    if a.list:
        print("\n".join(s.name for s in all_scenarios))
        return
    if (ROOT / "verilog/tag_profiles.v").read_text() != tag_profile.verilog(SENSORS):
        raise SystemExit("FAIL: verilog/tag_profiles.v is not what scripts/senseworks/tag_profile.py generates")
    print("verilog/tag_profiles.v is what scripts/senseworks/tag_profile.py generates")
    chosen = all_scenarios
    if a.only:
        wanted = a.only.split(",")
        chosen = [s for s in all_scenarios if any(s.name == w or s.name.startswith(w) for w in wanted)]
    resume = Resume(a.resume)
    with tempfile.TemporaryDirectory(prefix="tag-fsm-") as temp:
        work = Path(temp)

        def one(s):
            kept = resume.get(s.name)
            if kept:
                return s, (kept["rows"], kept["verdict"], {tuple(c) for c in kept["cover"]}), None
            try:
                r, verdict, cover = run_scenario(s, work)
                resume.put(s.name, dict(rows=r, verdict=verdict, cover=sorted(cover)))
                return s, (r, verdict, cover), None
            except Mismatch as e:
                return s, None, f"MISMATCH {e}"
            except Exception as e:     # noqa: BLE001  a crash is reported, and fails the run
                return s, None, f"ERROR {e}"

        rows, coverage, failures = [], set(), 0
        for s in {sc.build for sc in chosen if not resume.get(sc.name)}:
            build_sim(s, work, "dut", None)     # compiled once, before the pool
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
            print(f"coverage: {len(required_coverage())} (profile, slot) required, {len(required_coverage()) - len(missing)} reached")
            if missing:
                raise SystemExit(f"FAIL: not reached: {missing[:12]} and {max(0, len(missing) - 12)} more")
        if a.output:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(rows, indent=1) + "\n")
        if a.mutants:
            texts = {f: (ROOT / "verilog" / f).read_text() for f in RTL}
            generator = (ROOT / "scripts/senseworks/tag_profile.py").read_text()
            by_name = {s.name: s for s in all_scenarios}
            caught = 0
            exec_lock = threading.Lock()

            def mutant(index):
                kept = resume.get(f"mutant {index}")
                if kept:
                    return index, kept[0], kept[1]
                result = mutant_run(index)
                if result[1] == "CAUGHT":
                    resume.put(f"mutant {index}", result[1:])
                return result

            def mutant_run(index):
                f, label, edits, names = MUTANTS[index]
                mutated = dict(texts)
                source = generator if f == "tag_profile.py" else mutated[f]
                for old, new in edits:
                    if source.count(old) != 1:
                        return index, "ERROR", f"text not found once in {f}: {old!r}"
                    source = source.replace(old, new)
                if f == "tag_profile.py":
                    with exec_lock:
                        mutated["tag_profiles.v"] = mutated_profiles(source)
                else:
                    mutated[f] = source
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
            print(f"mutants caught: {caught}/{len(chosen_mutants)}")
            if caught != len(chosen_mutants):
                raise SystemExit("FAIL")
    print("PASS")


if __name__ == "__main__":
    main()
