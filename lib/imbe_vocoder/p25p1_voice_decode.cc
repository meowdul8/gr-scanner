/* -*- c++ -*- */
/*
 * GNU Radio interface for Pavel Yazev's Project 25 IMBE Encoder/Decoder
 *
 * Copyright 2009 Pavel Yazev E-mail: pyazev@gmail.com
 * Copyright 2009, 2010, 2011, 2012, 2013, 2014 KA1RBI
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

#include "p25p1_voice_decode.h"
#include <stdint.h>

p25p1_voice_decode::p25p1_voice_decode()
{
}

/*
 * Our virtual destructor.
 */
p25p1_voice_decode::~p25p1_voice_decode() {}

// 88 bits in (11 uint8_ts)
void p25p1_voice_decode::decode(const uint8_t* u, int16_t* snd)
{
   int16_t frame_vector[8];

   frame_vector[0] = (uint16_t(u[0]) << 4) | (u[1] >> 4);
   frame_vector[1] = ((uint16_t(u[1]) & 0xf) << 8) | u[2];
   frame_vector[2] = (uint16_t(u[3]) << 4) | (u[4] >> 4);
   frame_vector[3] = ((uint16_t(u[4]) & 0xf) << 8) | u[5];
   frame_vector[4] = (uint16_t(u[6]) << 3) | ((u[7] & 0xe0) >> 5);
   frame_vector[5] = (uint16_t(u[7] & 0x1f) << 6) | ((u[8] & 0xfc) >> 2);
   frame_vector[6] = (uint16_t(u[9]) << 1) | ((u[10] & 0x80) >> 7);
   frame_vector[7] = ((uint16_t(u[10]) & 0x7f) << 1);
#if 0
   /* TEST*/ frame_vector[7] >>= 1;
#endif   
   vocoder.imbe_decode(frame_vector, snd);
}

void* imbe_decoder_make()
{
   return new p25p1_voice_decode();
}

void imbe_decoder_destroy(void* p)
{
   delete (p25p1_voice_decode*) p;
}

void imbe_decoder_decode(void* p, const uint8_t* u, int16_t* snd)
{
   p25p1_voice_decode* decoder = (p25p1_voice_decode*) p;
   decoder->decode(u, snd);
}
