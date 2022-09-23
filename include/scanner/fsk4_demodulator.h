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

#include <gnuradio/block.h>
#include <scanner/api.h>

namespace gr
{
namespace scanner
{

/*!
 * \brief <+description of block+>
 * \ingroup p25tools
 *
 */
class SCANNER_API fsk4_demodulator : virtual public gr::block
{
public:
   typedef boost::shared_ptr<fsk4_demodulator> sptr;

   /*!
    * \brief Return a shared_ptr to a new instance of p25tools::fsk4_demodulator.
    *
    * To avoid accidental use of raw pointers, p25tools::fsk4_demodulator's
    * constructor is in a private implementation
    * class. p25tools::fsk4_demodulator::make is the public interface for
    * creating new instances.
    */
   static sptr make(float sample_rate = 87500, float symbol_rate = 4800);
};

} // namespace scanner
} // namespace gr

