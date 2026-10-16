# btle_tx of ble-tx-min (GAUSS_TABLE=1, ADV_DATA_FLOPS=1, ADV_ADDRESS_OTP=1), GF180MCU-D.
# Two clocks: clk, the baseband clock (16 MHz), and clkb, the packet writer's clock (AXI side; the
# contract asks for 8 MHz or faster, constrained here at 50 MHz). The packet path crosses from clkb
# to clk through a toggle and two synchronizing flip-flops, so the two clocks are asynchronous.
# adv_address_otp_prog is a production port held for at least 50 us: no timing on it.

create_clock -name clk  -period 62.5 [get_ports clk]
create_clock -name clkb -period 20.0 [get_ports clkb]
set_clock_groups -asynchronous -group [get_clocks clk] -group [get_clocks clkb]

set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
if { [info exists ::env(MAX_TRANSITION_CONSTRAINT)] } {
    set_max_transition $::env(MAX_TRANSITION_CONSTRAINT) [current_design]
}

set clkb_inputs [get_ports {pdu_octet_mem_data[*] pdu_octet_mem_addr[*]}]
set async_inputs [get_ports {adv_address_otp_prog[*]}]
set clk_inputs {}
foreach p [all_inputs] {
    set n [get_name $p]
    if { $n == "clk" || $n == "clkb" } { continue }
    if { [string match "pdu_octet_mem_*" $n] || [string match "adv_address_otp_prog*" $n] } { continue }
    lappend clk_inputs $p
}

set_input_delay [expr 62.5 * 0.2] -clock [get_clocks clk]  $clk_inputs
set_input_delay [expr 20.0 * 0.2] -clock [get_clocks clkb] $clkb_inputs
set_output_delay [expr 62.5 * 0.2] -clock [get_clocks clk] [all_outputs]
set_false_path -from $async_inputs

set_driving_cell -lib_cell [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 0] \
    -pin [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 1] [concat $clk_inputs [get_ports {pdu_octet_mem_* adv_address_otp_prog[*]}]]
set_load [expr $::env(OUTPUT_CAP_LOAD) / 1000.0] [all_outputs]

set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) [all_clocks]
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [all_clocks]
set_timing_derate -early [expr 1 - $::env(TIME_DERATING_CONSTRAINT) / 100.0]
set_timing_derate -late  [expr 1 + $::env(TIME_DERATING_CONSTRAINT) / 100.0]
set_propagated_clock [all_clocks]
