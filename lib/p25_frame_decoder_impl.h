/* -*- c++ -*- */
/*
 * Copyright 2009, 2010, 2011, 2012, 2013, 2014 Max H. Parke KA1RBI
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

#include "p25p1_fdma.h"
#include <arpa/inet.h>
#include <netinet/in.h>
#include <scanner/p25_frame_decoder.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <deque>


namespace gr
{
namespace scanner
{
class p25_frame_decoder_impl : public p25_frame_decoder
{
private:
   p25p1_fdma p1fdma;

public:
   p25_frame_decoder_impl(int debug);
   ~p25_frame_decoder_impl();

   // Where all the action really happens
   virtual int work(int noutput_items,
      gr_vector_const_void_star& input_items,
      gr_vector_void_star& output_items);
};

} // namespace scanner
} // namespace gr

