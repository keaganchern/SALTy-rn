#ifndef RISCV_SYMBOLIC_BITWUZLA_MEMORY_HPP
#define RISCV_SYMBOLIC_BITWUZLA_MEMORY_HPP

#include "../symbolic_common_bitwuzla.hpp"
#include "types.hpp"
#include <map>
#include <vector>
#include <cstdint>

/**
 * Global VL (vector length) for current operation
 * Set by vsetvl instructions, affects subsequent vector operations
 */
inline size_t g_current_vl = 0;

/**
 * Global storage indexed by memory address for load/store tracking
 * Maps memory addresses to vectors of stored symbolic values
 */
inline std::map<uintptr_t, std::vector<vint32m1_t>> g_riscv_memory;

/**
 * Global storage for int8 vectors (needed for XNN operations)
 */
inline std::map<uintptr_t, std::vector<vint8m1_t>> g_riscv_memory_i8;

#endif // RISCV_SYMBOLIC_BITWUZLA_MEMORY_HPP
