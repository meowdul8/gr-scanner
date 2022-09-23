/* -*- c++ -*- */
/*
 * Copyright 2010, 2011, 2012, 2013, 2014, 2018 Max H. Parke KA1RBI
 * Copyright 2017 Graham J. Norbury (modularization rewrite)
 * Copyright 2008, Michael Ossmann <mike@ossmann.com>
 * Copyright 2022 Aaron Rossetto <aaron.rossetto@gmail.com>
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#   include "config.h"
#endif

#include "bch.h"
#include "op25_imbe_frame.h"
#include "p25_frame.h"
#include "p25_framer.h"
#include "p25p1_fdma.h"
#include "rs.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <vector>

namespace gr
{
namespace scanner
{
p25p1_fdma::~p25p1_fdma()
{
   delete framer;
}

static uint16_t crc16(uint8_t buf[], int len)
{
   if(buf == 0)
      return -1;
   uint32_t poly = (1 << 12) + (1 << 5) + (1 << 0);
   uint32_t crc = 0;
   for(int i = 0; i < len; i++)
   {
      uint8_t bits = buf[i];
      for(int j = 0; j < 8; j++)
      {
         uint8_t bit = (bits >> (7 - j)) & 1;
         crc = ((crc << 1) | bit) & 0x1ffff;
         if(crc & 0x10000)
            crc = (crc & 0xffff) ^ poly;
      }
   }
   crc = crc ^ 0xffff;
   return crc & 0xffff;
}

/* translated from p25craft.py Michael Ossmann <mike@ossmann.com>  */
static uint32_t crc32(uint8_t buf[], int len)
{ /* length is nr. of bits */
   uint32_t g = 0x04c11db7;
   uint64_t crc = 0;
   for(int i = 0; i < len; i++)
   {
      crc <<= 1;
      int b = (buf[i / 8] >> (7 - (i % 8))) & 1;
      if(((crc >> 32) ^ b) & 1)
         crc ^= g;
   }
   crc = (crc & 0xffffffff) ^ 0xffffffff;
   return crc;
}

/* find_min is from wireshark/plugins/p25/packet-p25cai.c */
/* Copyright 2008, Michael Ossmann <mike@ossmann.com>  */
/* return the index of the lowest value in a list */
static int find_min(uint8_t list[], int len)
{
   int min = list[0];
   int index = 0;
   int unique = 1;
   int i;

   for(i = 1; i < len; i++)
   {
      if(list[i] < min)
      {
         min = list[i];
         index = i;
         unique = 1;
      }
      else if(list[i] == min)
      {
         unique = 0;
      }
   }
   /* return -1 if a minimum can't be found */
   if(!unique)
      return -1;

   return index;
}

/* count_bits is from wireshark/plugins/p25/packet-p25cai.c */
/* Copyright 2008, Michael Ossmann <mike@ossmann.com>  */
/* count the number of 1 bits in an int */
static int count_bits(unsigned int n)
{
   int i = 0;
   for(i = 0; n != 0; i++)
      n &= n - 1;
   return i;
}

/* adapted from wireshark/plugins/p25/packet-p25cai.c */
/* Copyright 2008, Michael Ossmann <mike@ossmann.com>  */
/* deinterleave and trellis1_2 decoding */
/* buf is assumed to be a buffer of 12 bytes */
static int block_deinterleave(bit_vector& bv, unsigned int start, uint8_t* buf)
{
   // clang-format off
	static const uint16_t deinterleave_tb[] = {
	  0,  1,  2,  3,  52, 53, 54, 55, 100,101,102,103, 148,149,150,151,
	  4,  5,  6,  7,  56, 57, 58, 59, 104,105,106,107, 152,153,154,155,
	  8,  9, 10, 11,  60, 61, 62, 63, 108,109,110,111, 156,157,158,159,
	 12, 13, 14, 15,  64, 65, 66, 67, 112,113,114,115, 160,161,162,163,
	 16, 17, 18, 19,  68, 69, 70, 71, 116,117,118,119, 164,165,166,167,
	 20, 21, 22, 23,  72, 73, 74, 75, 120,121,122,123, 168,169,170,171,
	 24, 25, 26, 27,  76, 77, 78, 79, 124,125,126,127, 172,173,174,175,
	 28, 29, 30, 31,  80, 81, 82, 83, 128,129,130,131, 176,177,178,179,
	 32, 33, 34, 35,  84, 85, 86, 87, 132,133,134,135, 180,181,182,183,
	 36, 37, 38, 39,  88, 89, 90, 91, 136,137,138,139, 184,185,186,187,
	 40, 41, 42, 43,  92, 93, 94, 95, 140,141,142,143, 188,189,190,191,
	 44, 45, 46, 47,  96, 97, 98, 99, 144,145,146,147, 192,193,194,195,
	 48, 49, 50, 51 };
   // clang-format on

   uint8_t hd[4];
   int b, d, j;
   int state = 0;
   uint8_t codeword;
   uint16_t crc;

   static const uint8_t next_words[4][4] = {{0x2, 0xC, 0x1, 0xF},
      {0xE, 0x0, 0xD, 0x3},
      {0x9, 0x7, 0xA, 0x4},
      {0x5, 0xB, 0x6, 0x8}};

   memset(buf, 0, 12);

   for(b = 0; b < 98 * 2; b += 4)
   {
      codeword = (bv[start + deinterleave_tb[b + 0]] << 3)
         + (bv[start + deinterleave_tb[b + 1]] << 2)
         + (bv[start + deinterleave_tb[b + 2]] << 1) + bv[start + deinterleave_tb[b + 3]];

      /* try each codeword in a row of the state transition table */
      for(j = 0; j < 4; j++)
      {
         /* find Hamming distance for candidate */
         hd[j] = count_bits(codeword ^ next_words[state][j]);
      }
      /* find the dibit that matches the most codeword bits (minimum Hamming distance) */
      state = find_min(hd, 4);
      /* error if minimum can't be found */
      if(state == -1)
         return -1; // decode error, return failure
      /* It also might be nice to report a condition where the minimum is
       * non-zero, i.e. an error has been corrected.  It probably shouldn't
       * be a permanent failure, though.
       *
       * DISSECTOR_ASSERT(hd[state] == 0);
       */

      /* append dibit onto output buffer */
      d = b >> 2; // dibit ctr
      if(d < 48)
      {
         buf[d >> 2] |= state << (6 - ((d % 4) * 2));
      }
   }
   return 0;
}

p25p1_fdma::p25p1_fdma(int debug, gr::block& owning_block)
   : d_debug(debug)
   , d_owning_block(owning_block)
   , framer(new p25_framer(debug))
   , ess_algid(0x80)
   , ess_keyid(0)
   , vf_tgid(0)
   , symbol_count_for_stats(480)
   , next_symbol_count_for_stats(symbol_count_for_stats)
{
}

void p25p1_fdma::process_HDU(const bit_vector& A)
{
   uint8_t MFID;
   int i, j, k, ec;
   uint32_t gly;
   std::vector<uint8_t> HB(63, 0); // hexbit vector
   int failures = 0;
   k = 0;
   if(d_debug >= 10)
   {
      fprintf(stderr, "NAC %03x HDU   ", framer->nac);
   }

   for(i = 0; i < 36; i++)
   {
      uint32_t CW = 0;
      for(j = 0; j < 18; j++)
      { // 18 bits / cw
         CW = (CW << 1) + A[hdu_codeword_bits[k++]];
      }
      gly = gly24128Dec(CW);
      HB[27 + i] = gly & 63;
      if(CW ^ gly24128Enc(gly))
         /* "failures" in this context means any mismatch,
          * disregarding how "recoverable" the error may be
          * and disregarding how many bits may mismatch */
         failures += 1;
   }
   ec = rs16.decode(HB); // Reed Solomon (36,20,17) error correction
   if(d_debug >= 10)
   {
      fprintf(stderr, "[%d/36 <%d>] ", failures, ec);
   }
   if(failures > 6)
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, "(ESS computation suppressed) ");
      }
      send_p25_pdu({{"ok", BOOL_DATA(false)}});

      return;
   }
   if(ec >= 0)
   {
      j = 27; // 72 bit MI
      for(i = 0; i < 9;)
      {
         ess_mi[i++] = (uint8_t)(HB[j] << 2) + (HB[j + 1] >> 4);
         ess_mi[i++] = (uint8_t)((HB[j + 1] & 0x0f) << 4) + (HB[j + 2] >> 2);
         ess_mi[i++] = (uint8_t)((HB[j + 2] & 0x03) << 6) + HB[j + 3];
         j += 4;
      }
      MFID = (HB[j] << 2) + (HB[j + 1] >> 4); // 8 bit MfrId
      ess_algid = ((HB[j + 1] & 0x0f) << 4) + (HB[j + 2] >> 2); // 8 bit AlgId
      ess_keyid = ((HB[j + 2] & 0x03) << 14) + (HB[j + 3] << 8) + (HB[j + 4] << 2)
         + (HB[j + 5] >> 4); // 16 bit KeyId
      vf_tgid = ((HB[j + 5] & 0x0f) << 12) + (HB[j + 6] << 6) + HB[j + 7]; // 16 bit TGID

      if(d_debug >= 10)
      {
         fprintf(stderr,
            "(ESS tgid=%d, algid=%x, keyid=%x, mi=",
            vf_tgid,
            ess_algid,
            ess_keyid);
         for(int i = 0; i < 9; i++)
         {
            fprintf(stderr, "%02x%c", ess_mi[i], (i == 8) ? ')' : ' ');
         }
         fprintf(stderr, " ");
      }
      // clang-format off
      send_p25_pdu({{"mfid", U8_HEX_DATA(MFID)},
                    {"tgid", U16_HEX_DATA(vf_tgid)},
                    {"algid", U8_HEX_DATA(ess_algid)},
                    {"keyid", U16_HEX_DATA(ess_keyid)},
                    {"mi", BUFFER_DATA(ess_mi, 9)},
                    {"ok", BOOL_DATA(true)}});
      // clang-format on
   }

   if(d_debug >= 10)
   {
      fprintf(stderr, "\n");
   }
}

int p25p1_fdma::process_LLDU(const bit_vector& A, std::vector<uint8_t>& HB)
{ // return count of hamming failures
   int i, j, k;
   int failures = 0;
   k = 0;
   for(i = 0; i < 24; i++)
   { // 24 10-bit codewords
      uint32_t CW = 0;
      for(j = 0; j < 10; j++)
      { // 10 bits / cw
         CW = (CW << 1) + A[imbe_ldu_ls_data_bits[k++]];
      }
      HB[39 + i] = hmg1063Dec(CW >> 4, CW & 0x0f);
      if(CW ^ ((HB[39 + i] << 4) + hmg1063EncTbl[HB[39 + i]]))
         failures += 1;
   }
   return failures;
}

void p25p1_fdma::process_LDU1(const bit_vector& A)
{
   int hmg_failures;
   if(d_debug >= 10)
   {
      fprintf(stderr, "NAC %03x LDU1  ", framer->nac);
   }

   std::vector<uint8_t> HB(63, 0); // hexbit vector
   hmg_failures = process_LLDU(A, HB);
   if(d_debug >= 10)
   {
      fprintf(stderr, "[%d/24] ", hmg_failures);
   }

   std::vector<uint8_t> lcw(9, 0);
   bool lcw_ok = false;
   if(hmg_failures < 6)
      lcw_ok = process_LCW(HB, lcw);
   else
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, " (LCW computation suppressed)");
      }
   }

   // LDUx frames with exactly 20 failures seem to be not uncommon (and deliberate?)
   // a TDU almost always immediately follows these code violations
   std::vector<uint8_t> packed_voice_frames(11 * 9, 0);
   bool ok = false;
   if(hmg_failures < 16)
   {
      process_voice(A, packed_voice_frames);
      ok = true;
   }

   // clang-format off
   send_p25_pdu({{"lcw", BUFFER_DATA(lcw.data(), 9)},
                 {"imbe", BUFFER_DATA(packed_voice_frames.data(), 99)},
                 {"ok", BOOL_DATA(ok)}});
   // clang-format on

   if(d_debug >= 10)
      fprintf(stderr, "\n");
}

void p25p1_fdma::process_LDU2(const bit_vector& A)
{
   std::string s = "";
   int hmg_failures;
   if(d_debug >= 10)
   {
      fprintf(stderr, "NAC %03x LDU2  ", framer->nac);
   }

   std::vector<uint8_t> HB(63, 0); // hexbit vector
   hmg_failures = process_LLDU(A, HB);
   if(d_debug >= 10)
   {
      fprintf(stderr, "[%d/24] ", hmg_failures);
   }

   int i, j, ec = 0;
   if(hmg_failures < 6)
   {
      ec = rs8.decode(HB); // Reed Solomon (24,16,9) error correction
      if(ec >= 0)
      { // save info if good decode
         j = 39; // 72 bit MI
         for(i = 0; i < 9;)
         {
            ess_mi[i++] = (uint8_t)(HB[j] << 2) + (HB[j + 1] >> 4);
            ess_mi[i++] = (uint8_t)((HB[j + 1] & 0x0f) << 4) + (HB[j + 2] >> 2);
            ess_mi[i++] = (uint8_t)((HB[j + 2] & 0x03) << 6) + HB[j + 3];
            j += 4;
         }
         ess_algid = (HB[j] << 2) + (HB[j + 1] >> 4); // 8 bit AlgId
         ess_keyid =
            ((HB[j + 1] & 0x0f) << 12) + (HB[j + 2] << 6) + HB[j + 3]; // 16 bit KeyId

         if(d_debug >= 10)
         {
            fprintf(stderr, "(ESS algid=%x, keyid=%x, mi=", ess_algid, ess_keyid);
            for(int i = 0; i < 9; i++)
            {
               fprintf(stderr, "%02x%c", ess_mi[i], (i == 8) ? ')' : ' ');
            }
            fprintf(stderr, " ");
         }
      }
   }
   else
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, " (ESS computation suppressed)");
      }
   }

   std::vector<uint8_t> packed_voice_frames(11 * 9, 0);
   bool ok = false;
   if(hmg_failures < 16)
   {
      process_voice(A, packed_voice_frames);
      ok = true;
   }

   // clang-format off
   send_p25_pdu(
      {{"imbe", BUFFER_DATA(packed_voice_frames.data(), 99)},
       {"ok", BOOL_DATA(ok)}});
   // clang-format on

   if(d_debug >= 10)
      fprintf(stderr, "\n");
}

void p25p1_fdma::process_TTDU() {}

void p25p1_fdma::process_TDU()
{
   if(d_debug >= 10)
   {
      fprintf(stderr, "NAC %03x TDU   ", framer->nac);
   }

   process_TTDU();

   if(d_debug >= 10)
   {
      fprintf(stderr, "\n");
   }

   send_p25_pdu({{"ok", BOOL_DATA(true)}});
}

void p25p1_fdma::process_TDULC(const bit_vector& A)
{
   if(d_debug >= 10)
   {
      fprintf(stderr, "NAC %03x TDULC ", framer->nac);
   }

   process_TTDU();

   int i, j, k;
   std::vector<uint8_t> HB(63, 0); // hexbit vector
   k = 0;
   for(i = 0; i <= 22; i += 2)
   {
      uint32_t CW = 0;
      for(j = 0; j < 12; j++)
      { // 12 24-bit codewords
         CW = (CW << 1) + A[hdu_codeword_bits[k++]];
         CW = (CW << 1) + A[hdu_codeword_bits[k++]];
      }
      uint32_t D = gly24128Dec(CW);
      HB[39 + i] = D >> 6;
      HB[40 + i] = D & 63;
   }

   std::vector<uint8_t> lcw(9, 0);
   bool ok = process_LCW(HB, lcw);
   // clang-format off
   send_p25_pdu({{"lcw", BUFFER_DATA(lcw.data(), 9)},
                 {"ok", BOOL_DATA(ok)}});
   // clang-format on

   if(d_debug >= 10)
   {
      fprintf(stderr, "\n");
   }
}

bool p25p1_fdma::process_LCW(std::vector<uint8_t>& HB, std::vector<uint8_t>& lcw)
{
   if(d_debug >= 10)
   {
      fprintf(stderr, "(LCW ");
   }

   int ec = rs12.decode(HB); // Reed Solomon (24,12,13) error correction
   if(ec < 0)
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, "[BAD RS])");
      }
      return false; // failed CRC
   }

   int i, j;
   ; // Convert hexbits to bytes
   j = 0;
   for(i = 0; i < 9;)
   {
      lcw[i++] = (uint8_t)(HB[j + 39] << 2) + (HB[j + 40] >> 4);
      lcw[i++] = (uint8_t)((HB[j + 40] & 0x0f) << 4) + (HB[j + 41] >> 2);
      lcw[i++] = (uint8_t)((HB[j + 41] & 0x03) << 6) + HB[j + 42];
      j += 4;
   }

   if(d_debug >= 10)
   {
      for(i = 0; i < 9; i++)
         fprintf(stderr, "%02x%c", lcw[i], (i == 8) ? ')' : ' ');
      fprintf(stderr, " ");
   }

   return true;
}

void p25p1_fdma::process_TSBK(const bit_vector& fr, uint32_t fr_len)
{
   uint8_t lb = 0;
   bool crc_ok = true;
   block_vector deinterleave_buf;
   if(process_blocks(fr, fr_len, deinterleave_buf) == 0)
   {
      for(int j = 0; (j < deinterleave_buf.size()) && (lb == 0); j++)
      {
         if(crc16(deinterleave_buf[j].data(), 12) != 0) // validate CRC
         {
            crc_ok = false;
         }

         lb = deinterleave_buf[j][0] >> 7; // last block flag

         if(d_debug >= 10)
         {
            fprintf(stderr, "NAC %03x TSBK  ", framer->nac);
            for(int i = 0; i < 12; i++)
            {
               fprintf(stderr, "%02x ", deinterleave_buf[j][i]);
            }
            if(!crc_ok)
            {
               fprintf(stderr, "[BAD CRC]");
            }
            fprintf(stderr, "\n");
         }

         // clang-format off
         send_p25_pdu({{"tsbk", BUFFER_DATA(deinterleave_buf[j].data(), 12)},
                       {"ok", BOOL_DATA(crc_ok)}});
         // clang-format on
      }
   }
   else
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, "NAC %03x TSBK  [BAD TRELLIS]\n", framer->nac);
      }

      send_p25_pdu({{"ok", BOOL_DATA(false)}});
   }
}

void p25p1_fdma::process_PDU(const bit_vector& fr, uint32_t fr_len)
{
   uint8_t fmt, sap, blks, op = 0;
   block_vector deinterleave_buf;
   bool header_crc_ok = true;
   bool payload_crc_ok = true;

   if(process_blocks(fr, fr_len, deinterleave_buf) == 0)
   {
      if(deinterleave_buf.size() > 0)
      { // extract all blocks associated with this PDU
         if(crc16(deinterleave_buf[0].data(), 12) != 0) { // validate PDU header
            header_crc_ok = false;
         }

         fmt = deinterleave_buf[0][0] & 0x1f;
         sap = deinterleave_buf[0][1] & 0x3f;
         blks = deinterleave_buf[0][6] & 0x7f;

         if((sap == 61) && ((fmt == 0x17) || (fmt == 0x15)))
         { // Multi Block Trunking messages
            if(blks > deinterleave_buf.size())
               return; // insufficient blocks available

            uint32_t crc1 = crc32(deinterleave_buf[1].data(), ((blks * 12) - 4) * 8);
            uint32_t crc2 = (deinterleave_buf[blks][8] << 24)
               + (deinterleave_buf[blks][9] << 16) + (deinterleave_buf[blks][10] << 8)
               + deinterleave_buf[blks][11];

            if(crc1 != crc2) {
               payload_crc_ok = false;
            }
            else
            {
               if(d_debug >= 10)
               {
                  if(fmt == 0x15)
                  {
                     op = deinterleave_buf[1][0] & 0x3f; // Unconfirmed MBT format
                  }
                  else if(fmt == 0x17)
                  {
                     op = deinterleave_buf[0][7] & 0x3f; // Alternate MBT format
                  }

                  fprintf(stderr,
                     "NAC %03x PDU   fmt 0x%02x op 0x%02x blks %d  ",
                     framer->nac,
                     fmt,
                     op,
                     blks);
                  for(int j = 0; (j < blks + 1) && (j < 3); j++)
                  {
                     for(int i = 0; i < 12; i++)
                     {
                        fprintf(stderr, "%02x ", deinterleave_buf[j][i]);
                     }
                  }
                  fprintf(stderr, "\n");
               }
               p25_du_data pdu_data;
               pdu_data.push_back({"pdu", BUFFER_DATA(deinterleave_buf[0].data(), (size_t)(12 * (blks + 1)))});
               pdu_data.push_back({"ok", BOOL_DATA(header_crc_ok && payload_crc_ok)});
               send_p25_pdu(pdu_data);
            }
         }
         else
         {
            // clang-format off
            send_p25_pdu({{"fmt", U8_HEX_DATA(fmt)},
                          {"sap", U8_HEX_DATA(sap)},
                          {"blks", U8_HEX_DATA(blks)},
                          {"ok", BOOL_DATA(header_crc_ok)}});
            // clang-format on
         }
      }
   }
   else
   {
      if(d_debug >= 10)
      {
         fprintf(stderr, "NAC %03x PDU   [BAD TRELLIS]\n", framer->nac);
      }

      send_p25_pdu({{"ok", BOOL_DATA(false)}});
   }
}

int p25p1_fdma::process_blocks(const bit_vector& fr, uint32_t& fr_len, block_vector& dbuf)
{
   bit_vector bv;
   bv.reserve(fr_len >> 1);
   for(unsigned int d = 0; d < (fr_len >> 1); d++)
   { // eliminate status bits from frame
      if((d + 1) % 36 == 0)
         continue;
      bv.push_back(fr[d * 2]);
      bv.push_back(fr[d * 2 + 1]);
   }

   int bl_cnt = 0;
   int bl_len = (bv.size() - (48 + 64)) / 196;
   for(bl_cnt = 0; bl_cnt < bl_len; bl_cnt++)
   { // deinterleave,  decode trellis1_2, save 12 byte block
      dbuf.push_back({0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0});
      if(block_deinterleave(bv, 48 + 64 + bl_cnt * 196, dbuf[bl_cnt].data()) != 0)
      {
         dbuf.pop_back();
         return -1;
      }
   }
   return (bl_cnt > 0) ? 0 : -1;
}

void p25p1_fdma::process_voice(const bit_vector& A, std::vector<uint8_t>& pc)
{
   if(d_debug >= 10)
      fprintf(stderr, "\n");
   for(size_t i = 0; i < nof_voice_codewords; ++i)
   {
      voice_codeword cw(voice_codeword_sz);
      uint32_t E0, ET;
      uint32_t u[8];
      imbe_deinterleave(A, cw, i);
      // recover 88-bit IMBE voice code word
      imbe_header_decode(cw, u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], E0, ET);

      if(d_debug >= 10)
      {
         fprintf(stderr, "                IMBE%ld ", i);

         packed_codeword p_cw;
         imbe_pack(p_cw, u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7]);
         for(size_t j = 0; j < 11; j++)
         {
            fprintf(stderr, "%02x ", p_cw[j]);
         }
         fprintf(stderr, "\n");
      }

      pc[11 * i + 0] = (u[0] >> 4);
      pc[11 * i + 1] = (((u[0] & 0xf) << 4) + (u[1] >> 8));
      pc[11 * i + 2] = (u[1] & 0xff);
      pc[11 * i + 3] = (u[2] >> 4);
      pc[11 * i + 4] = (((u[2] & 0xf) << 4) + (u[3] >> 8));
      pc[11 * i + 5] = (u[3] & 0xff);
      pc[11 * i + 6] = (u[4] >> 3);
      pc[11 * i + 7] = (((u[4] & 0x7) << 5) + (u[5] >> 6));
      pc[11 * i + 8] = (((u[5] & 0x3f) << 2) + (u[6] >> 9));
      pc[11 * i + 9] = (u[6] >> 1);
      pc[11 * i + 10] = (((u[6] & 0x1) << 7) + (u[7] >> 1));
   }
}

void p25p1_fdma::send_p25_pdu(const p25_du_data& data)
{
   char frame_data[64];
   sprintf(frame_data,
      "{\"p25_du\": {\"nac\": \"0x%03x\", \"duid\": \"0x%01x\", ",
      framer->nac,
      framer->duid);

   std::string json_string(frame_data);
   size_t num_datum = data.size();
   size_t count = 0;
   for(const auto& datum : data)
   {
      json_string += "\"" + datum.first + "\": ";
      json_string += datum.second.serialize();
      if(count < num_datum - 1)
         json_string += ", ";
      count++;
   }
   json_string += "}}\n";

   pmt::pmt_t pdu_data =
      pmt::init_u8vector(json_string.size(), (const uint8_t*) json_string.data());
   d_owning_block.message_port_pub(pmt::intern("p25"), pdu_data);
}

void p25p1_fdma::rx_sym(const uint8_t* syms, int nsyms)
{
   for(int i1 = 0; i1 < nsyms; i1++)
   {
      if(framer->rx_sym(syms[i1] - '0'))
      { // complete frame was detected

         if(framer->nac == 0)
         { // discard frame if NAC is invalid
            return;
         }

         // extract additional signalling information and voice codewords
         switch(framer->duid)
         {
            case 0x00:
               process_HDU(framer->frame_body);
               break;
            case 0x03:
               process_TDU();
               break;
            case 0x05:
               process_LDU1(framer->frame_body);
               break;
            case 0x07:
               process_TSBK(framer->frame_body, framer->frame_size);
               break;
            case 0x0a:
               process_LDU2(framer->frame_body);
               break;
            case 0x0c:
               process_PDU(framer->frame_body, framer->frame_size);
               break;
            case 0x0f:
               process_TDULC(framer->frame_body);
               break;
         }
      } // end of complete frame
      struct framer_stats stats = framer->get_stats();
      if(stats.symbols_received > next_symbol_count_for_stats)
      {
         next_symbol_count_for_stats += symbol_count_for_stats;

         // clang-format off
         std::string stats_json = "{\"stats\": {";
         stats_json += "\"symbols\": " + std::to_string(stats.symbols_received) + ", ";
         stats_json += "\"syncs\": " + std::to_string(stats.syncs_detected) + ", ";
         stats_json += "\"good_nids\": " + std::to_string(stats.good_nids) + ", ";
         stats_json += "\"bad_nids\": " + std::to_string(stats.bad_nids) + "}}";
         // clang-format on

         pmt::pmt_t pdu_data =
            pmt::init_u8vector(stats_json.size(), (const uint8_t*) stats_json.data());
         d_owning_block.message_port_pub(pmt::intern("p25"), pdu_data);
      }
   }
}

} // namespace scanner
} // namespace gr
