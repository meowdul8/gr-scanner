/* -*- c++ -*- */

#define SCANNER_API

%include "gnuradio.i"           // the common stuff

//load generated python docstrings
%include "scanner_swig_doc.i"

%{
#include "scanner/fsk4_demodulator.h"
#include "scanner/p25_frame_decoder.h"
%}

%include "scanner/fsk4_demodulator.h"
%include "scanner/p25_frame_decoder.h"
GR_SWIG_BLOCK_MAGIC2(scanner, fsk4_demodulator);
GR_SWIG_BLOCK_MAGIC2(scanner, p25_frame_decoder);

