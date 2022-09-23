/* -*- c++ -*- */

/*
 * construct P25 frames out of raw dibits
 * Copyright 2010, KA1RBI
 *
 * usage: after constructing, call rx_sym once per received dibit.
 * frame fields are available for inspection when true is returned
 */

#pragma once

namespace gr
{
namespace scanner
{

struct framer_stats
{
   uint32_t symbols_received;
   uint32_t syncs_detected;
   uint32_t good_nids;
   uint32_t bad_nids;

   framer_stats()
   {
      reset();
   }

   void reset()
   {
      symbols_received = 0;
      syncs_detected = 0;
      good_nids = 0;
      bad_nids = 0;
   }
};

class p25_framer
{
private:
   typedef std::vector<bool> bit_vector;
   // internal functions
   bool nid_codeword(uint64_t acc);
   // internal instance variables and state
   uint8_t reverse_p;
   int nid_syms;
   uint32_t next_bit;
   uint64_t nid_accum;
   struct framer_stats stats;

   uint32_t frame_size_limit;
   int d_debug;

public:
   p25_framer(int debug = 0);
   ~p25_framer(); // destructor
   bool rx_sym(uint8_t dibit);
   struct framer_stats get_stats()
   {
      return stats;
   }

   // info from received frame
   uint64_t nid_word; // received NID word
   uint32_t nac; // extracted NAC
   uint32_t duid; // extracted DUID
   uint8_t parity; // extracted DUID parity
   bit_vector frame_body; // all bits in frame
   uint32_t frame_size; // number of bits in frame_body
   uint32_t bch_errors; // number of errors detected in bch
};

} // namespace scanner
} // namespace gr
