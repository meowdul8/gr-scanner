/* -*- c++ -*- */
/*
 * Copyright 2010, 2011, 2012, 2013, 2014 Max H. Parke KA1RBI
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

#include "p25_frame_decoder_impl.h"
#include <errno.h>
#include <gnuradio/io_signature.h>
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
p25_frame_decoder::sptr p25_frame_decoder::make(int debug)
{
   return gnuradio::get_initial_sptr(new p25_frame_decoder_impl(debug));
}

/*
 * The private constructor
 */

/*
 * Our virtual destructor.
 */
p25_frame_decoder_impl::~p25_frame_decoder_impl() {}

static const int MIN_IN = 1; // mininum number of input streams
static const int MAX_IN = 1; // maximum number of input streams

/*
 * The private constructor
 */
p25_frame_decoder_impl::p25_frame_decoder_impl(int debug)
   : gr::sync_block("p25_frame_decoder",
      gr::io_signature::make(MIN_IN, MAX_IN, sizeof(char)),
      gr::io_signature::make(0, 0, 0))
   , p1fdma(debug, *this)
{
   message_port_register_out(pmt::mp("p25"));
}

int p25_frame_decoder_impl::work(int noutput_items,
   gr_vector_const_void_star& input_items,
   gr_vector_void_star& output_items)
{
   const uint8_t* in = (const uint8_t*) input_items[0];

   p1fdma.rx_sym(in, noutput_items);
   // Tell runtime system how many output items we produced.
   return noutput_items;
}

} /* namespace scanner */
} /* namespace gr */
