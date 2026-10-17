# btle_controller out of context on xc7z020clg484-1. bb_clk: the baseband, 16 MHz; rf_clk: the AD9361 IQ
# interface, 8 MHz, the documented 2:1 relation with bb_clk (one group); the AXI-lite registers and the
# IQ-capture BRAM's PS port at 100 MHz (a Zynq FCLK), asynchronous to the baseband (clk_cross_bus).
create_clock -name bb_clk   -period 62.500 [get_ports bb_clk]
create_clock -name rf_clk   -period 125.000 [get_ports rf_clk]
create_clock -name axi_clk  -period 10.000 [get_ports s00_axi_aclk]
create_clock -name bram_clk -period 10.000 [get_ports bram_clk_a]
set_clock_groups -asynchronous -group {bb_clk rf_clk} -group axi_clk -group bram_clk
