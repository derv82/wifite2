cmake_minimum_required(VERSION 3.1.0 FATAL_ERROR)
set(CMAKE_CXX_STANDARD 11)

# FIXME: Search for this path instead of hardcoding it
include_directories(/usr/include/libnl3)

add_library(util osal_wi.cpp osal_nl.cpp util.cpp MacAddr.cpp crc.cpp eapol.cpp crypto.cpp pcap.cpp)
target_link_libraries(util nl-3 nl-genl-3 ssl crypto)


project(reactivejam)
add_executable(reactivejam reactivejam.cpp)
target_link_libraries(reactivejam util)

project(channelmitm)
add_executable(channelmitm channelmitm.cpp ClientInfo.cpp SeqnumType.cpp SeqnumStats.cpp chopstate.cpp)
target_link_libraries(channelmitm util)

project(constantjam)
add_executable(constantjam constantjam.cpp)
target_link_libraries(constantjam util)

project(fastreply)
add_executable(fastreply fastreply.cpp)
target_link_libraries(fastreply util)
