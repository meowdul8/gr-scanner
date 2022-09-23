/* -*- c++ -*- */
/*
 * Copyright 2009, 2010, 2011, 2012, 2013, 2014 Max H. Parke KA1RBI
 * Copyright 2022 Aaron Rossetto <aaron.rossetto@ni.com>
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

#pragma once

#include "ezpwd/rs"
#include <gnuradio/block.h>
#include "p25_framer.h"

namespace gr
{
namespace scanner
{

struct typed_data
{
   enum class type
   {
      U8, U16, U32,
      U8_HEX, U16_HEX, U32_HEX,
      BUFFER,
   };

   type m_type;
   uintptr_t m_data;
   size_t m_len;

   typed_data(type type, uintptr_t data, size_t len) :
      m_type(type),
      m_data(data),
      m_len(len)
   {
   }

   std::string serialize() const
   {
      std::string result;
      char buf[16];
      switch(m_type)
      {
         case type::U8:
         case type::U16:
         case type::U32:
            sprintf(buf, "%d", (uint32_t) m_data);
            result = std::string(buf);
            break;
         case type::U8_HEX:
            sprintf(buf, "\"0x%02x\"", (uint32_t)(m_data & 0xff));
            result = std::string(buf);
            break;
         case type::U16_HEX:
            sprintf(buf, "\"0x%04x\"", (uint32_t)(m_data & 0xffff));
            result = std::string(buf);
            break;
         case type::U32_HEX:
            sprintf(buf, "\"0x%08x\"", (uint32_t) m_data);
            result = std::string(buf);
            break;
         case type::BUFFER:
         {
            result += "\"";
            uint8_t* p = reinterpret_cast<uint8_t*>(m_data);
            for(size_t i = 0; i < m_len; i++)
            {
               sprintf(buf, "%02x", p[i]);
               result += std::string(buf);
            }
            result += "\"";
            break;
         }
      }
      return result;
   }
};

#define U8_DATA(value) {typed_data::type::U8, (uintptr_t)(value), 0}
#define BOOL_DATA(value) {typed_data::type::U8, (value) ? (uintptr_t) 1 : (uintptr_t) 0, 0}
#define U16_DATA(value) {typed_data::type::U16, (uintptr_t)(value), 0}
#define U32_DATA(value) {typed_data::type::U32, (uintptr_t)(value), 0}
#define U8_HEX_DATA(value) {typed_data::type::U8_HEX, (uintptr_t)(value), 0}
#define U16_HEX_DATA(value) {typed_data::type::U16_HEX, (uintptr_t)(value), 0}
#define U32_HEX_DATA(value) {typed_data::type::U32_HEX, (uintptr_t)(value), 0}
#define BUFFER_DATA(value, len) {typed_data::type::BUFFER, (uintptr_t)(value), (len)}

typedef std::pair<std::string, typed_data> named_value;

class p25p1_fdma
{
private:
   typedef std::vector<bool> bit_vector;
   typedef std::array<uint8_t, 12> block_array;
   typedef std::vector<block_array> block_vector;

   // internal functions
   bool header_codeword(uint64_t acc, uint32_t& nac, uint32_t& duid);
   void process_HDU(const bit_vector& A);
   bool process_LCW(std::vector<uint8_t>& HB, std::vector<uint8_t>& lcw);
   int process_LLDU(const bit_vector& A, std::vector<uint8_t>& HB);
   void process_LDU1(const bit_vector& A);
   void process_LDU2(const bit_vector& A);
   void process_TTDU();
   void process_TDULC(const bit_vector& A);
   void process_TDU();
   void process_TSBK(const bit_vector& fr, uint32_t fr_len);
   void process_PDU(const bit_vector& fr, uint32_t fr_len);
   void process_voice(const bit_vector& A, std::vector<uint8_t>& pc);
   int process_blocks(const bit_vector& fr, uint32_t& fr_len, block_vector& dbuf);
   inline bool encrypted()
   {
      return (ess_algid != 0x80);
   }
   typedef std::vector<named_value> p25_du_data;
   void send_p25_pdu(const p25_du_data& data);

   // internal instance variables and state
   int d_debug;
   p25_framer* framer;
   gr::block& d_owning_block;

   ezpwd::RS<63, 55> rs8; // Reed-Solomon decoders for 8, 12 and 16 bit parity
   ezpwd::RS<63, 51> rs12;
   ezpwd::RS<63, 47> rs16;

   uint8_t ess_keyid;
   uint16_t ess_algid;
   uint8_t ess_mi[9] = {0};
   uint16_t vf_tgid;

   size_t symbol_count_for_stats;
   size_t next_symbol_count_for_stats;

public:
   p25p1_fdma(int debug, gr::block& owning_block);
   ~p25p1_fdma();

   void rx_sym(const uint8_t* syms, int nsyms);
};
} // namespace scanner
} // namespace gr
