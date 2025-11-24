#ifndef NEON_SYMBOLIC_BITWUZLA_MEMORY_HPP
#define NEON_SYMBOLIC_BITWUZLA_MEMORY_HPP

#include "../symbolic_common_bitwuzla.hpp"
#include "types.hpp"
#include <map>
#include <vector>
#include <cstdint>

// Global storage indexed by memory address for load/store tracking
inline std::map<uintptr_t, std::vector<int32x4_t>> g_neon_memory;
inline std::map<uintptr_t, std::vector<int8x16_t>> g_neon_memory_i8x16;
inline std::map<uintptr_t, std::vector<int8x8_t>> g_neon_memory_i8x8;

#endif // NEON_SYMBOLIC_BITWUZLA_MEMORY_HPP
