# Copyright 2011,2012 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

########################################################################
# Setup library
########################################################################
include(GrPlatform) #define LIB_SUFFIX

include_directories(${Boost_INCLUDE_DIR})
link_directories(${Boost_LIBRARY_DIRS})
list(APPEND scanner_sources
    fsk4_demodulator_impl.cc
    p25_frame_decoder_impl.cc
)

list(APPEND scanner_sources
    bch.cc
    p25_framer.cc
    p25p1_fdma.cc
    rs.cc
)

set(scanner_sources "${scanner_sources}" PARENT_SCOPE)

add_library(gnuradio-scanner SHARED ${scanner_sources})
if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    find_library(GR_FILTER_LIBRARY libgnuradio-filter.dylib )
else(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    find_library(GR_FILTER_LIBRARY libgnuradio-filter.so )
endif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
set(GR_FILTER_LIBRARIES ${GR_FILTER_LIBRARY})
target_link_libraries(gnuradio-scanner ${Boost_LIBRARIES} gnuradio::gnuradio-runtime ${GR_FILTER_LIBRARIES} imbe_vocoder)
target_include_directories(gnuradio-scanner
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../include>
    PUBLIC $<INSTALL_INTERFACE:include>
)
set_target_properties(gnuradio-scanner PROPERTIES DEFINE_SYMBOL "gnuradio_scanner_EXPORTS")

########################################################################
# Install built library files
########################################################################
install(TARGETS gnuradio-scanner
    LIBRARY DESTINATION lib${LIB_SUFFIX} # .so/.dylib file
    ARCHIVE DESTINATION lib${LIB_SUFFIX} # .lib file
    RUNTIME DESTINATION bin              # .dll file
)

add_subdirectory(imbe_vocoder)
