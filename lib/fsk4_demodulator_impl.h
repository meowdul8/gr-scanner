/* -*- c++ -*- */
/*
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

#pragma once

#include <scanner/fsk4_demodulator.h>

namespace gr
{
namespace scanner
{

class fsk4_demodulator_impl : public fsk4_demodulator
{
private:
   const float d_block_rate;
   std::vector<float> d_history;
   size_t d_history_last;
   double d_symbol_clock;
   double d_symbol_spread;
   const float d_symbol_time;
   double fine_frequency_correction;
   double coarse_frequency_correction;

   /**
    * Called when we want the input frequency to be adjusted.
    */
   void send_frequency_correction();

   /**
    * Tracking loop.
    */
   bool tracking_loop_mmse(float input, char* output);

public:
   fsk4_demodulator_impl(float sample_rate, float symbol_rate);
   ~fsk4_demodulator_impl();

   // Where all the action really happens
   void forecast(int noutput_items, gr_vector_int& ninput_items_required);

   int general_work(int noutput_items,
      gr_vector_int& ninput_items,
      gr_vector_const_void_star& input_items,
      gr_vector_void_star& output_items);
};

} // namespace scanner
} // namespace gr

