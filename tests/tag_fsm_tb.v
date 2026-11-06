// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// tag_fsm on its pins, with its world: the models of its sensors, one on the bus by the pins sel, the pull-ups, the eFuse
// blocks, the I2C monitor. tests/test_tag_fsm.py runs it and checks what it logs:
//   events.txt   tx <packet> <ns> <ticks> <sensor hex> <AdvA hex> <the sensor in shutdown> <channel>, at tx_start
//   iq.txt       <packet> <I> <Q> per sample, bits.txt <packet> <bit> per PHY bit
//   cover.txt    every (profile, slot) on the bus reached
//   and the models' logs
// Defines: TICK_DIV, BCH, OTP, CHANNEL, CLK_HALF_NS, ROM_ADV, CID.
// Plusargs: events (the packets to wait for), max_ms (the watchdog); sel, rate; present (0: no sensor on the bus); spi_model
// (1: tests/spi_sensor_model.v, SPI mode 0, on the bus instead); i2c_monitor, i2c_protocol; test_mode; off_after, off_ticks,
// on_rate: rate 0 after that many packets, then on_rate after off_ticks ticks; nack_from, nack_to: the sensor off the bus
// from that packet's end to that one's; stuck_scl_from/to, stuck_sda_from/to: the line held low so; reset_packet, reset_t: one
// reset of reset_clocks clocks when t[11:0] in the last 2^12 ticks is reset_t after that packet (reset_t < 0: in the packet);
// otp_prog: program this AdvA into the eFuse blocks. The bus must be idle outside the frames: its lines released (SCL low with
// SPI mode 0), the last frame closed by a STOP (when i2c_protocol is on).

`timescale 1ns/1ps
module tag_fsm_tb;
  reg clk = 0;
  always #(`CLK_HALF_NS) clk = !clk;
  reg rst = 1;

  tri1 scl, sda;
  wire scl_oe, sda_oe, cs_n;
  reg stuck_scl = 0, stuck_sda = 0;
  assign scl = (scl_oe || stuck_scl) ? 1'b0 : 1'bz;
  assign sda = (sda_oe || stuck_sda) ? 1'b0 : 1'bz;

  wire signed [7:0] i, q;
  wire iq_valid, iq_valid_last, phy_bit, phy_bit_valid, phy_bit_valid_last, up, up_v, up_vl, gauss_v, gauss_vl;
  wire signed [15:0] gauss;
  wire tx_start, otp_ready;
  wire [15:0] sensor;
  wire [47:0] adv_sent;
  reg [47:0] otp_prog = 0;
  reg [2:0] rate = 3'd4;
  reg [1:0] sel = 2'd0;
  reg test_mode = 0;

  tag_fsm #(
    .TICK_DIV(`TICK_DIV), .BCH_T(`BCH), .ADV_ADDRESS_OTP(`OTP), .ADV_ADDRESS(`ROM_ADV),
    .COMPANY_ID(`CID), .CHANNEL(`CHANNEL)
  ) dut (
    .clk(clk), .rst(rst), .rate(rate), .sel(sel), .test_mode(test_mode),
    .sda_i(sda), .scl_oe(scl_oe), .sda_oe(sda_oe), .cs_n(cs_n),
    .adv_address_otp_prog(otp_prog), .adv_address_otp_ready(otp_ready),
    .i(i), .q(q), .iq_valid(iq_valid), .iq_valid_last(iq_valid_last),
    .phy_bit(phy_bit), .phy_bit_valid(phy_bit_valid), .phy_bit_valid_last(phy_bit_valid_last),
    .bit_upsample(up), .bit_upsample_valid(up_v), .bit_upsample_valid_last(up_vl),
    .bit_upsample_gauss_filter(gauss), .bit_upsample_gauss_filter_valid(gauss_v),
    .bit_upsample_gauss_filter_valid_last(gauss_vl),
    .tx_start(tx_start), .sensor(sensor), .adv_address_sent(adv_sent)
  );

  integer present_arg = 1, spi_model = 0, i2c_monitor = 1, i2c_protocol = 1;
  reg on_bus = 1;
  wire sensor_on = (present_arg != 0) && on_bus && (spi_model == 0);
  tmp100_model tmp100_i (.scl(scl), .sda(sda), .present(sensor_on && (sel == 2'd0)));
  tmp114_model tmp114_i (.scl(scl), .sda(sda), .present(sensor_on && (sel == 2'd1)));
  max31875_model max31875_i (.scl(scl), .sda(sda), .present(sensor_on && (sel == 2'd2)));
  tmp126_model tmp126_i (.sclk(scl), .cs_n(cs_n), .sio(sda), .present(sensor_on && (sel == 2'd3)));
  wire spi_miso, spi_cs_n = (spi_model != 0) ? cs_n : 1'b1;
  spi_sensor_model #(.COMMAND(0)) spi_i (.sclk(scl), .mosi(sda), .cs_n(spi_cs_n), .miso(spi_miso));
  assign sda = (spi_model != 0) ? spi_miso : 1'bz;
  wire monitor_on = (i2c_monitor != 0) && (rst === 1'b0);
  wire monitor_protocol = (i2c_protocol != 0);
  i2c_timing_monitor monitor_i (.scl(scl), .sda(sda), .enable(monitor_on), .protocol(monitor_protocol));

  wire in_shutdown = (sel == 2'd0) ? tmp100_i.shut_down : (sel == 2'd1) ? tmp114_i.shut_down :
                     (sel == 2'd2) ? max31875_i.shut_down : tmp126_i.shut_down;
  wire [15:0] config_now = (sel == 2'd0) ? {8'd0, tmp100_i.config_reg} : (sel == 2'd1) ? tmp114_i.config_reg :
                           (sel == 2'd2) ? max31875_i.config_reg : tmp126_i.config_reg;

  reg seen [0:4095];
  integer k, fd_events, fd_iq, fd_bits, fd_cover;
  integer events = 3, max_ms = 2000, packet = 0, ticks = 0, rate_arg = 4, test_arg = 0, sel_arg = 0;
  integer nack_from = -1, nack_to = -1, stuck_scl_from = -1, stuck_scl_to = -1, stuck_sda_from = -1, stuck_sda_to = -1;
  integer reset_packet = -1, reset_t = 0, reset_clocks = 2, rst_release = 0, finish_after = 0;
  integer off_after = -1, off_ticks = 0, on_rate = 4, off_left = 0;
  reg reset_done = 0, off_done = 0, finishing = 0;
  reg [47:0] otp_value = 0;
  reg in_packet = 0, tx_d = 0;
  integer was_on_bus = 0;

  function in_window(input integer from, input integer to, input integer now);
    in_window = (from >= 0) && (now >= from) && (now < to);
  endfunction

  initial begin
    for (k = 0; k < 4096; k = k + 1) seen[k] = 0;
    fd_events = $fopen("events.txt", "w");
    fd_iq = $fopen("iq.txt", "w");
    fd_bits = $fopen("bits.txt", "w");
    fd_cover = $fopen("cover.txt", "w");
    if (!$value$plusargs("events=%d", events)) events = 3;
    if (!$value$plusargs("max_ms=%d", max_ms)) max_ms = 2000;
    if (!$value$plusargs("present=%d", present_arg)) present_arg = 1;
    if (!$value$plusargs("spi_model=%d", spi_model)) spi_model = 0;
    if (!$value$plusargs("i2c_monitor=%d", i2c_monitor)) i2c_monitor = 1;
    if (!$value$plusargs("i2c_protocol=%d", i2c_protocol)) i2c_protocol = 1;
    if ($value$plusargs("sel=%d", sel_arg)) sel = sel_arg[1:0];
    if ($value$plusargs("rate=%d", rate_arg)) rate = rate_arg[2:0];
    if ($value$plusargs("test_mode=%d", test_arg)) begin
      test_mode = (test_arg != 0);
      rate = 3'd0;                                    // clears the test mode's counter
    end
    if (!$value$plusargs("nack_from=%d", nack_from)) nack_from = -1;
    if (!$value$plusargs("nack_to=%d", nack_to)) nack_to = -1;
    if (!$value$plusargs("stuck_scl_from=%d", stuck_scl_from)) stuck_scl_from = -1;
    if (!$value$plusargs("stuck_scl_to=%d", stuck_scl_to)) stuck_scl_to = -1;
    if (!$value$plusargs("stuck_sda_from=%d", stuck_sda_from)) stuck_sda_from = -1;
    if (!$value$plusargs("stuck_sda_to=%d", stuck_sda_to)) stuck_sda_to = -1;
    if (!$value$plusargs("reset_packet=%d", reset_packet)) reset_packet = -1;
    if (!$value$plusargs("reset_t=%d", reset_t)) reset_t = 0;
    if (!$value$plusargs("reset_clocks=%d", reset_clocks)) reset_clocks = 2;
    if (!$value$plusargs("off_after=%d", off_after)) off_after = -1;
    if (!$value$plusargs("off_ticks=%d", off_ticks)) off_ticks = 0;
    if (!$value$plusargs("on_rate=%d", on_rate)) on_rate = 4;
    stuck_scl = in_window(stuck_scl_from, stuck_scl_to, 0);
    stuck_sda = in_window(stuck_sda_from, stuck_sda_to, 0);
    on_bus = !in_window(nack_from, nack_to, 0);
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
    if (test_mode) begin
      repeat (4) @(posedge clk);
      rate = rate_arg[2:0];
    end
  end

  initial begin : watchdog
    #(1.0e6 * max_ms);
    $display("MISMATCH watchdog: %0d packets of %0d after %0d ms", packet, events, max_ms);
    $fatal(1, "watchdog");
  end

  always @(posedge clk) begin
    if (dut.tick) ticks <= ticks + 1;
    if (dut.code != 3'd0 && dut.tick) seen[{sel, dut.slot}] = 1;
    if (rst === 1'b0 && (^{iq_valid, iq_valid_last}) === 1'bx) begin
      $display("MISMATCH unknown valid output at %0t", $time);
      $fatal(1, "unknown");
    end
    if (rst === 1'b0 && (^{scl_oe, sda_oe, cs_n}) === 1'bx) begin
      $display("MISMATCH unknown pin at %0t", $time);
      $fatal(1, "unknown");
    end
    if (rst === 1'b0 && dut.code == 3'd0 && dut.tick && was_on_bus == 0 && dut.cpol0 == 1'b0 && (scl_oe || sda_oe || !cs_n)) begin
      $display("MISMATCH the bus not idle outside the frames at %0t: SCL %b SDA %b CS_n %b", $time, !scl_oe, !sda_oe, cs_n);
      $fatal(1, "idle");
    end
    if (rst === 1'b0 && !dut.spi && !cs_n) begin
      $display("MISMATCH CS_n low with an I2C sensor at %0t", $time);
      $fatal(1, "cs_n");
    end
    if (dut.tick) was_on_bus = (dut.code != 3'd0) ? 1 : 0;
    tx_d <= tx_start;
    if (rst === 1'b0 && tx_d) begin                   // the clock after: the test mode's counter has stepped
      if ((^sensor) === 1'bx) begin
        $display("MISMATCH unknown sensor at %0t", $time);
        $fatal(1, "unknown");
      end
      if (monitor_on && monitor_protocol && monitor_i.in_frame) begin
        $display("MISMATCH the last frame not closed by a STOP at tx_start, %0t", $time);
        $fatal(1, "idle");
      end
      $fdisplay(fd_events, "tx %0d %0.0f %0d %04x %012x %0d %0d", packet, $realtime, ticks, sensor, adv_sent, in_shutdown, `CHANNEL);
      $fflush(fd_events);
      in_packet <= 1;
    end
    if (rst === 1'b0 && iq_valid) $fdisplay(fd_iq, "%0d %0d %0d", packet, i, q);
    if (rst === 1'b0 && phy_bit_valid) $fdisplay(fd_bits, "%0d %0d", packet, phy_bit);
    if (iq_valid_last) begin
      in_packet <= 0;
      packet = packet + 1;
      on_bus = !in_window(nack_from, nack_to, packet);
      if (stuck_scl_from >= 0) stuck_scl = in_window(stuck_scl_from, stuck_scl_to, packet);
      if (stuck_sda_from >= 0) stuck_sda = in_window(stuck_sda_from, stuck_sda_to, packet);
      if (off_after >= 0 && !off_done && packet == off_after) begin
        off_done = 1;
        rate = 3'd0;
        off_left = off_ticks * `TICK_DIV;
      end
    end
    if (off_left > 0) begin
      off_left = off_left - 1;
      if (off_left == 0) rate = on_rate[2:0];
    end
    // one reset, at the place chosen
    if (!reset_done && reset_packet >= 0 && packet >= reset_packet &&
        ((reset_t < 0) ? in_packet && (rst === 1'b0) && dut.tick && iq_valid :
                         (dut.t[11:0] == reset_t[11:0]) && &dut.t[17:12])) begin
      reset_done = 1;
      rst <= 1;
      rst_release <= reset_clocks;
      $fdisplay(fd_events, "reset %0d %0.0f %0d %0d", packet, $realtime, ticks, in_packet);
      if (in_packet) begin
        in_packet <= 0;
        packet = packet + 1;
      end
    end
    if (rst_release > 0) begin
      rst_release <= rst_release - 1;
      if (rst_release == 1) rst <= 0;
    end
    if (packet >= events && !finishing) begin
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
      for (k = 0; k < 4096; k = k + 1) if (seen[k]) $fdisplay(fd_cover, "slot %0d %0d", k >> 10, k & 1023);
      $fclose(fd_events); $fclose(fd_iq); $fclose(fd_bits); $fclose(fd_cover);
      $display("PASS: %0d packets; SCL period, between %0.1f and %0.1f ns; %0d STARTs, %0d STOPs; config %04x, profile %0d",
               packet, monitor_i.period_min, monitor_i.period_max, monitor_i.starts, monitor_i.stops, config_now, sel);
      $finish;
    end
  endtask
endmodule
