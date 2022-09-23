INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_SCANNER scanner)

FIND_PATH(
    SCANNER_INCLUDE_DIRS
    NAMES scanner/api.h
    HINTS $ENV{SCANNER_DIR}/include
        ${PC_SCANNER_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    SCANNER_LIBRARIES
    NAMES gnuradio-scanner
    HINTS $ENV{SCANNER_DIR}/lib
        ${PC_SCANNER_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/scannerTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(SCANNER DEFAULT_MSG SCANNER_LIBRARIES SCANNER_INCLUDE_DIRS)
MARK_AS_ADVANCED(SCANNER_LIBRARIES SCANNER_INCLUDE_DIRS)
