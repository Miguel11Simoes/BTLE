#!/usr/bin/env python3
"""The figures of open_btle_baseband_chip/, redone with the ble-tx-min RTL as the transmitter.

Author: Miguel Simões

Run from the repository root in WSL (Icarus in OSS_CAD, NumPy, Matplotlib):

  python3 scripts/figures/tx_min_figures.py tx   OUT_DIR   # py-fig3 and py-fig4 with the RTL transmitter
  python3 scripts/figures/tx_min_figures.py ber  OUT_DIR [--packets N] [--realizations R]   # the BER curves, 50 and -30 ppm
  python3 scripts/figures/tx_min_figures.py area OUT_DIR AREA_JSON       # the transmitter area per branch

The transmitter is verilog/btle_tx.v with GAUSS_TABLE = 1 (as the branch is measured), run by the
upstream testbench verilog/btle_tx_tb.v plus a monitor of the upsampled bit and the Gaussian filter
output; everything after it (channel, receiver) is python/btlelib.py, as in the upstream figures.
Each RTL waveform is also compared with python/btlelib.py's btle_tx: the figures print the number of
differing samples (0 expected). py-fig3 and py-fig4 are drawn twice: for upstream's own packet
(example 2 of test_vector_for_btle_verilog.py, the one in open_btle_baseband_chip/py-fig3.png and
py-fig4.png, so both figures cover the same 640 samples) and for a Legacy Advertising PDU of 39 bytes
(suffix _adv). The BER packets are Legacy Advertising PDUs (channel 37, the advertising access
address and CRC init) with the chip's AdvA, ADV_ADDRESS of verilog/btle_tx.v.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import btlelib as bl  # noqa: E402

CAD = Path(os.environ.get("OSS_CAD", str(Path.home() / "eda/oss-cad-suite-20260907"))) / "bin"
CHANNEL, AA, CRC_INIT = 37, "D6BE898E", "555555"
# AdvData of upstream's BER packet (test_btle_ber.py): AD local name "SDR/Bluetooth/Low/Energy" + 5 bytes
ADV_DATA = bytes.fromhex("19095344522f426c7565746f6f74682f4c6f772f456e657267791234567890")
# Upstream's py-fig3/py-fig4: `python test_vector_for_btle_verilog.py 2` (20 dB, 0 ppm), a data packet
# with an empty payload (LLID 1, length 0): 80 bits, 640 samples. Its 2 bytes never reach AdvA (bytes 2..7).
EXAMPLE2 = dict(pdu=bytes.fromhex("0100"), channel=10, aa="1B0A8511", crc_init="123456", snr=20, ppm=0)

TRACE = r"""
`timescale 1ns/1ps
module tx_trace;
  integer fu, fg;
  initial begin fu = $fopen("trace_upsample.txt", "w"); fg = $fopen("trace_gauss.txt", "w"); end
  always @(posedge btle_tx_tb.clk) begin
    if (btle_tx_tb.btle_tx_i.bit_upsample_valid) $fwrite(fu, "%0d\n", btle_tx_tb.btle_tx_i.bit_upsample);
    if (btle_tx_tb.btle_tx_i.bit_upsample_gauss_filter_valid) $fwrite(fg, "%0d\n", btle_tx_tb.btle_tx_i.bit_upsample_gauss_filter);
  end
endmodule
"""


def adv_address() -> bytes:
    """AdvA as sent, PDU bytes 2..7 (ADV_ADDRESS of btle_tx.v, least significant byte first)."""
    text = (ROOT / "verilog/btle_tx.v").read_text()
    m = re.search(r"parameter \[47:0\] ADV_ADDRESS = 48'h([0-9a-fA-F_]+)", text)
    return bytes.fromhex(m.group(1).replace("_", "").rjust(12, "0"))[::-1]


def adv_pdu(adv_data: bytes) -> bytes:
    """ADV_NONCONN_IND (type 2, TxAdd 1): header, AdvA, AdvData; at most 39 bytes."""
    payload = adv_address() + adv_data
    assert len(payload) <= 37
    return bytes([0x42, len(payload)]) + payload


class RtlTx:
    """verilog/btle_tx.v (GAUSS_TABLE = 1) under the upstream TX testbench, one packet per call."""

    def __init__(self, work: Path):
        self.work = work
        rtl = work / "rtl"
        shutil.copytree(ROOT / "verilog", rtl, ignore=shutil.ignore_patterns("*.txt", "*.vcd"))
        f = rtl / "btle_tx.v"
        text, n = re.subn(r"(parameter integer GAUSS_TABLE = )\d+", r"\g<1>1", f.read_text())
        assert n == 1
        f.write_text(text)
        tb = rtl / "btle_tx_tb.v"
        tb.write_text(re.sub(r"^\s*\$dump(?:file|vars)\b[^;]*;", "", tb.read_text(), flags=re.M))
        (rtl / "tx_trace.v").write_text(TRACE)
        files = [str(p) for p in rtl.glob("*.v") if not p.name.endswith("_tb.v")
                 and p.name not in {"btle_controller_wrapper.v", "sdpram_two_clk_xilinx.v"}]
        self.sim = work / "sim"
        compile_result = subprocess.run(
            [str(CAD / "iverilog"), "-s", "btle_tx_tb", "-s", "tx_trace", "-o", str(self.sim), str(tb), *files],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if compile_result.returncode:
            raise RuntimeError(
                f"Icarus compilation failed ({compile_result.returncode}):\n"
                f"{compile_result.stdout}{compile_result.stderr}"
            )
        self.taps = np.int8(np.round(128 * bl.gauss_fir_gen()))
        self.cos, self.sin = bl.sin_cos_gen(64)

    def run(self, pdu: bytes, tag: str, channel: int = CHANNEL, aa: str = AA, crc_init: str = CRC_INIT) -> dict:
        d = self.work / f"run_{tag}"
        d.mkdir()
        for name, data in [("gauss_filter_tap", self.taps), ("cos_table", self.cos), ("sin_table", self.sin)]:
            np.savetxt(d / (name + ".txt"), data, fmt="%d")
        pdu_bit = bl.hex_string_to_bit(pdu.hex())
        i, q, phy_bit, phy_bit_upsample = bl.btle_tx(pdu_bit, channel, bl.hex_string_to_bit(crc_init), aa)
        (d / "btle_config.txt").write_text(f"{len(pdu_bit):x}\n{channel:x}\n{crc_init}\n{aa}\n")
        (d / "btle_tx_test_input.txt").write_text("".join(f"{v:02x}\n" for v in pdu))
        np.savetxt(d / "btle_tx_test_output_i_ref.txt", i, fmt="%d")
        np.savetxt(d / "btle_tx_test_output_q_ref.txt", q, fmt="%d")
        r = subprocess.run([str(CAD / "vvp"), "-n", str(self.sim)], cwd=d, capture_output=True, text=True, timeout=120)
        if r.returncode or "output I Test PASS." not in r.stdout or "output Q Test PASS." not in r.stdout:
            raise RuntimeError(f"RTL TX failed for {pdu.hex()}:\n{r.stdout[-2000:]}{r.stderr[-500:]}")
        out = dict(pdu_bit=pdu_bit, py_i=i, py_q=q, py_upsample=phy_bit_upsample,
                   i=np.loadtxt(d / "btle_tx_test_output_i.txt", dtype=int),
                   q=np.loadtxt(d / "btle_tx_test_output_q.txt", dtype=int),
                   upsample=np.loadtxt(d / "trace_upsample.txt", dtype=int),
                   gauss=np.loadtxt(d / "trace_gauss.txt", dtype=int))
        n = min(len(out["i"]), len(i))
        out["differences"] = int(np.sum(out["i"][:n] != i[:n]) + np.sum(out["q"][:n] != q[:n]) + abs(len(out["i"]) - len(i)))
        shutil.rmtree(d)
        return out


def style(ax, title):
    ax.grid(True)
    ax.legend(loc="upper right")
    ax.set_title(title)


def fig_tx(out_dir: Path) -> None:
    adv = dict(pdu=adv_pdu(ADV_DATA), channel=CHANNEL, aa=AA, crc_init=CRC_INIT, snr=20, ppm=20)
    with tempfile.TemporaryDirectory(prefix="tx-min-fig-") as t:
        rtl = RtlTx(Path(t))
        summary = {
            "example2": _fig_pair(out_dir, rtl, EXAMPLE2, "",
                                  f"upstream's example 2: PDU 0100 (data, empty payload), channel {EXAMPLE2['channel']}"),
            "adv": _fig_pair(out_dir, rtl, adv, "_adv", f"PDU {len(adv['pdu'])} bytes (ADV, AdvA from ROM), channel {CHANNEL}"),
        }
    (out_dir / "tx_min_figures_tx.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


def _fig_pair(out_dir: Path, rtl: RtlTx, pkt: dict, suffix: str, what: str) -> dict:
    """py-fig3 and py-fig4 for one packet, the RTL as the transmitter."""
    pdu, channel, aa, crc_init = pkt["pdu"], pkt["channel"], pkt["aa"], pkt["crc_init"]
    r = rtl.run(pdu, "fig" + suffix, channel, aa, crc_init)
    i, q = r["i"].astype(float), r["q"].astype(float)
    fo, _ = bl.check_realtime_fo(i, q)
    note = f"RTL ble-tx-min, {what}; RTL vs Python: {r['differences']} samples differ"

    # py-fig3: signals in the transmitter
    plt.figure(0, figsize=(6.4, 4.8))
    ax = plt.subplot(211)
    ax.plot(2 * r["upsample"] - 1, "b", label="Upsampled phy bit")
    ax.plot(r["gauss"][8:] / 128.0, "r", label="Guass filter out")
    ax.plot(fo[6:], "k--", label="Normalized freq offset")
    style(ax, "Signals in BTLE transmitter (ble-tx-min RTL)")
    ax = plt.subplot(212)
    ax.plot(i[8:], "b", label="I")
    ax.plot(q[8:], "r", label="Q")
    style(ax, "BTLE transmitter I and Q (ble-tx-min RTL)")
    plt.figtext(0.5, 0.005, note, ha="center", fontsize=7)
    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig(out_dir / f"tx_min_py_fig3{suffix}.png", dpi=100)
    plt.close()

    # py-fig4: the receiver's decision signal, after the channel
    rng_state = np.random.get_state()
    np.random.seed(20261016)
    i_err, q_err, _, _ = bl.add_freq_sampling_error(i, q, pkt["ppm"])
    rx_i, rx_q = bl.add_noise(i_err, q_err, pkt["snr"])
    np.random.set_state(rng_state)
    rx_pdu_bit, crc_ok, num_byte_payload, _, _, _, best = bl.btle_rx(rx_i, rx_q, channel, bl.hex_string_to_bit(crc_init), aa)
    plt.figure(1, figsize=(6.4, 4.8))
    ax = plt.subplot(211)
    ax.plot(2 * r["upsample"] - 1, "b", label="Upsampled phy bit")
    ax.plot(r["gauss"][8:] / 128.0, "r", label="Guass filter out")
    ax.plot(fo[6:], "k--", label="Normalized freq offset")
    style(ax, "Signals in BTLE transmitter (ble-tx-min RTL)")
    ax = plt.subplot(212)
    ii, qq = np.int16(rx_i), np.int16(rx_q)
    n_sig = round(len(ii) / bl.SAMPLE_PER_SYMBOL) - 1
    sig = np.zeros(n_sig * bl.SAMPLE_PER_SYMBOL, dtype=np.int32)
    idx = np.arange(len(sig))
    for ph in range(bl.SAMPLE_PER_SYMBOL):
        _, s = bl.gfsk_demodulation_fixed_point(ii[ph::bl.SAMPLE_PER_SYMBOL], qq[ph::bl.SAMPLE_PER_SYMBOL])
        s = np.concatenate((s, [s[-1]] * (n_sig - len(s)))) if len(s) < n_sig else s[:n_sig]
        sig[ph::bl.SAMPLE_PER_SYMBOL] = s
    ax.plot(idx - 4, sig, "b", label="signal for decision")
    ax.plot(idx[best::bl.SAMPLE_PER_SYMBOL] - 4, sig[best::bl.SAMPLE_PER_SYMBOL], "rs", label="best phase moment")
    style(ax, "signal for decision in receiver")
    ok = crc_ok and bl.bit_to_hex_string(rx_pdu_bit) == pdu.hex()
    plt.figtext(0.5, 0.005, f"channel {pkt['snr']} dB SNR, {pkt['ppm']} ppm; Python receiver: CRC {'OK' if crc_ok else 'FAIL'}, "
                f"PDU {'equal to the one sent' if ok else 'DIFFERENT'} ({num_byte_payload} payload bytes)",
                ha="center", fontsize=7)
    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig(out_dir / f"tx_min_py_fig4{suffix}.png", dpi=100)
    plt.close()
    return dict(pdu=pdu.hex(), channel=channel, access_address=aa, crc_init=crc_init, snr_db=pkt["snr"], ppm=pkt["ppm"],
                rtl_vs_python_differences=r["differences"], samples=len(i),
                rx_crc_ok=bool(crc_ok), rx_pdu_equal=bool(ok), best_phase=int(best))


# ---- BER: RTL transmitter vs Python transmitter, same channel noise ----
# The channel and the receiver are upstream's python/btlelib.py (tag upstream-baseline), as in
# open_btle_baseband_chip/: its btle_rx returns the demodulated PDU even when the CRC fails, so the
# BER counts the bits that differ. (The audited btlelib.py returns no PDU on a CRC failure, which
# would count a whole packet as wrong: a packet error rate, not a BER.)
_UP = None


def _upstream():
    global _UP
    if _UP is None:
        import importlib.util
        d = Path(os.environ["BTLE_UPSTREAM_PY"])
        os.chdir(d)  # it writes its debug files to ../verilog
        spec = importlib.util.spec_from_file_location("btlelib_upstream", d / "btlelib.py")
        _UP = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_UP)
    return _UP


def _rx_errors(args):
    i, q, pdu_bit, ppm, snr, seed = args
    up = _upstream()
    np.random.seed(seed)
    i_err, q_err, _, fo = up.add_freq_sampling_error(i, q, ppm)
    rx_i, rx_q = up.add_noise(i_err, q_err, snr)
    rx_pdu_bit, crc_ok, _, _, _, _, _ = up.btle_rx(rx_i, rx_q, CHANNEL)
    if crc_ok:
        return 0, len(pdu_bit)
    if len(rx_pdu_bit) == 0:
        return len(pdu_bit), len(pdu_bit)
    m = min(len(pdu_bit), len(rx_pdu_bit))
    return int(np.sum(pdu_bit[:m] != rx_pdu_bit[:m])), len(pdu_bit)


def _seed(realization: int, ppm: int, s_idx: int, k: int) -> int:
    """The noise seed of packet k; realization 0 is the one first published (2026-10-16)."""
    return 10_000_000 * realization + 1000 * s_idx + k + (ppm + 100) * 100000


def fig_ber(out_dir: Path, packets: int, realizations: int) -> None:
    """The same packets and, in each realization, the same noise for the RTL and the Python transmitter.

    Realization 0 is the comparison of the figures; the others only show how much the BER of these
    packet counts moves from one noise draw to another (upstream's script draws a new one at every
    run), drawn as the band between the lowest and the highest realization of the RTL.
    """
    counts = [packets // 3, 2 * packets // 3, packets, packets]  # upstream's 100, 200, 300, 300
    rng = np.random.default_rng(8675309)
    with tempfile.TemporaryDirectory(prefix="tx-min-ber-") as t:
        rtl = RtlTx(Path(t))
        waves = []
        for k in range(max(counts)):
            pdu = adv_pdu(rng.integers(0, 256, 31, dtype=np.uint8).tobytes())  # random AdvData, the chip's AdvA
            r = rtl.run(pdu, str(k))
            if r["differences"]:
                raise RuntimeError(f"packet {k}: RTL and Python transmitters differ")
            waves.append((r["i"].astype(float), r["q"].astype(float), r["py_i"], r["py_q"], r["pdu_bit"]))
    # BTLE_UPSTREAM_PY, if set: the python/ of upstream-baseline already extracted (and a sibling
    # verilog/), for a worktree whose git does not run here (a Windows worktree under WSL)
    if "BTLE_UPSTREAM_PY" not in os.environ:
        up_dir = Path(tempfile.mkdtemp(prefix="btle-upstream-py-"))
        arc = subprocess.run(["git", "-C", str(ROOT), "archive", "upstream-baseline", "python"], stdout=subprocess.PIPE, check=True)
        subprocess.run(["tar", "-x", "-C", str(up_dir)], input=arc.stdout, check=True)
        (up_dir / "verilog").mkdir()
        os.environ["BTLE_UPSTREAM_PY"] = str(up_dir / "python")
    results = {}
    for ppm in (50, -30):
        ppm_abs = np.array([0, 10, 20, 25, 30, 35, 40, 45, 50])
        max_snr = np.array([11, 12, 13, 14, 15, 17, 19, 21, 26])
        snr0 = float(np.interp(abs(ppm), ppm_abs, max_snr))
        snrs = [snr0 - 4, snr0 - 2.5, snr0 - 1, snr0]
        runs = []  # runs[r] = {"rtl": [...], "python": [...]}, one entry per SNR
        with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 1, 16)) as pool:
            for r in range(realizations):
                curves = {"rtl": [], "python": []}
                for s_idx, snr in enumerate(snrs):
                    for side, (a, b) in (("rtl", (0, 1)), ("python", (2, 3))):
                        jobs = [(waves[k][a], waves[k][b], waves[k][4], ppm, snr, _seed(r, ppm, s_idx, k))
                                for k in range(counts[s_idx])]
                        err = tot = 0
                        for e, n in pool.map(_rx_errors, jobs, chunksize=8):
                            err += e
                            tot += n
                        curves[side].append(dict(snr=snr, ber=err / tot, bits=tot, errors=err))
                    if curves["rtl"][-1] != curves["python"][-1]:
                        raise RuntimeError(f"ppm {ppm} snr {snr} realization {r}: RTL and Python BER differ")
                print(f"ppm {ppm} realization {r}: errors {[c['errors'] for c in curves['rtl']]} (RTL = Python)", flush=True)
                runs.append(curves)
        results[ppm] = dict(runs[0], realizations=dict(
            count=realizations, seed="10000000 * realization + 1000 * snr_index + packet + (ppm + 100) * 100000",
            rtl_equals_python_in_every_realization=True,
            errors=[[c["errors"] for c in run["rtl"]] for run in runs]))
        _ber_stats(results[ppm])
    (out_dir / "tx_min_figures_ber.json").write_text(json.dumps(results, indent=2) + "\n")
    plot_ber(out_dir, results)


def _ber_stats(res: dict) -> None:
    """The band (min, median, max of the realizations) and the mean: all the realizations' errors over
    all their bits, the BER's estimate (a rare packet whose access address is missed adds 312 errors,
    so the median of small draws lies below it)."""
    rz = res["realizations"]
    bits = np.array([c["bits"] for c in res["rtl"]])
    err = np.array(rz["errors"])  # realizations x SNR
    ber = err / bits
    rz.update(ber_min=ber.min(axis=0).tolist(), ber_median=np.median(ber, axis=0).tolist(),
              ber_max=ber.max(axis=0).tolist(), ber_mean=(err.sum(axis=0) / (bits * len(err))).tolist())


def plot_ber(out_dir: Path, results: dict) -> None:
    """The figures from the results of fig_ber (tx_min_figures_ber.json): no simulation."""
    for ppm, res in results.items():
        _ber_stats(res)
        rz = res["realizations"]
        snrs = [c["snr"] for c in res["rtl"]]
        counts = [c["bits"] // 312 for c in res["rtl"]]
        plt.figure(figsize=(6.4, 4.8))
        if rz["count"] > 1:
            plt.fill_between(snrs, np.maximum(rz["ber_min"], 1e-7), rz["ber_max"], color="0.85",
                             label=f"range over {rz['count']} noise realizations")
            plt.semilogy(snrs, rz["ber_mean"], "k:", linewidth=1.5, label=f"mean of {rz['count']} realizations (the BER)")
        plt.semilogy(snrs, [max(c["ber"], 1e-7) for c in res["rtl"]], "b+-", markersize=10, label="TX: ble-tx-min RTL")
        plt.semilogy(snrs, [max(c["ber"], 1e-7) for c in res["python"]], "rx--", markersize=8, label="TX: upstream's Python model")
        plt.title(f"BER (Bit Error Rate) with ppm {ppm}")
        plt.xlabel("SNR(dB)")
        plt.ylabel("BER")
        plt.grid()
        plt.legend(loc="upper right", fontsize=8)
        plt.figtext(0.5, 0.005, f"39-byte ADV PDUs, random AdvData, {counts} packets per SNR\n"
                    f"the two lines: the same packets and noise (realization 0); RTL = Python in all {rz['count']}",
                    ha="center", fontsize=7)
        plt.tight_layout(rect=(0, 0.05, 1, 1))
        plt.savefig(out_dir / f"tx_min_ber_ppm{ppm}.png", dpi=100)
        plt.close()


# ---- the transmitter's area per branch ----
def fig_area(out_dir: Path, area_json: Path) -> None:
    rows = json.loads(area_json.read_text())  # [{"branch", "logic", "macros"}], measured
    names = [r["branch"] for r in rows]
    logic = np.array([r["logic"] for r in rows])
    macros = np.array([r["macros"] for r in rows])
    blue, orange = "#2a78d6", "#eb6834"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1.2, 1]))
    for ax, sel, title in ((axes[0], range(len(rows)), "Transmitter area, every option measured"),
                           (axes[1], [k for k, r in enumerate(rows) if r.get("zoom")], "The smallest, enlarged")):
        sel = list(sel)
        y = np.arange(len(sel))[::-1]
        ax.barh(y, logic[sel], color=blue, height=0.6, label="logic (std cells)", edgecolor="#fcfcfb", linewidth=2)
        ax.barh(y, macros[sel], left=logic[sel], color=orange, height=0.6, label="SRAM macros", edgecolor="#fcfcfb", linewidth=2)
        for yy, k in zip(y, sel):
            ax.text(logic[k] + macros[k], yy, f"  {logic[k] + macros[k]:,.0f}", va="center", fontsize=8, color="#0b0b0b")
        ax.set_yticks(y)
        ax.set_yticklabels([names[k] for k in sel], fontsize=8)
        ax.set_xlabel("µm² (Nangate45 cells + OpenRAM FreePDK45 macros)")
        ax.set_title(title, fontsize=10)
        ax.set_xlim(0, (logic[sel] + macros[sel]).max() * 1.22)
        ax.grid(axis="x", color="#e5e4e0")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "tx_min_area.png", dpi=120)
    plt.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("figure", choices=("tx", "ber", "ber-plot", "area"),
                   help="ber-plot: the BER figures again from out_dir/tx_min_figures_ber.json, no simulation")
    p.add_argument("out_dir", type=Path)
    p.add_argument("area_json", type=Path, nargs="?")
    p.add_argument("--packets", type=int, default=300)
    p.add_argument("--realizations", type=int, default=20, help="noise draws for the BER (draw 0 is the first published one)")
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    if a.figure == "tx":
        fig_tx(a.out_dir)
    elif a.figure == "ber":
        fig_ber(a.out_dir, a.packets, a.realizations)
    elif a.figure == "ber-plot":
        f = a.out_dir / "tx_min_figures_ber.json"
        results = json.loads(f.read_text())
        plot_ber(a.out_dir, results)
        f.write_text(json.dumps(results, indent=2) + "\n")
    else:
        fig_area(a.out_dir, a.area_json)


if __name__ == "__main__":
    main()
