// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// tag_core on its pins, with the models of its world: the TMP100, the 24AA02E48 and a SPI sensor on the bus, the
// pull-ups, an ADC and an MTP port, the eFuse blocks. tests/test_tag_core.py runs it and checks what it logs:
//   events.txt   one line per packet: tx <packet> <ns> <clocks> <sensor hex> <failed> <profile_ok> <eui_ok>
//                <AdvA hex> <TxAdd> <channel>, at tx_start
//   iq.txt       <packet> <I> <Q> per sample, bits.txt <packet> <bit> per PHY bit
//   cover.txt    every (phase, state) and every bus (command, phase) reached
//   and the models' logs (tmp100.log, eeprom.log, spi.log)
// Defines: CFG_SRC, SB (SENSOR_BYTES), BCH, ADC, BUS_DIV, OTP (ADV_ADDRESS_OTP), CLK_HALF_NS, COMMAND (the SPI
// model's shape), and optionally PROFILE (DEFAULT_PROFILE).
// Plusargs: events (the packets to wait for), max_ms (the watchdog); tmp100 (0: not on the bus), eeprom (0: not on
// the bus); i2c_monitor, i2c_protocol (tests/i2c_timing_monitor.v); nack_from, nack_to: the TMP100 off the bus from
// that packet's end to that one's; stuck_scl_from/to, stuck_sda_from/to: the line held low so; stuck_state,
// stuck_ph, stuck_after, stuck_clocks: SCL held low for stuck_clocks clocks, once, after stuck_after clocks in that
// state and phase; reset_state, reset_ph, reset_event, reset_after: one reset, of reset_clocks clocks, after
// reset_after clocks in that state and phase from packet reset_event on; otp_prog: program this AdvA into the eFuse
// blocks. The bus must be idle while the state machine sleeps: its lines released, the last frame closed by a STOP
// (when i2c_protocol is on). Each WAIT step is logged: wait <its value> <clocks>.

`timescale 1ns/1ps
`ifndef PROFILE
  `define PROFILE 256'h0120e803250680095000b09001014d00b09001814da190009491000000000084
`endif
module tag_core_tb;
  reg clk = 0;
  always #(`CLK_HALF_NS) clk = !clk;
  reg rst = 1;

  tri1 scl, sda, miso;
  wire scl_oe, sda_oe, cs_n;
  reg stuck_scl = 0, stuck_sda = 0;
  assign scl = (scl_oe || stuck_scl) ? 1'b0 : 1'bz;
  assign sda = (sda_oe || stuck_sda) ? 1'b0 : 1'bz;

  wire signed [7:0] i, q;
  wire iq_valid, iq_valid_last, phy_bit, phy_bit_valid, phy_bit_valid_last, up, up_v, up_vl, gauss_v, gauss_vl;
  wire signed [15:0] gauss;
  wire event_done, sensor_failed, profile_ok, adv_address_read, tx_add, test_mode, otp_ready;
  wire [8*`SB-1:0] sensor;
  wire [47:0] adv_sent;
  wire [5:0] channel;
  wire [15:0] interval;
  wire [3:0] state_status;
  reg [47:0] otp_prog = 0;

  // the ADC: a conversion takes a few clocks more than a bus phase; the samples in temps.hex
  wire adc_start;
  reg adc_done = 1;
  reg [11:0] adc_data = 0;
  reg [15:0] adc_samples [0:4095];
  integer adc_index = 0, adc_count = 0;
  initial $readmemh("spi_values.hex", adc_samples);

  // the MTP: mtp.hex, a few clocks to read
  wire mtp_read;
  wire [5:0] mtp_address;
  reg [7:0] mtp_mem [0:63];
  reg mtp_valid = 0;
  reg [7:0] mtp_data = 0;
  integer mtp_wait = 0;
  initial $readmemh("mtp.hex", mtp_mem);

  tag_core #(
    .CFG_SRC(`CFG_SRC), .SENSOR_BYTES(`SB), .BCH_T(`BCH), .ADC_EN(`ADC), .BUS_DIV(`BUS_DIV),
    .ADV_ADDRESS_OTP(`OTP), .ADV_ADDRESS(`ROM_ADV), .DEFAULT_PROFILE(`PROFILE), .COMPANY_ID(`CID)
  ) dut (
    .clk(clk), .rst(rst),
    .scl_i(scl), .sda_i(sda), .miso_i(miso), .scl_oe(scl_oe), .sda_oe(sda_oe), .cs_n(cs_n),
    .adc_start(adc_start), .adc_done(adc_done), .adc_data(adc_data),
    .mtp_read(mtp_read), .mtp_address(mtp_address), .mtp_data(mtp_data), .mtp_valid(mtp_valid),
    .adv_address_otp_prog(otp_prog), .adv_address_otp_ready(otp_ready),
    .i(i), .q(q), .iq_valid(iq_valid), .iq_valid_last(iq_valid_last),
    .phy_bit(phy_bit), .phy_bit_valid(phy_bit_valid), .phy_bit_valid_last(phy_bit_valid_last),
    .bit_upsample(up), .bit_upsample_valid(up_v), .bit_upsample_valid_last(up_vl),
    .bit_upsample_gauss_filter(gauss), .bit_upsample_gauss_filter_valid(gauss_v),
    .bit_upsample_gauss_filter_valid_last(gauss_vl),
    .event_done(event_done), .sensor(sensor), .sensor_failed(sensor_failed), .profile_ok(profile_ok),
    .adv_address_read(adv_address_read), .tx_add(tx_add), .adv_address_sent(adv_sent),
    .channel(channel), .interval(interval), .test_mode(test_mode), .state_status(state_status)
  );

  // the world
  integer use_tmp100 = 1, use_eeprom = 1, i2c_monitor = 1, i2c_protocol = 1;
  reg tmp100_present = 1;
  wire tmp100_on = (use_tmp100 != 0) && tmp100_present;
  wire eeprom_on = (use_eeprom != 0);
  tmp100_model tmp100_i (.scl(scl), .sda(sda), .present(tmp100_on));
  eeprom_24aa02e48_model eeprom_i (.scl(scl), .sda(sda), .present(eeprom_on));
  spi_sensor_model #(.COMMAND(`COMMAND)) spi_i (.sclk(scl), .mosi(sda), .cs_n(cs_n), .miso(miso));
  wire monitor_on = (i2c_monitor != 0) && (rst === 1'b0);
  wire monitor_protocol = (i2c_protocol != 0);
  i2c_timing_monitor monitor_i (.scl(scl), .sda(sda), .enable(monitor_on), .protocol(monitor_protocol));

  always @(posedge clk) begin
    if (adc_start) begin
      adc_done <= 0;
      adc_index <= 100;                               // longer than a bus phase, so that the bus must wait for it
    end else if (adc_index > 0) begin
      adc_index <= adc_index - 1;
      if (adc_index == 1) begin
        adc_data <= adc_samples[adc_count][15:4];
        adc_count <= adc_count + 1;
        adc_done <= 1;
      end
    end
    if (mtp_valid) begin
      mtp_valid <= 0;
      mtp_wait <= 0;
    end else if (mtp_read) begin
      if (mtp_wait == 3) begin
        mtp_data <= mtp_mem[mtp_address];
        mtp_valid <= 1;
      end
      mtp_wait <= mtp_wait + 1;
    end
  end

  // what the state machine reached: the coverage of its states
  reg seen_state [0:255];
  reg seen_bus [0:15];
  integer k, fd_events, fd_iq, fd_bits, fd_cover;
  integer events = 3, max_ms = 2000, packet = 0, done_count = 0, clocks = 0;
  integer nack_from = -1, nack_to = -1, stuck_scl_from = -1, stuck_scl_to = -1, stuck_sda_from = -1, stuck_sda_to = -1;
  integer reset_state = -1, reset_ph = -1, reset_event = 0, reset_after = 0, reset_clocks = 2, reset_count = 0;
  integer stuck_state = -1, stuck_ph = -1, stuck_after = 0, stuck_clocks = 0, stuck_count = 0, stuck_left = 0;
  integer rst_release = 0, finish_after = 0;
  reg reset_done = 0, stuck_done = 0, finishing = 0;
  reg [47:0] otp_value = 0;
  reg in_packet = 0, in_wait = 0;
  integer wait_begin = 0, wait_value = 0;
  wire reset_pending = (reset_state >= 0) && !reset_done;

  function in_window(input integer from, input integer to, input integer now);
    in_window = (from >= 0) && (now >= from) && (now < to);
  endfunction

  initial begin
    for (k = 0; k < 256; k = k + 1) seen_state[k] = 0;
    for (k = 0; k < 16; k = k + 1) seen_bus[k] = 0;
    fd_events = $fopen("events.txt", "w");
    fd_iq = $fopen("iq.txt", "w");
    fd_bits = $fopen("bits.txt", "w");
    fd_cover = $fopen("cover.txt", "w");
    if (!$value$plusargs("events=%d", events)) events = 3;
    if (!$value$plusargs("max_ms=%d", max_ms)) max_ms = 2000;
    if (!$value$plusargs("tmp100=%d", use_tmp100)) use_tmp100 = 1;
    if (!$value$plusargs("eeprom=%d", use_eeprom)) use_eeprom = 1;
    if (!$value$plusargs("i2c_monitor=%d", i2c_monitor)) i2c_monitor = 1;
    if (!$value$plusargs("i2c_protocol=%d", i2c_protocol)) i2c_protocol = 1;
    if (!$value$plusargs("nack_from=%d", nack_from)) nack_from = -1;
    if (!$value$plusargs("nack_to=%d", nack_to)) nack_to = -1;
    if (!$value$plusargs("stuck_scl_from=%d", stuck_scl_from)) stuck_scl_from = -1;
    if (!$value$plusargs("stuck_scl_to=%d", stuck_scl_to)) stuck_scl_to = -1;
    if (!$value$plusargs("stuck_sda_from=%d", stuck_sda_from)) stuck_sda_from = -1;
    if (!$value$plusargs("stuck_sda_to=%d", stuck_sda_to)) stuck_sda_to = -1;
    if (!$value$plusargs("stuck_state=%d", stuck_state)) stuck_state = -1;
    if (!$value$plusargs("stuck_ph=%d", stuck_ph)) stuck_ph = -1;
    if (!$value$plusargs("stuck_after=%d", stuck_after)) stuck_after = 0;
    if (!$value$plusargs("stuck_clocks=%d", stuck_clocks)) stuck_clocks = 0;
    stuck_scl = in_window(stuck_scl_from, stuck_scl_to, 0);
    stuck_sda = in_window(stuck_sda_from, stuck_sda_to, 0);
    tmp100_present = !in_window(nack_from, nack_to, 0);
    if (!$value$plusargs("reset_state=%d", reset_state)) reset_state = -1;
    if (!$value$plusargs("reset_ph=%d", reset_ph)) reset_ph = -1;
    if (!$value$plusargs("reset_event=%d", reset_event)) reset_event = 0;
    if (!$value$plusargs("reset_after=%d", reset_after)) reset_after = 0;
    if (!$value$plusargs("reset_clocks=%d", reset_clocks)) reset_clocks = 2;
    if ($value$plusargs("otp_prog=%h", otp_value)) begin
      // an unprogrammed chip reads 0; AdvA programmed once, sensed at the next reset
      repeat (4) @(posedge clk);
      rst <= 0;
      repeat (2) @(posedge clk);
      if (adv_sent !== 48'h0) begin
        $display("MISMATCH unprogrammed OTP reads %h", adv_sent);
        $fatal(1, "otp");
      end
      rst <= 1;                                       // hold the core while the fuses are blown: production
      repeat (2) @(posedge clk);
      rst <= 0;
      @(posedge clk);
      otp_prog <= otp_value;
      #(51000);                                       // Tprog
      otp_prog <= 0;
      @(posedge clk);
      rst <= 1;
      repeat (4) @(posedge clk);
    end else begin
      repeat (8) @(posedge clk);
    end
    rst <= 0;
  end

  initial begin : watchdog
    #(1.0e6 * max_ms);
    $display("MISMATCH watchdog: %0d packets of %0d after %0d ms, state %0d, phase %0d", packet, events, max_ms,
             state_status, dut.ph);
    $fatal(1, "watchdog");
  end

  always @(posedge clk) begin
    clocks <= clocks + 1;
    seen_state[{2'b0, dut.ph, dut.state}] = 1;
    if (dut.tag_bus_i.active) seen_bus[{dut.tag_bus_i.op, dut.tag_bus_i.phase}] = 1;
    if (rst === 1'b0 && (^{iq_valid, iq_valid_last}) === 1'bx) begin
      $display("MISMATCH unknown valid output at %0t", $time);
      $fatal(1, "unknown");
    end
    if (rst === 1'b0 && (^{scl_oe, sda_oe, cs_n}) === 1'bx) begin
      $display("MISMATCH unknown pin at %0t", $time);
      $fatal(1, "unknown");
    end
    if (rst === 1'b0 && state_status == 4'd10 && (scl_oe || sda_oe || !cs_n)) begin
      $display("MISMATCH the bus not idle while sleeping at %0t: SCL %b SDA %b CS_n %b", $time, !scl_oe, !sda_oe, cs_n);
      $fatal(1, "idle");
    end
    if (rst === 1'b0 && state_status == 4'd10 && monitor_on && monitor_protocol && monitor_i.in_frame) begin
      $display("MISMATCH the last frame not closed by a STOP, sleeping at %0t", $time);
      $fatal(1, "idle");
    end
    if (state_status == 4'd4 && !in_wait) begin
      in_wait = 1;
      wait_begin = clocks;
      wait_value = dut.wait_count;
    end else if (state_status != 4'd4 && in_wait) begin
      in_wait = 0;
      if (rst === 1'b0) $fdisplay(fd_events, "wait %0d %0d", wait_value, clocks - wait_begin);
    end
    if (rst === 1'b0 && dut.tx_start) begin
      if ((^sensor) === 1'bx) begin
        $display("MISMATCH unknown sensor at %0t", $time);
        $fatal(1, "unknown");
      end
      $fdisplay(fd_events, "tx %0d %0.0f %0d %0x %0d %0d %0d %012x %0d %0d", packet, $realtime, clocks, sensor,
                sensor_failed, profile_ok, adv_address_read, adv_sent, tx_add, channel);
      $fflush(fd_events);
      in_packet <= 1;
    end
    if (rst === 1'b0 && iq_valid) $fdisplay(fd_iq, "%0d %0d %0d", packet, i, q);
    if (rst === 1'b0 && phy_bit_valid) $fdisplay(fd_bits, "%0d %0d", packet, phy_bit);
    if (event_done) begin
      in_packet <= 0;
      packet = packet + 1;
      tmp100_present = !in_window(nack_from, nack_to, packet);
      if (stuck_scl_from >= 0) stuck_scl = in_window(stuck_scl_from, stuck_scl_to, packet);
      if (stuck_sda_from >= 0) stuck_sda = in_window(stuck_sda_from, stuck_sda_to, packet);
    end
    // SCL held low once, in the state chosen
    if (!stuck_done && stuck_state >= 0 && dut.state == stuck_state && dut.ph == stuck_ph) begin
      if (stuck_count == stuck_after) begin
        stuck_done = 1;
        stuck_scl = 1;
        stuck_left = stuck_clocks;
      end
      stuck_count = stuck_count + 1;
    end
    if (stuck_left > 0) begin
      stuck_left = stuck_left - 1;
      if (stuck_left == 0) stuck_scl = 0;
    end
    // one reset, in the state chosen
    if (!reset_done && reset_state >= 0 && dut.state == reset_state && dut.ph == reset_ph && packet >= reset_event) begin
      if (reset_count == reset_after) begin
        reset_done = 1;
        rst <= 1;
        rst_release <= reset_clocks;
        $fdisplay(fd_events, "reset %0d %0.0f %0d", packet, $realtime, clocks);
        in_packet <= 0;
        packet = packet + 1;
      end
      reset_count = reset_count + 1;
    end
    if (rst_release > 0) begin
      rst_release <= rst_release - 1;
      if (rst_release == 1) rst <= 0;
    end
    if (packet >= events && !finishing && !reset_pending) begin
      finishing = 1;
      finish_after <= 50;
    end
    if (finish_after > 0) begin
      finish_after <= finish_after - 1;
      if (finish_after == 1) finish_run;
    end
  end

  task finish_run;
    begin
      for (k = 0; k < 256; k = k + 1) if (seen_state[k]) $fdisplay(fd_cover, "state %0d %0d", k >> 4, k & 15);
      for (k = 0; k < 16; k = k + 1) if (seen_bus[k]) $fdisplay(fd_cover, "bus %0d %0d", k >> 2, k & 3);
      $fclose(fd_events); $fclose(fd_iq); $fclose(fd_bits); $fclose(fd_cover);
      $display("PASS: %0d packets; SCL period, between %0.1f and %0.1f ns; %0d STARTs, %0d STOPs; interval %0d, channel %0d, test mode %b",
               packet, monitor_i.period_min, monitor_i.period_max, monitor_i.starts, monitor_i.stops, interval, channel, test_mode);
      $finish;
    end
  endtask
endmodule
