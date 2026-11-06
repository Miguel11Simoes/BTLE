"""The board's files of ble-tx-poc against the RTL: what can be checked without Vivado 2022.2 and ADI's IP.

Author: Miguel Simões

The bitstream needs Vivado 2022.2 and ADI's HDL (fpga/README.md), so the block design is not built here. These are the
checks that do not need them, on fpga/antsdr:
- the tag's external ports of src/system.bd exist on btle_controller (verilog/btle_controller.v), with its direction, and
  its nets join each to the controller's pin of the same name;
- src/system_wrapper.v and src/system_top.v carry them (the top elaborated with Icarus Verilog against stubs of the block
  design, of ADI's ad_iobuf and of Xilinx's IOBUF, generated from the wrapper's own instance): SCL and SDA are open-drain,
  an IOBUF with I = 0 and T = !oe, on gpio_bd[0] and gpio_bd[1], and gpio_bd[3:0] have left the PS's GPIO;
- src/system_no_ila.xdc places those pins, without internal pull-ups, with no timing on them, and names no cell of the
  receiver this branch does not have; src/system.xdc's ILA probes name nets that the RTL has;
- verilog/btle_controller.tcl lists every RTL file the controller needs, so that the IP's project has them.

  python3 tests/test_poc_board_files.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "fpga/antsdr/src"
TAG_PORTS = {"tag_scl_i": "I", "tag_sda_i": "I", "tag_miso_i": "I", "tag_scl_oe": "O", "tag_sda_oe": "O", "tag_cs_n": "O"}


def fail(message: str) -> None:
    sys.exit(f"FAIL: {message}")


def main() -> None:
    design = json.loads((BOARD / "system.bd").read_text())["design"]
    controller = (ROOT / "verilog/btle_controller.v").read_text()
    for port, direction in TAG_PORTS.items():
        if design["ports"].get(port, {}).get("direction") != direction:
            fail(f"system.bd: port {port}, direction {design['ports'].get(port)}")
        declared = "input" if direction == "I" else "output"
        if not re.search(rf"{declared}\s+wire\s+{port}\b", controller):
            fail(f"btle_controller.v: no {declared} {port}")
        nets = [n for n, v in design["nets"].items() if set(v["ports"]) == {port, f"btle_controller_0/{port}"}]
        if len(nets) != 1:
            fail(f"system.bd: the net of {port}: {nets}")
    print(f"system.bd: {len(TAG_PORTS)} ports of the tag, each with a net to the controller's pin of its direction")

    wrapper = (BOARD / "system_wrapper.v").read_text()
    top = (BOARD / "system_top.v").read_text()
    instance = re.search(r"system\s+system_i\s*\((.*?)\);", wrapper, re.S).group(1)
    pins = re.findall(r"\.(\w+)\(", instance)
    for port in TAG_PORTS:
        if port not in pins or f"{port}," not in wrapper or not re.search(rf"\.{port}\s*\({port}\)", top):
            fail(f"{port} is not carried through system_wrapper.v and system_top.v")
    for text in ("IOBUF i_tag_scl (.I (1'b0), .T (!tag_scl_oe), .O (tag_scl_i), .IO (gpio_bd[0]));",
                 "IOBUF i_tag_sda (.I (1'b0), .T (!tag_sda_oe), .O (tag_sda_i), .IO (gpio_bd[1]));",
                 "assign gpio_bd[2] = tag_cs_n;", "assign tag_miso_i = gpio_bd[3];",
                 ".dio_p (gpio_bd[10:4]));", "assign gpio_i[3:0] = gpio_o[3:0];"):
        if text not in top:
            fail(f"system_top.v: {text}")
    print("system_wrapper.v, system_top.v: the ports carried; SCL and SDA open-drain on gpio_bd[1:0], CS_n and MISO on gpio_bd[3:2]")

    # elaborate the top against stubs
    widths = {name: width for width, name in re.findall(r"^\s*(?:inout|input|output)\s*(\[[^\]]+\])?\s*(\w+);", wrapper, re.M)}
    stub = "module system (" + ", ".join(pins) + ");\n"
    for pin in pins:
        stub += f"  inout {widths.get(pin, '')} {pin};\n"
    stub += "endmodule\n"
    stub += """module ad_iobuf #(parameter DATA_WIDTH = 1) (input [DATA_WIDTH-1:0] dio_t, input [DATA_WIDTH-1:0] dio_i,
  output [DATA_WIDTH-1:0] dio_o, inout [DATA_WIDTH-1:0] dio_p);
endmodule
module IOBUF (output O, inout IO, input I, input T);
  assign IO = T ? 1'bz : I;
  assign O = IO;
endmodule
"""
    cad = Path(os.environ.get("OSS_CAD", str(Path.home() / "eda/oss-cad-suite-20260907"))) / "bin"
    with tempfile.TemporaryDirectory(prefix="poc-board-") as temp:
        work = Path(temp)
        (work / "stubs.v").write_text(stub)
        # upstream's top declares its band-select outputs again as wires: Vivado takes it, Icarus Verilog does not
        (work / "top.v").write_text(re.sub(r"^\s*wire\s+[rt]x[12]_band_sel_[hl];\n", "", top, flags=re.M))
        run = subprocess.run([str(cad / "iverilog"), "-g2012", "-Wimplicit", "-s", "system_top", "-o", str(work / "top.vvp"),
                              str(work / "top.v"), str(BOARD / "system_wrapper.v"), str(work / "stubs.v")],
                             capture_output=True, text=True)
        if run.returncode != 0 or re.search(r"tag_\w+.*(implicit|not a port|Unable)", run.stderr):
            fail(f"the top does not elaborate:\n{run.stderr[-1500:]}")
    print("system_top.v elaborates with its wrapper (Icarus Verilog, stubs of the block design and of the IO buffers)")

    no_ila = (BOARD / "system_no_ila.xdc").read_text()
    if "btle_rx_i" in no_ila:
        fail("system_no_ila.xdc names cells of the receiver")
    for k in range(4):
        if not re.search(r"PACKAGE_PIN \w+ IOSTANDARD LVCMOS33\} \[get_ports \{gpio_bd\[" + str(k) + r"\]\}\]", no_ila):
            fail(f"system_no_ila.xdc: gpio_bd[{k}] not placed at 3.3 V")
    for text in ("set_property PULLTYPE NONE [get_ports {gpio_bd[0] gpio_bd[1] gpio_bd[3]}]",
                 "set_false_path -from [get_ports {gpio_bd[0] gpio_bd[1] gpio_bd[3]}]",
                 "set_false_path -to [get_ports {gpio_bd[0] gpio_bd[1] gpio_bd[2]}]"):
        if text not in no_ila:
            fail(f"system_no_ila.xdc: {text}")
    print("system_no_ila.xdc: the four pins at 3.3 V, no internal pull-up, no timing; no cell of the receiver named")

    ila = (BOARD / "system.xdc").read_text()
    core = (ROOT / "verilog/tag_core.v").read_text()
    bus = (ROOT / "verilog/tag_bus.v").read_text()
    prefix = "i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/"
    if "tag_core_i" not in (ROOT / "verilog/btle_phy.v").read_text():
        fail("btle_phy.v: no instance tag_core_i")
    named = set(re.findall(re.escape(prefix) + r"([\w/]+)", ila))
    if len(named) < 7:
        fail(f"system.xdc: the probes of the tag: {sorted(named)}")
    for net in named:
        scope, _, name = net.rpartition("/")
        text = bus if scope == "tag_bus_i" else core
        if not re.search(rf"(reg|wire)\s*(\[[^\]]*\]\s*)?{name}\b", text):
            fail(f"system.xdc: net {net} is not in the RTL")
    print(f"system.xdc: the ILA's {len(named)} nets of the tag are in the RTL: {', '.join(sorted(named))}")

    tcl = (ROOT / "verilog/btle_controller.tcl").read_text()
    for f in ("tag_core.v", "tag_bus.v", "tag_capture.v", "btle_tx.v"):
        if tcl.count(f'/{f}"') != 2:
            fail(f"btle_controller.tcl: {f}")
    print("btle_controller.tcl: the RTL files of the tag are in the IP's project")
    print("PASS")


if __name__ == "__main__":
    main()
