* static power of sram_1rw_8x256 deselected, settled (sram_leakage.py)
.include "/home/msmiguel/venvs/openram/lib/python3.11/site-packages/openram/technology/freepdk45/models/tran_models/models_nom/PMOS_VTG.inc"
.include "/home/msmiguel/venvs/openram/lib/python3.11/site-packages/openram/technology/freepdk45/models/tran_models/models_nom/NMOS_VTG.inc"
.include "/tmp/btle_sramleak.dprPea/sram_1rw_8x256/leak/netlist.sp"
Vvdd vdd 0 1.0
Xsram_1rw_8x256 din0_0 din0_1 din0_2 din0_3 din0_4 din0_5 din0_6 din0_7 addr0_0 addr0_1 addr0_2 addr0_3 addr0_4 addr0_5 addr0_6 addr0_7 csb0 web0 clk0 dout0_0 dout0_1 dout0_2 dout0_3 dout0_4 dout0_5 dout0_6 dout0_7 vdd gnd sram_1rw_8x256
Vdin0_0 din0_0 0 DC 0
Vdin0_1 din0_1 0 DC 0
Vdin0_2 din0_2 0 DC 0
Vdin0_3 din0_3 0 DC 0
Vdin0_4 din0_4 0 DC 0
Vdin0_5 din0_5 0 DC 0
Vdin0_6 din0_6 0 DC 0
Vdin0_7 din0_7 0 DC 0
Vaddr0_0 addr0_0 0 DC 0
Vaddr0_1 addr0_1 0 DC 0
Vaddr0_2 addr0_2 0 DC 0
Vaddr0_3 addr0_3 0 DC 0
Vaddr0_4 addr0_4 0 DC 0
Vaddr0_5 addr0_5 0 DC 0
Vaddr0_6 addr0_6 0 DC 0
Vaddr0_7 addr0_7 0 DC 0
Vcsb0 csb0 0 DC 1.0
Vweb0 web0 0 DC 1.0
Vclk0 clk0 0 PWL(0 0 1n 0 1.05n 1.0 2n 1.0 2.05n 0)
CLdout0_0 dout0_0 0 0.2091f
CLdout0_1 dout0_1 0 0.2091f
CLdout0_2 dout0_2 0 0.2091f
CLdout0_3 dout0_3 0 0.2091f
CLdout0_4 dout0_4 0 0.2091f
CLdout0_5 dout0_5 0 0.2091f
CLdout0_6 dout0_6 0 0.2091f
CLdout0_7 dout0_7 0 0.2091f
.meas tran leak_5_10ns avg par('(-1*v(vdd)*I(vvdd))') from=5n to=10n
.meas tran leak_0p5_1us avg par('(-1*v(vdd)*I(vvdd))') from=500n to=1000n
.meas tran leak_1_2us avg par('(-1*v(vdd)*I(vvdd))') from=1000n to=2000n
.meas tran leak_2_3us avg par('(-1*v(vdd)*I(vvdd))') from=2000n to=3000n
.meas tran leak_3_4us avg par('(-1*v(vdd)*I(vvdd))') from=3000n to=4000n
.meas tran leak_4_4p5us avg par('(-1*v(vdd)*I(vvdd))') from=4000n to=4500n
.meas tran leak_4p5_5us avg par('(-1*v(vdd)*I(vvdd))') from=4500n to=5000n
.meas tran v_bl0_10ns find v(xsram_1rw_8x256.xbank0.bl_0_0) at=10n
.meas tran v_sa0_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d0.dint) at=10n
.meas tran v_bl0_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_0) at=1000n
.meas tran v_sa0_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d0.dint) at=1000n
.meas tran v_bl0_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_0) at=5000n
.meas tran v_sa0_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d0.dint) at=5000n
.meas tran v_bl1_10ns find v(xsram_1rw_8x256.xbank0.bl_0_8) at=10n
.meas tran v_sa1_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d1.dint) at=10n
.meas tran v_bl1_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_8) at=1000n
.meas tran v_sa1_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d1.dint) at=1000n
.meas tran v_bl1_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_8) at=5000n
.meas tran v_sa1_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d1.dint) at=5000n
.meas tran v_bl2_10ns find v(xsram_1rw_8x256.xbank0.bl_0_16) at=10n
.meas tran v_sa2_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d2.dint) at=10n
.meas tran v_bl2_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_16) at=1000n
.meas tran v_sa2_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d2.dint) at=1000n
.meas tran v_bl2_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_16) at=5000n
.meas tran v_sa2_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d2.dint) at=5000n
.meas tran v_bl3_10ns find v(xsram_1rw_8x256.xbank0.bl_0_24) at=10n
.meas tran v_sa3_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d3.dint) at=10n
.meas tran v_bl3_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_24) at=1000n
.meas tran v_sa3_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d3.dint) at=1000n
.meas tran v_bl3_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_24) at=5000n
.meas tran v_sa3_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d3.dint) at=5000n
.meas tran v_bl4_10ns find v(xsram_1rw_8x256.xbank0.bl_0_32) at=10n
.meas tran v_sa4_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d4.dint) at=10n
.meas tran v_bl4_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_32) at=1000n
.meas tran v_sa4_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d4.dint) at=1000n
.meas tran v_bl4_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_32) at=5000n
.meas tran v_sa4_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d4.dint) at=5000n
.meas tran v_bl5_10ns find v(xsram_1rw_8x256.xbank0.bl_0_40) at=10n
.meas tran v_sa5_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d5.dint) at=10n
.meas tran v_bl5_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_40) at=1000n
.meas tran v_sa5_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d5.dint) at=1000n
.meas tran v_bl5_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_40) at=5000n
.meas tran v_sa5_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d5.dint) at=5000n
.meas tran v_bl6_10ns find v(xsram_1rw_8x256.xbank0.bl_0_48) at=10n
.meas tran v_sa6_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d6.dint) at=10n
.meas tran v_bl6_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_48) at=1000n
.meas tran v_sa6_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d6.dint) at=1000n
.meas tran v_bl6_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_48) at=5000n
.meas tran v_sa6_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d6.dint) at=5000n
.meas tran v_bl7_10ns find v(xsram_1rw_8x256.xbank0.bl_0_56) at=10n
.meas tran v_sa7_10ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d7.dint) at=10n
.meas tran v_bl7_1000ns find v(xsram_1rw_8x256.xbank0.bl_0_56) at=1000n
.meas tran v_sa7_1000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d7.dint) at=1000n
.meas tran v_bl7_5000ns find v(xsram_1rw_8x256.xbank0.bl_0_56) at=5000n
.meas tran v_sa7_5000ns find v(xsram_1rw_8x256.xbank0.xport_data0.xsense_amp_array0.xsa_d7.dint) at=5000n
.TEMP 25
.TRAN 10p 5000n 0n 1n UIC
.OPTIONS POST=1 RELTOL=0.001 PROBE method=gear ACCT
.end
