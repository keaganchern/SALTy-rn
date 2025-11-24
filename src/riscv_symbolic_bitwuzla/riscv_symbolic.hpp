#ifndef RISCV_SYMBOLIC_BITWUZLA_HPP
#define RISCV_SYMBOLIC_BITWUZLA_HPP

/**
 * RISC-V Vector Extension Symbolic Execution Library (Bitwuzla Version)
 *
 * This library provides symbolic execution semantics for RISC-V Vector Extension
 * intrinsics using the Bitwuzla SMT solver.
 *
 * Usage:
 *   #include "riscv_symbolic_bitwuzla/riscv_symbolic.hpp"
 *
 *   Bitwuzla bitwuzla;
 *   g_symbolic_bitwuzla = &bitwuzla;
 *   SymbolicRISCVHelpers::clearMemory();
 *
 *   // Use RVV intrinsics...
 */

#include "types.hpp"
#include "memory.hpp"
#include "intrinsics.hpp"
#include "helpers.hpp"

#endif // RISCV_SYMBOLIC_BITWUZLA_HPP
