/* -*- c++ -*- */
/*
 * Copyright 2009, 2010, 2011, 2012, 2013, 2014 Max H. Parke KA1RBI
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

#ifndef INCLUDED_OP25_REPEATER_P25P1_VOICE_DECODE_H
#define INCLUDED_OP25_REPEATER_P25P1_VOICE_DECODE_H

#include "imbe_vocoder.h"
#include <stdint.h>
#include <sys/time.h>
#include <deque>
#include <vector>

class p25p1_voice_decode
{
private:
   // Nothing to declare in this block.

public:
   p25p1_voice_decode();
   ~p25p1_voice_decode();
   void decode(const uint8_t* u, int16_t* snd);

private:
   imbe_vocoder vocoder;
};

extern "C"
{
   __attribute__((visibility("default"))) void* imbe_decoder_make();
   __attribute__((visibility("default"))) void imbe_decoder_destroy(void* p);
   __attribute__((visibility("default"))) void imbe_decoder_decode(void* p, const uint8_t* u, int16_t* snd);
};

#endif /* INCLUDED_OP25_REPEATER_P25P1_VOICE_DECODE_H */
