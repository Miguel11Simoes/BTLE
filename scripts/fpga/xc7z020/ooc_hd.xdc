# Mode ooc_hd of impl.tcl: out of context, where the clocks come from (HD.CLK_SRC, a global buffer per
# clock); without it Vivado warns that it cannot time clock delay and skew (Timing 38-242, Route 35-197).
# impl.tcl sets HD.PARTPIN_RANGE on the ports that reach a cell (Route 35-198) and deasserts the resets in
# the power analysis (Power 33-332).
set_property HD.CLK_SRC BUFGCTRL_X0Y0 [get_ports bb_clk]
set_property HD.CLK_SRC BUFGCTRL_X0Y1 [get_ports rf_clk]
set_property HD.CLK_SRC BUFGCTRL_X0Y2 [get_ports s00_axi_aclk]
set_property HD.CLK_SRC BUFGCTRL_X0Y3 [get_ports bram_clk_a]
