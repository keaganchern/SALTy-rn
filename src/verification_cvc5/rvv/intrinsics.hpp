#pragma once
// RVV shared infra base (cvc5): type aliases + vsetvl helper used by every
// intrinsic family. Every intrinsic — including the hand-written core — lives in
// ops/*.hpp and includes this. Intrinsic bodies follow op-semantics/rvv-intrinsics.md.

#include "../core/bv_fold.hpp"
#include "../core/context.hpp"
#include "../core/fp_convert.hpp"
#include "../core/symbolic_buffer.hpp"
#include "../core/symbolic_scalar.hpp"
#include "../core/symbolic_vector.hpp"

#include <cmath>
#include <cstring>
#include <cvc5/cvc5.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace salt_cvc5 {

// ===========================================================================
// Type aliases NOT defined in symbolic_vector.hpp (cvc5 tree currently only
// aliases the f16-conv-hwc2chw subset).  All these are RVVVector under the
// hood — adding `using X = RVVVector` here is harmless (and would also be
// harmless if `X` were already aliased elsewhere — same target).
// ===========================================================================
using vint8mf2_t   = RVVVector;
using vint8m1_t    = RVVVector;
using vint8m2_t    = RVVVector;
using vint8m4_t    = RVVVector;
using vint8m8_t    = RVVVector;
using vint16m1_t   = RVVVector;
using vint16m2_t   = RVVVector;
using vint16m4_t   = RVVVector;
using vint16m8_t   = RVVVector;
using vint16mf2_t  = RVVVector;
using vint32m1_t   = RVVVector;
using vint32m4_t   = RVVVector;
using vint32m8_t   = RVVVector;
using vuint8m1_t   = RVVVector;
using vuint8m2_t   = RVVVector;
using vuint8m4_t   = RVVVector;
using vuint8m8_t   = RVVVector;
using vuint8mf2_t  = RVVVector;
using vuint16m2_t  = RVVVector;
using vuint16m4_t  = RVVVector;
using vuint32m1_t  = RVVVector;
using vuint32m4_t  = RVVVector;
using vuint32m8_t  = RVVVector;
using vfloat16m2_t = RVVVector;
using vfloat16m4_t = RVVVector;
using vfloat16m8_t = RVVVector;
using vfloat32m1_t = RVVVector;
using vfloat32m2_t = RVVVector;
using vfloat32m4_t = RVVVector;
using vfloat32m8_t = RVVVector;
using vuint32m1x2_t = VectorTuple<RVVVector, 2>;
using vuint32mf2x2_t = VectorTuple<RVVVector, 2>;
using vuint32m2x2_t = VectorTuple<RVVVector, 2>;
using vuint32m4x2_t = VectorTuple<RVVVector, 2>;
using vuint32m2x3_t = VectorTuple<RVVVector, 3>;
using vuint32m2x4_t = VectorTuple<RVVVector, 4>;
using vfloat32m1x6_t = VectorTuple<RVVVector, 6>;

using vbool4_t  = MaskVector;
using vbool8_t  = MaskVector;
using vbool32_t = MaskVector;

// ===========================================================================
// VSETVL — returns min(avl, vlmax) where vlmax = VLEN/SEW * LMUL.
// Clamps vlmax to ≥1 to defend against pathologically small `vlen` values
// passed by the orchestrator: vsetvl returning 0 silently breaks any inner
// stripmine loop (`while (k > 0) k -= vl * SEW;` becomes infinite).
// ===========================================================================
inline size_t _rvv_vsetvl(size_t avl, size_t sew, size_t lmul) {
    return std::min(avl, std::max((size_t)1, g_ctx->vlen / sew * lmul));
}
} // namespace salt_cvc5
