# tag_chip of ble-tx-poc-gen, GF180MCU-D. One clock, clk: constrained at 16 MHz, what btle_tx needs (the rest of the core
# works at 32.768 kHz between packets). SDA is asynchronous, sampled a quarter of a bit after SCL rises, when it has long
# been stable; adv_address_otp_prog is a production port held for at least 50 us: no timing on them.

create_clock -name clk -period 62.5 [get_ports clk]

set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
if { [info exists ::env(MAX_TRANSITION_CONSTRAINT)] } {
    set_max_transition $::env(MAX_TRANSITION_CONSTRAINT) [current_design]
}

set async_inputs [get_ports {sda_i adv_address_otp_prog[*]}]
set clk_inputs {}
foreach p [all_inputs] {
    set n [get_name $p]
    if { $n == "clk" || $n == "sda_i" || [string match "adv_address_otp_prog*" $n] } { continue }
    lappend clk_inputs $p
}

set_input_delay [expr 62.5 * 0.2] -clock [get_clocks clk] $clk_inputs
set_output_delay [expr 62.5 * 0.2] -clock [get_clocks clk] [all_outputs]
set_false_path -from $async_inputs
# The eFuse blocks, when there are any (ADV_ADDRESS_OTP = 1), sense their fuses once after reset_n rises (the Liberty's
# reset_n -> ready/out arc, 32 ns at ss) and hold them: out is static from then on and ready is a status output. Not a
# clock-cycle path.
set efuse_reset_pins [get_pins -quiet -hierarchical *efuse_i/reset_n]
if { [llength $efuse_reset_pins] != 0 } {
    if { [llength $efuse_reset_pins] != 6 } { error "expected the six efuse_i/reset_n pins, found [llength $efuse_reset_pins]" }
    set_false_path -through $efuse_reset_pins
}

set_driving_cell -lib_cell [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 0] \
    -pin [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 1] [concat $clk_inputs $async_inputs]
set_load [expr $::env(OUTPUT_CAP_LOAD) / 1000.0] [all_outputs]

set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) [all_clocks]
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [all_clocks]
set_timing_derate -early [expr 1 - $::env(TIME_DERATING_CONSTRAINT) / 100.0]
set_timing_derate -late  [expr 1 + $::env(TIME_DERATING_CONSTRAINT) / 100.0]
set_propagated_clock [all_clocks]

