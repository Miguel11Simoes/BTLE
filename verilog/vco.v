// Author: Xianjun Jiao <putaoshu@msn.com>
// SPDX-FileCopyrightText: 2024 Xianjun Jiao
// SPDX-License-Identifier: Apache-2.0 license
// Modified 2026-10-05 by Miguel Simões: the COS and SIN tables are a fixed ROM of the first eighth of the wave
// See CHANGES.md.

// Core_v5.3 section 3.1on page 2640
// The modulation index shall be between 0.45 and 0.55
// We implement 0.5

`timescale 1ns / 1ps
module vco #
(
  parameter integer VCO_BIT_WIDTH = 16,
  parameter integer SIN_COS_ADDR_BIT_WIDTH = 11,
  parameter integer IQ_BIT_WIDTH = 8
) (
  input wire clk,
  input wire rst,

  // kept for the interface; the tables are fixed, these writes are ignored
  input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] cos_table_write_address,
  input  wire signed [(IQ_BIT_WIDTH-1) : 0] cos_table_write_data,
  input  wire [(SIN_COS_ADDR_BIT_WIDTH-1) : 0] sin_table_write_address,
  input  wire signed [(IQ_BIT_WIDTH-1) : 0] sin_table_write_data,

  input wire signed [(VCO_BIT_WIDTH-1) : 0] voltage_signal,
  input wire voltage_signal_valid,
  input wire voltage_signal_valid_last,

  output reg signed [(IQ_BIT_WIDTH-1) : 0] cos_out,
  output reg signed [(IQ_BIT_WIDTH-1) : 0] sin_out,
  output reg sin_cos_out_valid,
  output reg sin_cos_out_valid_last
);

reg signed [(VCO_BIT_WIDTH-1) : 0] integral_voltage_signal;

reg voltage_signal_valid_delay1;
reg voltage_signal_valid_last_delay1;

always @ (posedge clk) begin
  if (rst) begin
    sin_cos_out_valid <= 0;
    sin_cos_out_valid_last <= 0;

    integral_voltage_signal <= 0;

    voltage_signal_valid_delay1 <= 0;
    voltage_signal_valid_last_delay1 <= 0;
  end else begin
    voltage_signal_valid_delay1 <= voltage_signal_valid;
    voltage_signal_valid_last_delay1 <= voltage_signal_valid_last;

    sin_cos_out_valid <= voltage_signal_valid_delay1;
    sin_cos_out_valid_last <= voltage_signal_valid_last_delay1;

    if (voltage_signal_valid) begin
      integral_voltage_signal <= integral_voltage_signal + voltage_signal;
    end
  end
end

// The project's tables (python/btlelib.py): cos[k] = round(127 cos(2 pi k / 2048)),
// sin[k] = round(127 sin(2 pi k / 2048)), k = 0 .. 2047, as the host writes them.
// Upstream reads both tables at the phase on every clock, from memories rewritten
// with those values, and shows the entries one clock later; so does this VCO, from
// the first eighth of the wave. In a quadrant (the two top bits of the phase) the
// offset o (0 .. 511) is folded into 0 .. 256: f = o, or 512 - o above 256, where
// sine and cosine swap. With s = |sin f| and c = |cos f|:
//   a = |sin o| = (o > 256) ? c : s,   b = |cos o| = (o > 256) ? s : c
//   quadrant 0: cos =  b, sin =  a        1: cos = -a, sin =  b
//            2: cos = -b, sin = -a        3: cos =  a, sin = -b
// The decomposition gives every entry of both tables exactly (all 2048 phases).
wire [SIN_COS_ADDR_BIT_WIDTH-1:0] phase = integral_voltage_signal[(SIN_COS_ADDR_BIT_WIDTH-1) : 0];
wire [1:0] quadrant = phase[10:9];
wire [8:0] offset = phase[8:0];
wire upper = offset[8] && (offset[7:0] != 0);
wire [8:0] folded = upper ? -offset : offset;   // 512 - o, modulo 512

wire [6:0] s;   // |sin| of the folded offset, 0 .. 90
wire [6:0] c;   // |cos| of the folded offset, 90 .. 127

// the first eighth of the wave, fixed: a ROM of 257 pairs (|sin|, |cos|)
reg [6:0] s_rom;
reg [6:0] c_rom;
always @* begin
  case (folded)
    9'd0: begin s_rom = 7'd0; c_rom = 7'd127; end
    9'd1: begin s_rom = 7'd0; c_rom = 7'd127; end
    9'd2: begin s_rom = 7'd1; c_rom = 7'd127; end
    9'd3: begin s_rom = 7'd1; c_rom = 7'd127; end
    9'd4: begin s_rom = 7'd2; c_rom = 7'd127; end
    9'd5: begin s_rom = 7'd2; c_rom = 7'd127; end
    9'd6: begin s_rom = 7'd2; c_rom = 7'd127; end
    9'd7: begin s_rom = 7'd3; c_rom = 7'd127; end
    9'd8: begin s_rom = 7'd3; c_rom = 7'd127; end
    9'd9: begin s_rom = 7'd4; c_rom = 7'd127; end
    9'd10: begin s_rom = 7'd4; c_rom = 7'd127; end
    9'd11: begin s_rom = 7'd4; c_rom = 7'd127; end
    9'd12: begin s_rom = 7'd5; c_rom = 7'd127; end
    9'd13: begin s_rom = 7'd5; c_rom = 7'd127; end
    9'd14: begin s_rom = 7'd5; c_rom = 7'd127; end
    9'd15: begin s_rom = 7'd6; c_rom = 7'd127; end
    9'd16: begin s_rom = 7'd6; c_rom = 7'd127; end
    9'd17: begin s_rom = 7'd7; c_rom = 7'd127; end
    9'd18: begin s_rom = 7'd7; c_rom = 7'd127; end
    9'd19: begin s_rom = 7'd7; c_rom = 7'd127; end
    9'd20: begin s_rom = 7'd8; c_rom = 7'd127; end
    9'd21: begin s_rom = 7'd8; c_rom = 7'd127; end
    9'd22: begin s_rom = 7'd9; c_rom = 7'd127; end
    9'd23: begin s_rom = 7'd9; c_rom = 7'd127; end
    9'd24: begin s_rom = 7'd9; c_rom = 7'd127; end
    9'd25: begin s_rom = 7'd10; c_rom = 7'd127; end
    9'd26: begin s_rom = 7'd10; c_rom = 7'd127; end
    9'd27: begin s_rom = 7'd11; c_rom = 7'd127; end
    9'd28: begin s_rom = 7'd11; c_rom = 7'd127; end
    9'd29: begin s_rom = 7'd11; c_rom = 7'd126; end
    9'd30: begin s_rom = 7'd12; c_rom = 7'd126; end
    9'd31: begin s_rom = 7'd12; c_rom = 7'd126; end
    9'd32: begin s_rom = 7'd12; c_rom = 7'd126; end
    9'd33: begin s_rom = 7'd13; c_rom = 7'd126; end
    9'd34: begin s_rom = 7'd13; c_rom = 7'd126; end
    9'd35: begin s_rom = 7'd14; c_rom = 7'd126; end
    9'd36: begin s_rom = 7'd14; c_rom = 7'd126; end
    9'd37: begin s_rom = 7'd14; c_rom = 7'd126; end
    9'd38: begin s_rom = 7'd15; c_rom = 7'd126; end
    9'd39: begin s_rom = 7'd15; c_rom = 7'd126; end
    9'd40: begin s_rom = 7'd16; c_rom = 7'd126; end
    9'd41: begin s_rom = 7'd16; c_rom = 7'd126; end
    9'd42: begin s_rom = 7'd16; c_rom = 7'd126; end
    9'd43: begin s_rom = 7'd17; c_rom = 7'd126; end
    9'd44: begin s_rom = 7'd17; c_rom = 7'd126; end
    9'd45: begin s_rom = 7'd17; c_rom = 7'd126; end
    9'd46: begin s_rom = 7'd18; c_rom = 7'd126; end
    9'd47: begin s_rom = 7'd18; c_rom = 7'd126; end
    9'd48: begin s_rom = 7'd19; c_rom = 7'd126; end
    9'd49: begin s_rom = 7'd19; c_rom = 7'd126; end
    9'd50: begin s_rom = 7'd19; c_rom = 7'd126; end
    9'd51: begin s_rom = 7'd20; c_rom = 7'd125; end
    9'd52: begin s_rom = 7'd20; c_rom = 7'd125; end
    9'd53: begin s_rom = 7'd21; c_rom = 7'd125; end
    9'd54: begin s_rom = 7'd21; c_rom = 7'd125; end
    9'd55: begin s_rom = 7'd21; c_rom = 7'd125; end
    9'd56: begin s_rom = 7'd22; c_rom = 7'd125; end
    9'd57: begin s_rom = 7'd22; c_rom = 7'd125; end
    9'd58: begin s_rom = 7'd22; c_rom = 7'd125; end
    9'd59: begin s_rom = 7'd23; c_rom = 7'd125; end
    9'd60: begin s_rom = 7'd23; c_rom = 7'd125; end
    9'd61: begin s_rom = 7'd24; c_rom = 7'd125; end
    9'd62: begin s_rom = 7'd24; c_rom = 7'd125; end
    9'd63: begin s_rom = 7'd24; c_rom = 7'd125; end
    9'd64: begin s_rom = 7'd25; c_rom = 7'd125; end
    9'd65: begin s_rom = 7'd25; c_rom = 7'd124; end
    9'd66: begin s_rom = 7'd26; c_rom = 7'd124; end
    9'd67: begin s_rom = 7'd26; c_rom = 7'd124; end
    9'd68: begin s_rom = 7'd26; c_rom = 7'd124; end
    9'd69: begin s_rom = 7'd27; c_rom = 7'd124; end
    9'd70: begin s_rom = 7'd27; c_rom = 7'd124; end
    9'd71: begin s_rom = 7'd27; c_rom = 7'd124; end
    9'd72: begin s_rom = 7'd28; c_rom = 7'd124; end
    9'd73: begin s_rom = 7'd28; c_rom = 7'd124; end
    9'd74: begin s_rom = 7'd29; c_rom = 7'd124; end
    9'd75: begin s_rom = 7'd29; c_rom = 7'd124; end
    9'd76: begin s_rom = 7'd29; c_rom = 7'd124; end
    9'd77: begin s_rom = 7'd30; c_rom = 7'd123; end
    9'd78: begin s_rom = 7'd30; c_rom = 7'd123; end
    9'd79: begin s_rom = 7'd30; c_rom = 7'd123; end
    9'd80: begin s_rom = 7'd31; c_rom = 7'd123; end
    9'd81: begin s_rom = 7'd31; c_rom = 7'd123; end
    9'd82: begin s_rom = 7'd32; c_rom = 7'd123; end
    9'd83: begin s_rom = 7'd32; c_rom = 7'd123; end
    9'd84: begin s_rom = 7'd32; c_rom = 7'd123; end
    9'd85: begin s_rom = 7'd33; c_rom = 7'd123; end
    9'd86: begin s_rom = 7'd33; c_rom = 7'd123; end
    9'd87: begin s_rom = 7'd33; c_rom = 7'd123; end
    9'd88: begin s_rom = 7'd34; c_rom = 7'd122; end
    9'd89: begin s_rom = 7'd34; c_rom = 7'd122; end
    9'd90: begin s_rom = 7'd35; c_rom = 7'd122; end
    9'd91: begin s_rom = 7'd35; c_rom = 7'd122; end
    9'd92: begin s_rom = 7'd35; c_rom = 7'd122; end
    9'd93: begin s_rom = 7'd36; c_rom = 7'd122; end
    9'd94: begin s_rom = 7'd36; c_rom = 7'd122; end
    9'd95: begin s_rom = 7'd36; c_rom = 7'd122; end
    9'd96: begin s_rom = 7'd37; c_rom = 7'd122; end
    9'd97: begin s_rom = 7'd37; c_rom = 7'd121; end
    9'd98: begin s_rom = 7'd38; c_rom = 7'd121; end
    9'd99: begin s_rom = 7'd38; c_rom = 7'd121; end
    9'd100: begin s_rom = 7'd38; c_rom = 7'd121; end
    9'd101: begin s_rom = 7'd39; c_rom = 7'd121; end
    9'd102: begin s_rom = 7'd39; c_rom = 7'd121; end
    9'd103: begin s_rom = 7'd39; c_rom = 7'd121; end
    9'd104: begin s_rom = 7'd40; c_rom = 7'd121; end
    9'd105: begin s_rom = 7'd40; c_rom = 7'd120; end
    9'd106: begin s_rom = 7'd41; c_rom = 7'd120; end
    9'd107: begin s_rom = 7'd41; c_rom = 7'd120; end
    9'd108: begin s_rom = 7'd41; c_rom = 7'd120; end
    9'd109: begin s_rom = 7'd42; c_rom = 7'd120; end
    9'd110: begin s_rom = 7'd42; c_rom = 7'd120; end
    9'd111: begin s_rom = 7'd42; c_rom = 7'd120; end
    9'd112: begin s_rom = 7'd43; c_rom = 7'd120; end
    9'd113: begin s_rom = 7'd43; c_rom = 7'd119; end
    9'd114: begin s_rom = 7'd44; c_rom = 7'd119; end
    9'd115: begin s_rom = 7'd44; c_rom = 7'd119; end
    9'd116: begin s_rom = 7'd44; c_rom = 7'd119; end
    9'd117: begin s_rom = 7'd45; c_rom = 7'd119; end
    9'd118: begin s_rom = 7'd45; c_rom = 7'd119; end
    9'd119: begin s_rom = 7'd45; c_rom = 7'd119; end
    9'd120: begin s_rom = 7'd46; c_rom = 7'd118; end
    9'd121: begin s_rom = 7'd46; c_rom = 7'd118; end
    9'd122: begin s_rom = 7'd46; c_rom = 7'd118; end
    9'd123: begin s_rom = 7'd47; c_rom = 7'd118; end
    9'd124: begin s_rom = 7'd47; c_rom = 7'd118; end
    9'd125: begin s_rom = 7'd48; c_rom = 7'd118; end
    9'd126: begin s_rom = 7'd48; c_rom = 7'd118; end
    9'd127: begin s_rom = 7'd48; c_rom = 7'd117; end
    9'd128: begin s_rom = 7'd49; c_rom = 7'd117; end
    9'd129: begin s_rom = 7'd49; c_rom = 7'd117; end
    9'd130: begin s_rom = 7'd49; c_rom = 7'd117; end
    9'd131: begin s_rom = 7'd50; c_rom = 7'd117; end
    9'd132: begin s_rom = 7'd50; c_rom = 7'd117; end
    9'd133: begin s_rom = 7'd50; c_rom = 7'd117; end
    9'd134: begin s_rom = 7'd51; c_rom = 7'd116; end
    9'd135: begin s_rom = 7'd51; c_rom = 7'd116; end
    9'd136: begin s_rom = 7'd51; c_rom = 7'd116; end
    9'd137: begin s_rom = 7'd52; c_rom = 7'd116; end
    9'd138: begin s_rom = 7'd52; c_rom = 7'd116; end
    9'd139: begin s_rom = 7'd53; c_rom = 7'd116; end
    9'd140: begin s_rom = 7'd53; c_rom = 7'd115; end
    9'd141: begin s_rom = 7'd53; c_rom = 7'd115; end
    9'd142: begin s_rom = 7'd54; c_rom = 7'd115; end
    9'd143: begin s_rom = 7'd54; c_rom = 7'd115; end
    9'd144: begin s_rom = 7'd54; c_rom = 7'd115; end
    9'd145: begin s_rom = 7'd55; c_rom = 7'd115; end
    9'd146: begin s_rom = 7'd55; c_rom = 7'd114; end
    9'd147: begin s_rom = 7'd55; c_rom = 7'd114; end
    9'd148: begin s_rom = 7'd56; c_rom = 7'd114; end
    9'd149: begin s_rom = 7'd56; c_rom = 7'd114; end
    9'd150: begin s_rom = 7'd56; c_rom = 7'd114; end
    9'd151: begin s_rom = 7'd57; c_rom = 7'd114; end
    9'd152: begin s_rom = 7'd57; c_rom = 7'd113; end
    9'd153: begin s_rom = 7'd57; c_rom = 7'd113; end
    9'd154: begin s_rom = 7'd58; c_rom = 7'd113; end
    9'd155: begin s_rom = 7'd58; c_rom = 7'd113; end
    9'd156: begin s_rom = 7'd58; c_rom = 7'd113; end
    9'd157: begin s_rom = 7'd59; c_rom = 7'd113; end
    9'd158: begin s_rom = 7'd59; c_rom = 7'd112; end
    9'd159: begin s_rom = 7'd60; c_rom = 7'd112; end
    9'd160: begin s_rom = 7'd60; c_rom = 7'd112; end
    9'd161: begin s_rom = 7'd60; c_rom = 7'd112; end
    9'd162: begin s_rom = 7'd61; c_rom = 7'd112; end
    9'd163: begin s_rom = 7'd61; c_rom = 7'd111; end
    9'd164: begin s_rom = 7'd61; c_rom = 7'd111; end
    9'd165: begin s_rom = 7'd62; c_rom = 7'd111; end
    9'd166: begin s_rom = 7'd62; c_rom = 7'd111; end
    9'd167: begin s_rom = 7'd62; c_rom = 7'd111; end
    9'd168: begin s_rom = 7'd63; c_rom = 7'd111; end
    9'd169: begin s_rom = 7'd63; c_rom = 7'd110; end
    9'd170: begin s_rom = 7'd63; c_rom = 7'd110; end
    9'd171: begin s_rom = 7'd64; c_rom = 7'd110; end
    9'd172: begin s_rom = 7'd64; c_rom = 7'd110; end
    9'd173: begin s_rom = 7'd64; c_rom = 7'd110; end
    9'd174: begin s_rom = 7'd65; c_rom = 7'd109; end
    9'd175: begin s_rom = 7'd65; c_rom = 7'd109; end
    9'd176: begin s_rom = 7'd65; c_rom = 7'd109; end
    9'd177: begin s_rom = 7'd66; c_rom = 7'd109; end
    9'd178: begin s_rom = 7'd66; c_rom = 7'd109; end
    9'd179: begin s_rom = 7'd66; c_rom = 7'd108; end
    9'd180: begin s_rom = 7'd67; c_rom = 7'd108; end
    9'd181: begin s_rom = 7'd67; c_rom = 7'd108; end
    9'd182: begin s_rom = 7'd67; c_rom = 7'd108; end
    9'd183: begin s_rom = 7'd68; c_rom = 7'd108; end
    9'd184: begin s_rom = 7'd68; c_rom = 7'd107; end
    9'd185: begin s_rom = 7'd68; c_rom = 7'd107; end
    9'd186: begin s_rom = 7'd69; c_rom = 7'd107; end
    9'd187: begin s_rom = 7'd69; c_rom = 7'd107; end
    9'd188: begin s_rom = 7'd69; c_rom = 7'd106; end
    9'd189: begin s_rom = 7'd70; c_rom = 7'd106; end
    9'd190: begin s_rom = 7'd70; c_rom = 7'd106; end
    9'd191: begin s_rom = 7'd70; c_rom = 7'd106; end
    9'd192: begin s_rom = 7'd71; c_rom = 7'd106; end
    9'd193: begin s_rom = 7'd71; c_rom = 7'd105; end
    9'd194: begin s_rom = 7'd71; c_rom = 7'd105; end
    9'd195: begin s_rom = 7'd72; c_rom = 7'd105; end
    9'd196: begin s_rom = 7'd72; c_rom = 7'd105; end
    9'd197: begin s_rom = 7'd72; c_rom = 7'd105; end
    9'd198: begin s_rom = 7'd72; c_rom = 7'd104; end
    9'd199: begin s_rom = 7'd73; c_rom = 7'd104; end
    9'd200: begin s_rom = 7'd73; c_rom = 7'd104; end
    9'd201: begin s_rom = 7'd73; c_rom = 7'd104; end
    9'd202: begin s_rom = 7'd74; c_rom = 7'd103; end
    9'd203: begin s_rom = 7'd74; c_rom = 7'd103; end
    9'd204: begin s_rom = 7'd74; c_rom = 7'd103; end
    9'd205: begin s_rom = 7'd75; c_rom = 7'd103; end
    9'd206: begin s_rom = 7'd75; c_rom = 7'd102; end
    9'd207: begin s_rom = 7'd75; c_rom = 7'd102; end
    9'd208: begin s_rom = 7'd76; c_rom = 7'd102; end
    9'd209: begin s_rom = 7'd76; c_rom = 7'd102; end
    9'd210: begin s_rom = 7'd76; c_rom = 7'd102; end
    9'd211: begin s_rom = 7'd77; c_rom = 7'd101; end
    9'd212: begin s_rom = 7'd77; c_rom = 7'd101; end
    9'd213: begin s_rom = 7'd77; c_rom = 7'd101; end
    9'd214: begin s_rom = 7'd78; c_rom = 7'd101; end
    9'd215: begin s_rom = 7'd78; c_rom = 7'd100; end
    9'd216: begin s_rom = 7'd78; c_rom = 7'd100; end
    9'd217: begin s_rom = 7'd78; c_rom = 7'd100; end
    9'd218: begin s_rom = 7'd79; c_rom = 7'd100; end
    9'd219: begin s_rom = 7'd79; c_rom = 7'd99; end
    9'd220: begin s_rom = 7'd79; c_rom = 7'd99; end
    9'd221: begin s_rom = 7'd80; c_rom = 7'd99; end
    9'd222: begin s_rom = 7'd80; c_rom = 7'd99; end
    9'd223: begin s_rom = 7'd80; c_rom = 7'd98; end
    9'd224: begin s_rom = 7'd81; c_rom = 7'd98; end
    9'd225: begin s_rom = 7'd81; c_rom = 7'd98; end
    9'd226: begin s_rom = 7'd81; c_rom = 7'd98; end
    9'd227: begin s_rom = 7'd81; c_rom = 7'd97; end
    9'd228: begin s_rom = 7'd82; c_rom = 7'd97; end
    9'd229: begin s_rom = 7'd82; c_rom = 7'd97; end
    9'd230: begin s_rom = 7'd82; c_rom = 7'd97; end
    9'd231: begin s_rom = 7'd83; c_rom = 7'd96; end
    9'd232: begin s_rom = 7'd83; c_rom = 7'd96; end
    9'd233: begin s_rom = 7'd83; c_rom = 7'd96; end
    9'd234: begin s_rom = 7'd84; c_rom = 7'd96; end
    9'd235: begin s_rom = 7'd84; c_rom = 7'd95; end
    9'd236: begin s_rom = 7'd84; c_rom = 7'd95; end
    9'd237: begin s_rom = 7'd84; c_rom = 7'd95; end
    9'd238: begin s_rom = 7'd85; c_rom = 7'd95; end
    9'd239: begin s_rom = 7'd85; c_rom = 7'd94; end
    9'd240: begin s_rom = 7'd85; c_rom = 7'd94; end
    9'd241: begin s_rom = 7'd86; c_rom = 7'd94; end
    9'd242: begin s_rom = 7'd86; c_rom = 7'd94; end
    9'd243: begin s_rom = 7'd86; c_rom = 7'd93; end
    9'd244: begin s_rom = 7'd86; c_rom = 7'd93; end
    9'd245: begin s_rom = 7'd87; c_rom = 7'd93; end
    9'd246: begin s_rom = 7'd87; c_rom = 7'd93; end
    9'd247: begin s_rom = 7'd87; c_rom = 7'd92; end
    9'd248: begin s_rom = 7'd88; c_rom = 7'd92; end
    9'd249: begin s_rom = 7'd88; c_rom = 7'd92; end
    9'd250: begin s_rom = 7'd88; c_rom = 7'd91; end
    9'd251: begin s_rom = 7'd88; c_rom = 7'd91; end
    9'd252: begin s_rom = 7'd89; c_rom = 7'd91; end
    9'd253: begin s_rom = 7'd89; c_rom = 7'd91; end
    9'd254: begin s_rom = 7'd89; c_rom = 7'd90; end
    9'd255: begin s_rom = 7'd90; c_rom = 7'd90; end
    9'd256: begin s_rom = 7'd90; c_rom = 7'd90; end
    default: begin s_rom = 7'd0; c_rom = 7'd0; end  // unreachable: folded <= 256
  endcase
end
assign s = s_rom;
assign c = c_rom;

wire [6:0] a = upper ? c : s;
wire [6:0] b = upper ? s : c;
wire [6:0] cos_magnitude = quadrant[0] ? a : b;
wire [6:0] sin_magnitude = quadrant[0] ? b : a;
wire cos_negative = quadrant[0] ^ quadrant[1];
wire sin_negative = quadrant[1];

always @ (posedge clk) begin
  cos_out <= cos_negative ? -$signed({1'b0, cos_magnitude}) : $signed({1'b0, cos_magnitude});
  sin_out <= sin_negative ? -$signed({1'b0, sin_magnitude}) : $signed({1'b0, sin_magnitude});
end

// Fixed tables deliberately ignore programming ports. Rounding keeps bits [14:8].
wire unused_fixed_table_interface = &{1'b0, cos_table_write_address, cos_table_write_data,
  sin_table_write_address, sin_table_write_data};

endmodule
