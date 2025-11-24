#ifndef NEON_SYMBOLIC_BITWUZLA_HPP
#define NEON_SYMBOLIC_BITWUZLA_HPP

/**
 * ARM NEON Symbolic Execution Library (Bitwuzla Version)
 *
 * This library provides symbolic execution semantics for ARM NEON intrinsics
 * using the Bitwuzla SMT solver.
 *
 * Usage:
 *   #include "neon_symbolic_bitwuzla/neon_symbolic.hpp"
 *
 *   Bitwuzla bitwuzla;
 *   g_symbolic_bitwuzla = &bitwuzla;
 *   SymbolicNEONHelpers::clearMemory();
 *
 *   // Use NEON intrinsics...
 */

#include "types.hpp"
#include "memory.hpp"
#include "intrinsics.hpp"
#include "utils.hpp"

#endif // NEON_SYMBOLIC_BITWUZLA_HPP
