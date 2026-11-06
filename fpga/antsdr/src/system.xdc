# Author: Xianjun Jiao
# SPDX-FileCopyrightText: 2025 Xianjun Jiao <putaoshu@msn.com>
# SPDX-License-Identifier: Apache-2.0

# ila (might be auto upated by vivado)

create_debug_core u_ila_0 ila
set_property ALL_PROBE_SAME_MU true [get_debug_cores u_ila_0]
set_property ALL_PROBE_SAME_MU_CNT 1 [get_debug_cores u_ila_0]
set_property C_ADV_TRIGGER false [get_debug_cores u_ila_0]
set_property C_DATA_DEPTH 65536 [get_debug_cores u_ila_0]
set_property C_EN_STRG_QUAL false [get_debug_cores u_ila_0]
set_property C_INPUT_PIPE_STAGES 0 [get_debug_cores u_ila_0]
set_property C_TRIGIN_EN false [get_debug_cores u_ila_0]
set_property C_TRIGOUT_EN false [get_debug_cores u_ila_0]
set_property port_width 1 [get_debug_ports u_ila_0/clk]
connect_debug_port u_ila_0/clk [get_nets [list i_system_wrapper/system_i/clk_wiz_1/inst/clk_out2]]
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe0]
set_property port_width 1 [get_debug_ports u_ila_0/probe0]
connect_debug_port u_ila_0/probe0 [get_nets [list {i_system_wrapper/system_i/btle_controller_0/inst/btle_ll_i/ll_gpio[0]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe1]
set_property port_width 15 [get_debug_ports u_ila_0/probe1]
connect_debug_port u_ila_0/probe1 [get_nets [list {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[0]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[1]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[2]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[3]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[4]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[5]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[6]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[7]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[8]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[9]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[10]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[11]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[12]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[13]} {i_system_wrapper/system_i/btle_controller_0/inst/auxiliary_daemon_i/bram_addr_b[14]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe2]
set_property port_width 1 [get_debug_ports u_ila_0/probe2]
connect_debug_port u_ila_0/probe2 [get_nets [list i_system_wrapper/system_i/btle_controller_0/inst/btle_ll_i/bram_addr_b_half_flag]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe3]
set_property port_width 1 [get_debug_ports u_ila_0/probe3]
connect_debug_port u_ila_0/probe3 [get_nets [list i_system_wrapper/system_i/btle_controller_0/inst/ll_itrpt2]]
# ble-tx-poc: the tag's state machine and its bus, on the same ILA (16 MHz, 65536 samples: 4 ms, a bus transaction)
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe4]
set_property port_width 4 [get_debug_ports u_ila_0/probe4]
connect_debug_port u_ila_0/probe4 [get_nets [list {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/state[0]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/state[1]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/state[2]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/state[3]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe5]
set_property port_width 2 [get_debug_ports u_ila_0/probe5]
connect_debug_port u_ila_0/probe5 [get_nets [list {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/ph[0]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/ph[1]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe6]
set_property port_width 5 [get_debug_ports u_ila_0/probe6]
connect_debug_port u_ila_0/probe6 [get_nets [list {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/pc[0]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/pc[1]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/pc[2]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/pc[3]} {i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/pc[4]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe7]
set_property port_width 3 [get_debug_ports u_ila_0/probe7]
connect_debug_port u_ila_0/probe7 [get_nets [list i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/tag_bus_i/scl_oe i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/tag_bus_i/sda_oe i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/tag_bus_i/active]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe8]
set_property port_width 2 [get_debug_ports u_ila_0/probe8]
connect_debug_port u_ila_0/probe8 [get_nets [list i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/scl_i i_system_wrapper/system_i/btle_controller_0/inst/btle_phy_i/tag_core_i/sda_i]]
set_property C_CLK_INPUT_FREQ_HZ 300000000 [get_debug_cores dbg_hub]
set_property C_ENABLE_CLK_DIVIDER false [get_debug_cores dbg_hub]
set_property C_USER_SCAN_CHAIN 1 [get_debug_cores dbg_hub]
connect_debug_port dbg_hub/clk [get_nets u_ila_0_clk_out2]
