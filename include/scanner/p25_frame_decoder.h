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

#include <gnuradio/sync_block.h>
#include <scanner/api.h>

namespace gr
{
namespace scanner
{
/*!
 * \brief <+description of block+>
 * \ingroup scanner
 *
 */
class SCANNER_API p25_frame_decoder : virtual public gr::sync_block
{
public:
   typedef boost::shared_ptr<p25_frame_decoder> sptr;

   /*!
    * \brief Return a shared_ptr to a new instance of
    * gr::scanner::p25_frame_decoder_impl.
    */
   static sptr make(int debug);
};

} // namespace scanner
} // namespace gr

