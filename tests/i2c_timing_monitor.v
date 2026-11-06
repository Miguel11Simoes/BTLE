// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
//
// The I2C bus as the two devices of the proof of concept ask for it, in fast mode, for the testbenches: a
// violation is a MISMATCH. The limits, the stricter of the TMP100 (SBOS231I, section 6.6) and the 24AA02E48 at
// 2.5 V or more (DS22124D, table 1-2), in ns: SCL at most 400 kHz; tLOW 1300; tHIGH 600; tSU;STA 600; tHD;STA
// 600; tSU;DAT 100; tHD;DAT 20; tSU;STO 600; tBUF 1300. With protocol = 1, also the frames: a START or a STOP only
// between bytes (nine bits after the last one), which a reset or a bus clear is allowed to break (protocol = 0).
// Reports the shortest SCL period seen, the period of the bits within a byte, as period_min and period_max.

`timescale 1ns/1ps
module i2c_timing_monitor (
  input  wire scl,
  input  wire sda,
  input  wire enable,
  input  wire protocol
);
  real t_scl_rise = -1.0e12, t_scl_fall = -1.0e12, t_sda_change = -1.0e12, t_start = -1.0e12, t_stop = -1.0e12;
  real period_min = 1.0e12, period_max = 0.0, low_min = 1.0e12, high_min = 1.0e12, now;
  integer bits = 0, starts = 0, stops = 0, clocks = 0;
  reg in_frame = 0;
  reg scl_seen = 0;
  reg start_fall = 0;                                 // the fall of SCL that completes a START is not a clock

  task fail(input [8*40-1:0] what, input real measured, input real limit);
    begin
      $display("MISMATCH i2c at %0.0f ns: %0s %0.1f ns, at least %0.1f ns", now, what, measured, limit);
      $fatal(1, "i2c timing");
    end
  endtask

  always @(posedge scl) if (enable) begin
    now = $realtime;
    if (now - t_scl_fall < 1300.0) fail("tLOW", now - t_scl_fall, 1300.0);
    if (now - t_sda_change < 100.0) fail("tSU;DAT", now - t_sda_change, 100.0);
    if (scl_seen && in_frame) begin
      if (now - t_scl_rise < period_min) period_min = now - t_scl_rise;
      if (now - t_scl_rise > period_max && (bits % 9) != 0) period_max = now - t_scl_rise;
    end
    if (now - t_scl_rise < 2500.0) fail("SCL period", now - t_scl_rise, 2500.0);
    t_scl_rise = now;
    scl_seen = 1;
    clocks = clocks + 1;
  end

  always @(negedge scl) if (enable) begin
    now = $realtime;
    if (now - t_scl_rise < 600.0) fail("tHIGH", now - t_scl_rise, 600.0);
    if (now - t_start < 600.0) fail("tHD;STA", now - t_start, 600.0);
    t_scl_fall = now;
    if (start_fall) start_fall = 0;
    else if (in_frame) bits = bits + 1;
  end

  always @(sda) if (enable) begin
    now = $realtime;
    if (scl === 1'b1) begin
      if (sda === 1'b0) begin                       // START
        if (now - t_scl_rise < 600.0) fail("tSU;STA", now - t_scl_rise, 600.0);
        if (now - t_stop < 1300.0) fail("tBUF", now - t_stop, 1300.0);
        if (protocol && in_frame && (bits % 9) != 0) fail("START inside a byte, bits", bits, 0.0);
        t_start = now;
        starts = starts + 1;
        in_frame = 1;
        start_fall = 1;
        bits = 0;
      end else begin                                // STOP
        if (now - t_scl_rise < 600.0) fail("tSU;STO", now - t_scl_rise, 600.0);
        if (protocol && in_frame && (bits % 9) != 0) fail("STOP inside a byte, bits", bits, 0.0);
        t_stop = now;
        stops = stops + 1;
        in_frame = 0;
      end
    end else begin
      if (now - t_scl_fall < 20.0) fail("tHD;DAT", now - t_scl_fall, 20.0);
    end
    t_sda_change = now;
  end
endmodule
