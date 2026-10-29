cmake_minimum_required(VERSION 3.14)
project(salt_verification_cvc5 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# cvc5 distribution, including its C++ headers and libraries.
set(CVC5_INSTALL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/cvc5/install"
    CACHE PATH "cvc5 install root")

# Try the package config first.  If that fails (or the targets don't pull
# in all transitive deps for the static libs), fall back to manual linking.
set(CVC5_CONFIG_DIR "${CVC5_INSTALL_DIR}/lib/cmake/cvc5")
find_package(cvc5 QUIET CONFIG PATHS "${CVC5_CONFIG_DIR}" NO_DEFAULT_PATH)

add_library(salt_cvc5_headers INTERFACE)
target_include_directories(salt_cvc5_headers INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CVC5_INSTALL_DIR}/include)

# The macOS release exports its actual dependencies through cvc5::cvc5.
# Its linker does not accept the GNU archive-group flags used on Linux.
target_link_directories(salt_cvc5_headers INTERFACE ${CVC5_INSTALL_DIR}/lib)
if(APPLE)
    if(NOT TARGET cvc5::cvc5)
        message(FATAL_ERROR "cvc5 C++ distribution not found. Set CVC5_INSTALL_DIR to its extracted root.")
    endif()
    target_link_libraries(salt_cvc5_headers INTERFACE cvc5::cvc5)
else()
# The Linux build needs the bundled static dependencies grouped explicitly.
target_link_libraries(salt_cvc5_headers INTERFACE
    -Wl,--start-group
    cvc5
    cadical
    cln
    picpolyxx
    picpoly
    glpk
    cocoa
    gmpxx
    gmp
    -Wl,--end-group
    pthread
    dl
    m)
endif()

target_compile_options(salt_cvc5_headers INTERFACE
    -Wno-unused-parameter
    -Wno-unused-variable
    -Wno-unused-but-set-variable
    -Wno-unused-private-field
    -Wno-format
    -Wno-sign-compare
    -fno-operator-names
    -fpermissive   # XNNPACK kernels are C: allow implicit void*->T* (e.g. qd8 `const void* w` + vld1q_s32(w))
)

# This legacy hand-written harness is optional in current checkouts. It must
# not prevent generated NEON/RVV or RVV/RVV targets from configuring.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/harness/verify_f16_conv_hwc2chw_cvc5.cpp")
    add_executable(verify_f16_conv_hwc2chw_cvc5
        harness/verify_f16_conv_hwc2chw_cvc5.cpp)
    target_link_libraries(verify_f16_conv_hwc2chw_cvc5 PRIVATE salt_cvc5_headers)
endif()

# Build a verification harness from a source file (mirror of bitwuzla
# CMakeLists' HARNESS_SRC mode — used by the orchestrator).
# Usage: cmake --build . --target verify_<name> -- HARNESS_SRC=path/to/harness.cpp
if(HARNESS_SRC)
    get_filename_component(HARNESS_NAME ${HARNESS_SRC} NAME_WE)
    add_executable(${HARNESS_NAME} ${HARNESS_SRC})
    target_link_libraries(${HARNESS_NAME} PRIVATE salt_cvc5_headers)
endif()
