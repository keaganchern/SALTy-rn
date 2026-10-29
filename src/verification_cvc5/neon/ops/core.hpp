#pragma once
// Hand-written core NEON intrinsics — foundational set, NOT generated.
// Relocated verbatim from intrinsics.hpp (now the shared infra base).
#include "../intrinsics.hpp"
namespace salt_cvc5 {


// ===========================================================================
// VDUP / VMOV — broadcast scalar to all lanes
// ===========================================================================
inline uint16x4_t vdup_n_u16(uint16_t v) {
    auto& tm = g_ctx->tm;
    Term val = mk_bv_val(tm, 16, v);
    std::array<Term, 4> l; l.fill(val);
    return uint16x4_t(tm, l);
}
inline uint16x4_t vmov_n_u16(uint16_t v) { return vdup_n_u16(v); }

// ===========================================================================
// VLD1 — full vector load
// ===========================================================================
inline uint16x4_t vld1_u16(const uint16_t* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<16, 4>(b.ptrToByteOffset(p));
}

// VLD1 lane: load one scalar, insert into existing vector at lane
inline uint16x4_t vld1_lane_u16(const uint16_t* p, const uint16x4_t& v, int lane) {
    auto r = v;
    auto& b = g_ctx->findBuffer(p);
    r.setLane(lane, b.loadScalar(b.ptrToByteOffset(p), 16));
    return r;
}

// ===========================================================================
// VST1 lane — store one lane of a vector to memory
// ===========================================================================
inline void vst1_lane_u16(void* ptr, const uint16x4_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 16);
}

inline void vst1_lane_u32(void* ptr, const uint32x2_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 32);
}

// vld1_dup_* / vst1_lane_u64 — element-broadcast loads + scalar stores used by
// the x8/x16/x64-transposec siblings.  vld1_dup_<W> loads ONE element from p
// and broadcasts to every lane of the resulting vector.
inline uint8x8_t vld1_dup_u8(const uint8_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 8);
    std::array<Term, 8> lanes; lanes.fill(v);
    return uint8x8_t(tm, lanes);
}
inline int8x8_t vld1_dup_s8(const int8_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 8);
    std::array<Term, 8> lanes; lanes.fill(v);
    return int8x8_t(tm, lanes);
}
// s32x2 lane add + store + low-half + i8→i16 widen — used by qs8-rsum.
inline int32x2_t vadd_s32(const int32x2_t& a, const int32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), b.getLane(i)});
    return int32x2_t(tm, lanes);
}
inline int32x2_t vmul_s32(const int32x2_t& a, const int32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_MULT, {a.getLane(i), b.getLane(i)});
    return int32x2_t(tm, lanes);
}
inline int32x2_t vget_low_s32(const int32x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes = {a.getLane(0), a.getLane(1)};
    return int32x2_t(tm, lanes);
}
inline void vst1_lane_s32(int32_t* p, const int32x2_t& v, int lane) {
    auto& b = g_ctx->findBuffer(p);
    b.storeScalar(b.ptrToByteOffset(p), v.getLane(lane), 32);
}
// vmovl_s8: widen i8x8 → i16x8 via sign-extension.
inline int16x8_t vmovl_s8(const int8x8_t& a) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(sext, {a.getLane(i)});
    return int16x8_t(tm, lanes);
}
// Unsigned variants — used by qu8-rsum.
inline uint16x8_t vmovl_u8(const uint8x8_t& a) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(zext, {a.getLane(i)});
    return uint16x8_t(tm, lanes);
}
inline uint32x4_t vmovl_u16(const uint16x4_t& a) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {16});
    std::array<Term, 4> lanes;
    for (size_t i = 0; i < 4; i++)
        lanes[i] = tm.mkTerm(zext, {a.getLane(i)});
    return uint32x4_t(tm, lanes);
}
inline uint16x4_t vget_low_u16(const uint16x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes = {a.getLane(0), a.getLane(1), a.getLane(2), a.getLane(3)};
    return uint16x4_t(tm, lanes);
}
inline uint32x2_t vget_low_u32(const uint32x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes = {a.getLane(0), a.getLane(1)};
    return uint32x2_t(tm, lanes);
}
inline uint32x2_t vget_high_u32(const uint32x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes = {a.getLane(2), a.getLane(3)};
    return uint32x2_t(tm, lanes);
}
inline uint32x2_t vadd_u32(const uint32x2_t& a, const uint32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), b.getLane(i)});
    return uint32x2_t(tm, lanes);
}
inline uint32x2_t vld1_dup_u32(const uint32_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 32);
    std::array<Term, 2> lanes = {v, v};
    return uint32x2_t(tm, lanes);
}
inline int16x4_t vld1_dup_s16(const int16_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 16);
    std::array<Term, 4> lanes; lanes.fill(v);
    return int16x4_t(tm, lanes);
}
// s16 element-wise ops — used by s8-ibilinear.
inline int16x8_t vsubq_s16(const int16x8_t& a, const int16x8_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SUB, {a.getLane(i), b.getLane(i)});
    return int16x8_t(tm, lanes);
}
inline int16x8_t vmulq_s16(const int16x8_t& a, const int16x8_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_MULT, {a.getLane(i), b.getLane(i)});
    return int16x8_t(tm, lanes);
}
// vmovn_s16: narrow i16x8 → i8x8 via low-byte extract.
inline int8x8_t vmovn_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm;
    Op extr = tm.mkOp(Kind::BITVECTOR_EXTRACT, {7u, 0u});
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(extr, {a.getLane(i)});
    return int8x8_t(tm, lanes);
}
inline uint8x8_t vmovn_u16(const uint16x8_t& a) {
    auto& tm = g_ctx->tm;
    Op extr = tm.mkOp(Kind::BITVECTOR_EXTRACT, {7u, 0u});
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++)
        lanes[i] = tm.mkTerm(extr, {a.getLane(i)});
    return uint8x8_t(tm, lanes);
}
inline int16x8_t  vreinterpretq_s16_u16(const uint16x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return int16x8_t(tm, lanes);
}
inline uint16x8_t vreinterpretq_u16_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return uint16x8_t(tm, lanes);
}
inline uint16x4_t vld1_dup_u16(const uint16_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 16);
    std::array<Term, 4> lanes; lanes.fill(v);
    return uint16x4_t(tm, lanes);
}
inline uint64x1_t vld1_dup_u64(const uint64_t* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 64);
    std::array<Term, 1> lanes = {v};
    return uint64x1_t(tm, lanes);
}
inline void vst1_lane_u64(uint64_t* ptr, const uint64x1_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 64);
}

// uint32x2 load/store/broadcast/zip — used by x32-transposec NEON 2x2 tile.
inline uint32x2_t vld1_u32(const uint32_t* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<32, 2>(b.ptrToByteOffset(p));
}
inline void vst1_u32(uint32_t* p, const uint32x2_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<32, 2>(b.ptrToByteOffset(p), v);
}
inline uint32x2_t vmov_n_u32(uint32_t v) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)v);
    std::array<Term, 2> lanes = {bv, bv};
    return uint32x2_t(tm, lanes);
}
// vzip_u32: interleave two 2-lane vectors → tuple of 2 vectors.
//   r.val[0] = {a[0], b[0]}; r.val[1] = {a[1], b[1]}.
inline VectorTuple<uint32x2_t, 2> vzip_u32(const uint32x2_t& a, const uint32x2_t& b) {
    auto& tm = g_ctx->tm;
    VectorTuple<uint32x2_t, 2> r;
    std::array<Term, 2> l0 = {a.getLane(0), b.getLane(0)};
    std::array<Term, 2> l1 = {a.getLane(1), b.getLane(1)};
    r.val[0] = uint32x2_t(tm, l0);
    r.val[1] = uint32x2_t(tm, l1);
    return r;
}

// ===========================================================================
// REINTERPRET — same width, different element-type view (no-op on lanes)
// ===========================================================================
inline float16x4_t vreinterpret_f16_u16(const uint16x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return float16x4_t(tm, lanes);
}

inline uint16x4_t vreinterpret_u16_f16(const float16x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return uint16x4_t(tm, lanes);
}

// 4×16 → 2×32: pack pairs of 16-bit lanes into 32-bit (little-endian).
inline uint32x2_t vreinterpret_u32_f16(const float16x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (int i = 0; i < 2; i++) {
        // little-endian: lo lane goes in low half
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_CONCAT,
                             {a.getLane(i*2 + 1), a.getLane(i*2)});
    }
    return uint32x2_t(tm, lanes);
}

// ===========================================================================
// FP16 FMA by lane: result[i] = a[i] + b[i] * v[lane]
// (A64 FMLA Vd.4H,Vn.4H,Vm.H[lane]; fused, single rounding)
// ===========================================================================
inline float16x4_t vfma_lane_f16(const float16x4_t& a, const float16x4_t& b,
                                  const float16x4_t& v, int lane) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    Term v_fp = load_as_fp16(tm, v.getLane(lane));
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term a_fp = load_as_fp16(tm, a.getLane(i));
        Term b_fp = load_as_fp16(tm, b.getLane(i));
        Term result_fp = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, b_fp, v_fp, a_fp});
        lanes[i] = store_fp16_as_bv(tm, result_fp);
    }
    return float16x4_t(tm, lanes);
}

// ===========================================================================
// FP16 MIN / MAX (use FP_MIN/FP_MAX — matches RVV semantics)
// ===========================================================================
template <size_t NumLanes>
inline NeonVector<16, NumLanes> neon_vmin_f16_maxnum(
    const NeonVector<16, NumLanes>& a, const NeonVector<16, NumLanes>& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, NumLanes> lanes;
    for (size_t i = 0; i < NumLanes; i++) {
        Term a_fp = load_as_fp16(tm, a.getLane(i));
        Term b_fp = load_as_fp16(tm, b.getLane(i));
        lanes[i] = store_fp16_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MIN, {a_fp, b_fp}));
    }
    return NeonVector<16, NumLanes>(tm, lanes);
}

template <size_t NumLanes>
inline NeonVector<16, NumLanes> neon_vmax_f16_maxnum(
    const NeonVector<16, NumLanes>& a, const NeonVector<16, NumLanes>& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, NumLanes> lanes;
    for (size_t i = 0; i < NumLanes; i++) {
        Term a_fp = load_as_fp16(tm, a.getLane(i));
        Term b_fp = load_as_fp16(tm, b.getLane(i));
        lanes[i] = store_fp16_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MAX, {a_fp, b_fp}));
    }
    return NeonVector<16, NumLanes>(tm, lanes);
}

inline float16x4_t vmin_f16(const float16x4_t& a, const float16x4_t& b) { return neon_vmin_f16_maxnum(a, b); }
inline float16x4_t vmax_f16(const float16x4_t& a, const float16x4_t& b) { return neon_vmax_f16_maxnum(a, b); }

// ===========================================================================
// vzip_f16 — interleave (ZIP1/ZIP2)
// val[0] = { a[0], b[0], a[1], b[1] }
// val[1] = { a[2], b[2], a[3], b[3] }
// ===========================================================================
struct float16x4x2_t {
    float16x4_t val[2];
    float16x4x2_t(const float16x4_t& v0, const float16x4_t& v1) : val{v0, v1} {}
};

inline float16x4x2_t vzip_f16(const float16x4_t& a, const float16x4_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lo, hi;
    for (int i = 0; i < 2; i++) {
        lo[2*i]     = a.getLane(i);
        lo[2*i + 1] = b.getLane(i);
        hi[2*i]     = a.getLane(i + 2);
        hi[2*i + 1] = b.getLane(i + 2);
    }
    return float16x4x2_t(float16x4_t(tm, lo), float16x4_t(tm, hi));
}

// ===========================================================================
// PHASE 2 ADDITIONS — full NEON surface for kernels/source/ counterparts of
// kernels/target/.
// ===========================================================================

// ---------------------------------------------------------------------------
// FP32 helpers (BV32 ↔ FP32 round-trip via fresh symbolic constant + asserted
// equality, since cvc5 has no fp.to_ieee_bv).
// ---------------------------------------------------------------------------
inline Term load_as_fp32(TermManager& tm, Term bv32) {
    auto it = g_fp_bv_cache.find(bv32.getId());   // memoized store→load: skip the FP↔BV round-trip
    if (it != g_fp_bv_cache.end()) return it->second;
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
    return tm.mkTerm(op, {bv32});
}
inline size_t& fp32_bv_counter() {
    static size_t counter = 0;
    return counter;
}
inline Term store_fp32_as_bv(TermManager& tm, Term fp_val) {
    Sort bv32 = tm.mkBitVectorSort(32);
    Term bv = tm.mkConst(bv32, "_neon_fp32_2bv_" + std::to_string(fp32_bv_counter()++));
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
    Term fp_from_bv = tm.mkTerm(op, {bv});
    g_ctx->solver->assertFormula(tm.mkTerm(Kind::EQUAL, {fp_from_bv, fp_val}));
    g_fp_bv_cache[bv.getId()] = fp_val;   // so load_as_fp32(bv) returns fp_val directly
    return bv;
}
inline Term mk_fp32_from_float(TermManager& tm, float v) {
    uint32_t bits;
    std::memcpy(&bits, &v, sizeof(bits));
    // Scalar-ref sentinel: high 11 bits == 0x7FE => qNaN with marker bit 21 set.
    // Payload = (buffer_id : 5 bits)(offset_in_lanes : 16 bits).  See
    // SymbolicBuffer::bindScalarRef.  Redirect the constant Term to the
    // symbolic Term stored in the buffer at the recorded lane offset.
    if ((bits & 0xFFE00000u) == 0x7FE00000u) {
        uint8_t buf_id = static_cast<uint8_t>((bits >> 16) & 0x1Fu);
        uint32_t lane = bits & 0xFFFFu;
        if (g_ctx && buf_id != 0) {
            if (auto* buf = g_ctx->findBufferById(buf_id)) {
                Term bv = buf->loadScalar(lane * 4, 32);
                Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
                return tm.mkTerm(op, {bv});
            }
        }
    }
    Term bv = tm.mkBitVector(32, static_cast<uint64_t>(bits));
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
    return tm.mkTerm(op, {bv});
}

// ---------------------------------------------------------------------------
// signed_saturate — narrowing helper used by VQ* intrinsics
// ---------------------------------------------------------------------------
inline Term signed_saturate(TermManager& tm, Term wide_val, size_t wide_bits, size_t narrow_bits) {
    int64_t max_val = (1LL << (narrow_bits - 1)) - 1;
    int64_t min_val = -(1LL << (narrow_bits - 1));
    Term t_max = mk_bv_val(tm, wide_bits, max_val);
    Term t_min = mk_bv_val(tm, wide_bits, min_val);
    Term gt_max = tm.mkTerm(Kind::BITVECTOR_SGT, {wide_val, t_max});
    Term lt_min = tm.mkTerm(Kind::BITVECTOR_SLT, {wide_val, t_min});
    Term clamped = tm.mkTerm(Kind::ITE, {gt_max, t_max,
        tm.mkTerm(Kind::ITE, {lt_min, t_min, wide_val})});
    Op extract_op = tm.mkOp(Kind::BITVECTOR_EXTRACT,
        {static_cast<uint32_t>(narrow_bits - 1), 0u});
    return tm.mkTerm(extract_op, {clamped});
}

// ---------------------------------------------------------------------------
// VDUP / VMOV broadcast — common templates for all integer types
// ---------------------------------------------------------------------------
template <size_t Bits, size_t Lanes>
inline NeonVector<Bits, Lanes> neon_vdup_impl_int(int64_t value) {
    auto& tm = g_ctx->tm;
    Term v = mk_bv_val(tm, Bits, value);
    std::array<Term, Lanes> lanes; lanes.fill(v);
    return NeonVector<Bits, Lanes>(tm, lanes);
}
inline int8x8_t   vdup_n_s8(int8_t v)    { return neon_vdup_impl_int<8, 8>(v); }
inline int8x16_t  vdupq_n_s8(int8_t v)   { return neon_vdup_impl_int<8, 16>(v); }
inline int16x4_t  vdup_n_s16(int16_t v)  { return neon_vdup_impl_int<16, 4>(v); }
inline int16x8_t  vdupq_n_s16(int16_t v) { return neon_vdup_impl_int<16, 8>(v); }
inline int32x2_t  vdup_n_s32(int32_t v)  { return neon_vdup_impl_int<32, 2>(v); }
inline int32x4_t  vdupq_n_s32(int32_t v) { return neon_vdup_impl_int<32, 4>(v); }
inline uint8x8_t  vdup_n_u8(uint8_t v)   { return neon_vdup_impl_int<8, 8>(v); }
inline uint8x16_t vdupq_n_u8(uint8_t v)  { return neon_vdup_impl_int<8, 16>(v); }
inline uint16x8_t vdupq_n_u16(uint16_t v){ return neon_vdup_impl_int<16, 8>(v); }
inline uint32x4_t vdupq_n_u32(uint32_t v){ return neon_vdup_impl_int<32, 4>(v); }
inline int16x8_t  vmovq_n_s16(int16_t v) { return vdupq_n_s16(v); }
inline int32x4_t  vmovq_n_s32(int32_t v) { return vdupq_n_s32(v); }

inline float32x4_t vdupq_n_f32(float v) {
    auto& tm = g_ctx->tm;
    Term bv = store_fp32_as_bv(tm, mk_fp32_from_float(tm, v));
    std::array<Term, 4> lanes; lanes.fill(bv);
    return float32x4_t(tm, lanes);
}
inline float32x4_t vmovq_n_f32(float v) { return vdupq_n_f32(v); }
// vdupq_lane_f32: broadcast lane `lane` of a 2-lane vector to all 4 lanes.
inline float32x4_t vdupq_lane_f32(const float32x2_t& v, int lane) {
    auto& tm = g_ctx->tm;
    Term bv = v.getLane(lane);
    std::array<Term, 4> lanes; lanes.fill(bv);
    return float32x4_t(tm, lanes);
}
// vdupq_laneq_f32: broadcast lane `lane` of a 4-lane vector to all 4 lanes.
inline float32x4_t vdupq_laneq_f32(const float32x4_t& v, int lane) {
    auto& tm = g_ctx->tm;
    Term bv = v.getLane(lane);
    std::array<Term, 4> lanes; lanes.fill(bv);
    return float32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VLD1 / VST1 — full vector loads/stores
// ---------------------------------------------------------------------------
inline int8x8_t   vld1_s8 (const int8_t*  p)  { auto& b = g_ctx->findBuffer(p); return b.loadNeon<8, 8>(b.ptrToByteOffset(p)); }
inline int8x16_t  vld1q_s8(const int8_t*  p)  { auto& b = g_ctx->findBuffer(p); return b.loadNeon<8, 16>(b.ptrToByteOffset(p)); }
inline uint16x8_t vld1q_u16(const uint16_t* p){ auto& b = g_ctx->findBuffer(p); return b.loadNeon<16, 8>(b.ptrToByteOffset(p)); }
inline float32x4_t vld1q_f32(const float* p)  { auto& b = g_ctx->findBuffer(p); return b.loadNeon<32, 4>(b.ptrToByteOffset(p)); }
inline uint32x4_t vld1q_u32(const uint32_t* p){
    // Fallback for static-const rodata LUTs (e.g. dwconv2d-chw mask_table)
    // not registered as SymbolicBuffer — read concrete u32 lanes verbatim.
    if (auto* b = g_ctx->findBufferSafe(p)) return b->loadNeon<32, 4>(b->ptrToByteOffset(p));
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = tm.mkBitVector(32, (uint64_t)p[i]);
    return uint32x4_t(tm, lanes);
}

inline void vst1_s8 (int8_t* p,  const int8x8_t&  v) { auto& b = g_ctx->findBuffer(p); b.storeNeon<8, 8>(b.ptrToByteOffset(p), v); }
inline void vst1q_s8(int8_t* p,  const int8x16_t& v) { auto& b = g_ctx->findBuffer(p); b.storeNeon<8, 16>(b.ptrToByteOffset(p), v); }
inline void vst1_u16(uint16_t* p,const uint16x4_t& v){ auto& b = g_ctx->findBuffer(p); b.storeNeon<16, 4>(b.ptrToByteOffset(p), v); }
inline void vst1q_u16(uint16_t* p,const uint16x8_t& v){auto& b = g_ctx->findBuffer(p); b.storeNeon<16, 8>(b.ptrToByteOffset(p), v); }
inline void vst1q_f32(float* p,  const float32x4_t& v){auto& b = g_ctx->findBuffer(p); b.storeNeon<32, 4>(b.ptrToByteOffset(p), v); }
inline void vst1q_u32(uint32_t* p, const uint32x4_t& v){auto& b = g_ctx->findBuffer(p); b.storeNeon<32, 4>(b.ptrToByteOffset(p), v); }
inline void vst1_f32 (float* p,  const float32x2_t& v){auto& b = g_ctx->findBuffer(p); b.storeNeon<32, 2>(b.ptrToByteOffset(p), v); }
inline void vst1_lane_f32(float* ptr, const float32x2_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 32);
}
inline void vst1q_lane_f32(float* ptr, const float32x4_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 32);
}
inline float32x4_t vld1q_lane_f32(const float* ptr, const float32x4_t& src, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    Term loaded = buf.loadScalar(buf.ptrToByteOffset(ptr), 32);
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = (i == lane) ? loaded : src.getLane(i);
    return float32x4_t(g_ctx->tm, lanes);
}
// vfmaq_laneq_f32: r[i] = a[i] + b[i] * c[lane]  (single FMA rounding)
inline float32x4_t vfmaq_laneq_f32(const float32x4_t& a, const float32x4_t& b, const float32x4_t& c, int lane) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term cf_lane = load_as_fp32(tm, c.getLane(lane));
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, bf, cf_lane, af});
        lanes[i] = store_fp32_as_bv(tm, res);
    }
    return float32x4_t(tm, lanes);
}
// vfmaq_lane_f32: r[i] = a[i] + b[i] * c[lane]  with c as 2-lane vector
inline float32x4_t vfmaq_lane_f32(const float32x4_t& a, const float32x4_t& b, const float32x2_t& c, int lane) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term cf_lane = load_as_fp32(tm, c.getLane(lane));
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, bf, cf_lane, af});
        lanes[i] = store_fp32_as_bv(tm, res);
    }
    return float32x4_t(tm, lanes);
}
// vextq_f32: concatenate {a,b} and extract 4 lanes starting at `n`.
inline float32x4_t vextq_f32(const float32x4_t& a, const float32x4_t& b, int n) {
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        int idx = n + i;
        lanes[i] = (idx < 4) ? a.getLane(idx) : b.getLane(idx - 4);
    }
    return float32x4_t(g_ctx->tm, lanes);
}
// vreinterpretq_u32_f32 / vreinterpretq_f32_u32: bitcast between fp32 and u32 lanes.
// Lanes hold raw 32-bit BV Terms either way, so this is identity at the Term level.
inline uint32x4_t vreinterpretq_u32_f32(const float32x4_t& v) {
    std::array<Term, 4> lanes = {v.getLane(0), v.getLane(1), v.getLane(2), v.getLane(3)};
    return uint32x4_t(g_ctx->tm, lanes);
}
inline float32x4_t vreinterpretq_f32_u32(const uint32x4_t& v) {
    std::array<Term, 4> lanes = {v.getLane(0), v.getLane(1), v.getLane(2), v.getLane(3)};
    return float32x4_t(g_ctx->tm, lanes);
}
// vzip1q_f32: result = {a[0], b[0], a[1], b[1]}
inline float32x4_t vzip1q_f32(const float32x4_t& a, const float32x4_t& b) {
    std::array<Term, 4> lanes = {a.getLane(0), b.getLane(0), a.getLane(1), b.getLane(1)};
    return float32x4_t(g_ctx->tm, lanes);
}
// vzip2q_f32: result = {a[2], b[2], a[3], b[3]}
inline float32x4_t vzip2q_f32(const float32x4_t& a, const float32x4_t& b) {
    std::array<Term, 4> lanes = {a.getLane(2), b.getLane(2), a.getLane(3), b.getLane(3)};
    return float32x4_t(g_ctx->tm, lanes);
}

// vld1 / vld1_dup / vget_lane / vpadd / vadd for float32x2_t (used by f32-rsum tail).
inline float32x2_t vld1_f32(const float* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<32, 2>(b.ptrToByteOffset(p));
}
inline float32x2_t vld1_dup_f32(const float* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 32);
    std::array<Term, 2> lanes = {v, v};
    return float32x2_t(tm, lanes);
}
inline float32x4_t vld1q_dup_f32(const float* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 32);
    std::array<Term, 4> lanes = {v, v, v, v};
    return float32x4_t(tm, lanes);
}
// Concrete value unused in symbolic mode — the caller's `vresult = vget_lane_f32(...)`
// flows into a downstream symbolic op via a 32-bit BV term recovered from the lane.
// Here we return 0.0f because the SymbolicScalar<float> side channel records the
// term in g_scalar_terms keyed by `&out`.  For f32-rsum the kernel does
// `*output += vresult * vscale` — the float multiplication routes through the
// salt symbolic-scalar overload, picking up the symbolic Term.
inline float vget_lane_f32(const float32x2_t& a, int lane) { (void)a; (void)lane; return 0.0f; }
inline float32x2_t vpadd_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 2> lanes;
    Term a0 = load_as_fp32(tm, a.getLane(0));
    Term a1 = load_as_fp32(tm, a.getLane(1));
    Term b0 = load_as_fp32(tm, b.getLane(0));
    Term b1 = load_as_fp32(tm, b.getLane(1));
    lanes[0] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, a0, a1}));
    lanes[1] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, b0, b1}));
    return float32x2_t(tm, lanes);
}
// vadd / vmul for float32x2_t — inline per lane (fp32_binop template is
// declared later in this file, so we can't delegate from here).
inline float32x2_t vadd_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        lanes[i] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf}));
    }
    return float32x2_t(tm, lanes);
}
inline float32x2_t vmul_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        lanes[i] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MULT, {rm, af, bf}));
    }
    return float32x2_t(tm, lanes);
}
// Pairwise FP min/max for float32x2:
//   r[0] = min(a[0], a[1]);  r[1] = min(b[0], b[1]).
inline float32x2_t vpmin_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    Term a0 = load_as_fp32(tm, a.getLane(0));
    Term a1 = load_as_fp32(tm, a.getLane(1));
    Term b0 = load_as_fp32(tm, b.getLane(0));
    Term b1 = load_as_fp32(tm, b.getLane(1));
    lanes[0] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MIN, {a0, a1}));
    lanes[1] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MIN, {b0, b1}));
    return float32x2_t(tm, lanes);
}
inline float32x2_t vpmax_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    Term a0 = load_as_fp32(tm, a.getLane(0));
    Term a1 = load_as_fp32(tm, a.getLane(1));
    Term b0 = load_as_fp32(tm, b.getLane(0));
    Term b1 = load_as_fp32(tm, b.getLane(1));
    lanes[0] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MAX, {a0, a1}));
    lanes[1] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MAX, {b0, b1}));
    return float32x2_t(tm, lanes);
}

// vmax / vmin for float32x2 — FP comparison-based (no rounding mode).
inline float32x2_t vmax_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        lanes[i] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MAX, {af, bf}));
    }
    return float32x2_t(tm, lanes);
}
inline float32x2_t vmin_f32(const float32x2_t& a, const float32x2_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (size_t i = 0; i < 2; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        lanes[i] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MIN, {af, bf}));
    }
    return float32x2_t(tm, lanes);
}
inline void vst1_lane_s8(int8_t* ptr, const int8x8_t& val, int lane) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeScalar(buf.ptrToByteOffset(ptr), val.getLane(lane), 8);
}

// ld1 lane / dup variants
template<size_t Bits, size_t Lanes>
inline NeonVector<Bits, Lanes> neon_vld1q_dup(const void* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term sc = b.loadScalar(b.ptrToByteOffset(p), Bits);
    std::array<Term, Lanes> lanes; lanes.fill(sc);
    return NeonVector<Bits, Lanes>(tm, lanes);
}
inline uint16x8_t vld1q_dup_u16(const uint16_t* p) { return neon_vld1q_dup<16, 8>(p); }
inline int32x2_t vld1_dup_s32(const int32_t* p)    { return neon_vld1q_dup<32, 2>(p); }
inline int32x2_t vld1_lane_s32(const int32_t* p, const int32x2_t& v, int lane) {
    auto r = v;
    auto& b = g_ctx->findBuffer(p);
    r.setLane(lane, b.loadScalar(b.ptrToByteOffset(p), 32));
    return r;
}

// ---------------------------------------------------------------------------
// Generic integer ADD / SUB / MUL — element-wise (templates)
// ---------------------------------------------------------------------------
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vadd_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), b.getLane(i)});
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vsub_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SUB, {a.getLane(i), b.getLane(i)});
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vmul_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_MULT, {a.getLane(i), b.getLane(i)});
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vand_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_AND, {a.getLane(i), b.getLane(i)});
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vbic_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term not_b = tm.mkTerm(Kind::BITVECTOR_NOT, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_AND, {a.getLane(i), not_b});
    }
    return NeonVector<B,N>(tm, lanes);
}

inline int16x8_t  vaddq_s16(const int16x8_t& a, const int16x8_t& b)  { return neon_vadd_impl(a,b); }
inline int32x4_t  vaddq_s32(const int32x4_t& a, const int32x4_t& b)  { return neon_vadd_impl(a,b); }
inline uint16x4_t vadd_u16 (const uint16x4_t& a, const uint16x4_t& b){ return neon_vadd_impl(a,b); }
inline uint16x8_t vaddq_u16(const uint16x8_t& a, const uint16x8_t& b){ return neon_vadd_impl(a,b); }
inline uint32x4_t vaddq_u32(const uint32x4_t& a, const uint32x4_t& b){ return neon_vadd_impl(a,b); }
inline int32x4_t  vandq_s32(const int32x4_t& a, const int32x4_t& b)  { return neon_vand_impl(a,b); }
inline uint16x4_t vand_u16 (const uint16x4_t& a, const uint16x4_t& b){ return neon_vand_impl(a,b); }
inline uint16x8_t vandq_u16(const uint16x8_t& a, const uint16x8_t& b){ return neon_vand_impl(a,b); }
inline uint32x4_t vandq_u32(const uint32x4_t& a, const uint32x4_t& b){ return neon_vand_impl(a,b); }
inline uint8x8_t  vand_u8  (const uint8x8_t&  a, const uint8x8_t&  b){ return neon_vand_impl(a,b); }
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vshl_n_impl(const NeonVector<B,N>& a, uint32_t n) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    Term shift = mk_bv_val(tm, B, n);
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SHL, {a.getLane(i), shift});
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vshr_n_signed_impl(const NeonVector<B,N>& a, uint32_t n) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    Term shift = mk_bv_val(tm, B, n);
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ASHR, {a.getLane(i), shift});
    return NeonVector<B,N>(tm, lanes);
}
inline uint8x8_t vshl_n_u8(const uint8x8_t& a, uint32_t n) { return neon_vshl_n_impl(a, n); }
inline int8x8_t  vshr_n_s8(const int8x8_t& a, uint32_t n)  { return neon_vshr_n_signed_impl(a, n); }
// Same-bitwidth reinterprets — types differ but BV layout is identical.
inline int8x8_t  vreinterpret_s8_u8(const uint8x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return int8x8_t(tm, lanes);
}
inline uint8x8_t vreinterpret_u8_s8(const int8x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return uint8x8_t(tm, lanes);
}
inline uint16x8_t vbicq_u16(const uint16x8_t& a, const uint16x8_t& b){ return neon_vbic_impl(a,b); }
inline uint32x4_t vbicq_u32(const uint32x4_t& a, const uint32x4_t& b){ return neon_vbic_impl(a,b); }

// ---------------------------------------------------------------------------
// VBSL — bitwise select: (mask & a) | (~mask & b)
// ---------------------------------------------------------------------------
template <size_t B, size_t N, typename M>
inline NeonVector<B,N> neon_vbsl_impl(const M& mask, const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term m = mask.getLane(i);
        Term not_m = tm.mkTerm(Kind::BITVECTOR_NOT, {m});
        Term sel_a = tm.mkTerm(Kind::BITVECTOR_AND, {m, a.getLane(i)});
        Term sel_b = tm.mkTerm(Kind::BITVECTOR_AND, {not_m, b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_OR, {sel_a, sel_b});
    }
    return NeonVector<B,N>(tm, lanes);
}
inline uint16x4_t vbsl_u16(const uint16x4_t& m, const uint16x4_t& a, const uint16x4_t& b)  { return neon_vbsl_impl(m,a,b); }
inline uint16x8_t vbslq_u16(const uint16x8_t& m, const uint16x8_t& a, const uint16x8_t& b) { return neon_vbsl_impl(m,a,b); }
inline uint32x4_t vbslq_u32(const uint32x4_t& m, const uint32x4_t& a, const uint32x4_t& b) { return neon_vbsl_impl(m,a,b); }
inline int16x8_t  vbslq_s16(const uint16x8_t& m, const int16x8_t& a, const int16x8_t& b)   { return neon_vbsl_impl<16,8,uint16x8_t>(m,a,b); }
inline float32x4_t vbslq_f32(const uint32x4_t& m, const float32x4_t& a, const float32x4_t& b) { return neon_vbsl_impl<32,4,uint32x4_t>(m,a,b); }
inline float16x4_t vbsl_f16(const uint16x4_t& m, const float16x4_t& a, const float16x4_t& b)  { return neon_vbsl_impl<16,4,uint16x4_t>(m,a,b); }
inline float16x8_t vbslq_f16(const uint16x8_t& m, const float16x8_t& a, const float16x8_t& b) { return neon_vbsl_impl<16,8,uint16x8_t>(m,a,b); }

// ---------------------------------------------------------------------------
// Integer compare (mask producing all-ones / all-zeros per lane)
// ---------------------------------------------------------------------------
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vcmp_int(const NeonVector<B,N>& a, const NeonVector<B,N>& b, Kind cmp) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term c = tm.mkTerm(cmp, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, mk_bv_val(tm, B, -1), mk_bv_val(tm, B, 0)});
    }
    return NeonVector<B,N>(tm, lanes);
}
inline uint16x8_t vcgtq_u16(const uint16x8_t& a, const uint16x8_t& b) { return neon_vcmp_int(a, b, Kind::BITVECTOR_UGT); }
inline uint32x4_t vcgtq_u32(const uint32x4_t& a, const uint32x4_t& b) { return neon_vcmp_int(a, b, Kind::BITVECTOR_UGT); }
inline uint16x8_t vcltq_s16(const int16x8_t& a, const int16x8_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, mk_bv_val(tm, 16, -1), mk_bv_val(tm, 16, 0)});
    }
    return uint16x8_t(tm, lanes);
}
inline uint32x4_t vcltq_s32(const int32x4_t& a, const int32x4_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, mk_bv_val(tm, 32, -1), mk_bv_val(tm, 32, 0)});
    }
    return uint32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// Integer MIN/MAX (signed, templates)
// ---------------------------------------------------------------------------
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vmaxs_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, a.getLane(i), b.getLane(i)});
    }
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vmins_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, a.getLane(i), b.getLane(i)});
    }
    return NeonVector<B,N>(tm, lanes);
}
inline int8x8_t   vmax_s8 (const int8x8_t& a, const int8x8_t& b)   { return neon_vmaxs_impl(a, b); }
inline int8x8_t   vmin_s8 (const int8x8_t& a, const int8x8_t& b)   { return neon_vmins_impl(a, b); }
inline int8x16_t  vmaxq_s8(const int8x16_t& a, const int8x16_t& b) { return neon_vmaxs_impl(a, b); }
inline int8x16_t  vminq_s8(const int8x16_t& a, const int8x16_t& b) { return neon_vmins_impl(a, b); }
// Unsigned variants — use ULE/UGE.
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vmaxu_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_UGE, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, a.getLane(i), b.getLane(i)});
    }
    return NeonVector<B,N>(tm, lanes);
}
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vminu_impl(const NeonVector<B,N>& a, const NeonVector<B,N>& b) {
    auto& tm = g_ctx->tm; std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_ULE, {a.getLane(i), b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::ITE, {c, a.getLane(i), b.getLane(i)});
    }
    return NeonVector<B,N>(tm, lanes);
}
inline uint8x16_t vmaxq_u8(const uint8x16_t& a, const uint8x16_t& b) { return neon_vmaxu_impl(a, b); }
inline uint8x16_t vminq_u8(const uint8x16_t& a, const uint8x16_t& b) { return neon_vminu_impl(a, b); }
inline uint8x8_t  vmax_u8 (const uint8x8_t& a,  const uint8x8_t& b)  { return neon_vmaxu_impl(a, b); }
inline uint8x8_t  vmin_u8 (const uint8x8_t& a,  const uint8x8_t& b)  { return neon_vminu_impl(a, b); }
inline int16x8_t  vmaxq_s16(const int16x8_t& a, const int16x8_t& b) { return neon_vmaxs_impl(a, b); }
inline int16x8_t  vminq_s16(const int16x8_t& a, const int16x8_t& b) { return neon_vmins_impl(a, b); }

// Integer multiply (vector-vector)
inline int32x4_t vmulq_s32(const int32x4_t& a, const int32x4_t& b) { return neon_vmul_impl(a, b); }

// Reinterpret int8 → smaller-lane unsigned (concat-style)
inline uint16x4_t vreinterpret_u16_s8(const int8x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_CONCAT, {a.getLane(i*2 + 1), a.getLane(i*2)});
    }
    return uint16x4_t(tm, lanes);
}
inline uint32x2_t vreinterpret_u32_s8(const int8x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (int i = 0; i < 2; i++) {
        // little-endian: lane[i] = concat(a[i*4+3], a[i*4+2], a[i*4+1], a[i*4+0])
        Term result = a.getLane(i * 4);
        for (int j = 1; j < 4; j++) {
            result = tm.mkTerm(Kind::BITVECTOR_CONCAT, {a.getLane(i * 4 + j), result});
        }
        lanes[i] = result;
    }
    return uint32x2_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// Integer EXT (extract from concatenated pair)
// ---------------------------------------------------------------------------
inline int8x8_t vext_s8(const int8x8_t& a, const int8x8_t& b, int n) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        int idx = i + n;
        lanes[i] = (idx < 8) ? a.getLane(idx) : b.getLane(idx - 8);
    }
    return int8x8_t(tm, lanes);
}
inline float16x4_t vext_f16(const float16x4_t& a, const float16x4_t& b, int n) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        int idx = i + n;
        lanes[i] = (idx < 4) ? a.getLane(idx) : b.getLane(idx - 4);
    }
    return float16x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VSHLQ_N — left shift by immediate
// ---------------------------------------------------------------------------
template <size_t B, size_t N>
inline NeonVector<B,N> neon_vshl_n_impl(const NeonVector<B,N>& a, int n) {
    auto& tm = g_ctx->tm; Term sh = mk_bv_val(tm, B, n);
    std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++)
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SHL, {a.getLane(i), sh});
    return NeonVector<B,N>(tm, lanes);
}
inline int16x8_t vshlq_n_s16(const int16x8_t& a, int n) { return neon_vshl_n_impl(a, n); }
inline int32x4_t vshlq_n_s32(const int32x4_t& a, int n) { return neon_vshl_n_impl(a, n); }

// ---------------------------------------------------------------------------
// Widening: VMOVL, VADDL, VSUBL, VADDW, VSUBW, VMULL
// ---------------------------------------------------------------------------
inline int32x4_t vmovl_s16(const int16x4_t& a) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = tm.mkTerm(sext, {a.getLane(i)});
    return int32x4_t(tm, lanes);
}
inline int16x8_t vsubl_s8(const int8x8_t& a, const int8x8_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term ae = tm.mkTerm(sext, {a.getLane(i)});
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SUB, {ae, be});
    }
    return int16x8_t(tm, lanes);
}
inline int16x8_t vsubl_high_s8(const int8x16_t& a, const int8x16_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term ae = tm.mkTerm(sext, {a.getLane(i + 8)});
        Term be = tm.mkTerm(sext, {b.getLane(i + 8)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SUB, {ae, be});
    }
    return int16x8_t(tm, lanes);
}
inline int16x8_t vaddw_s8(const int16x8_t& a, const int8x8_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), be});
    }
    return int16x8_t(tm, lanes);
}
inline int16x8_t vsubw_s8(const int16x8_t& a, const int8x8_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SUB, {a.getLane(i), be});
    }
    return int16x8_t(tm, lanes);
}
inline uint16x8_t vaddw_u8(const uint16x8_t& a, const uint8x8_t& b) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {8});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term be = tm.mkTerm(zext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), be});
    }
    return uint16x8_t(tm, lanes);
}
inline uint32x4_t vaddw_u16(const uint32x4_t& a, const uint16x4_t& b) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {16});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term be = tm.mkTerm(zext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {a.getLane(i), be});
    }
    return uint32x4_t(tm, lanes);
}
inline int32x4_t vmull_s16(const int16x4_t& a, const int16x4_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term ae = tm.mkTerm(sext, {a.getLane(i)});
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_MULT, {ae, be});
    }
    return int32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VGET_LOW / VGET_HIGH / VCOMBINE / VGETQ_LANE
// ---------------------------------------------------------------------------
inline int16x4_t vget_low_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return int16x4_t(tm, lanes);
}
inline int16x4_t vget_high_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i + 4);
    return int16x4_t(tm, lanes);
}
inline int8x8_t vget_low_s8(const int8x16_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return int8x8_t(tm, lanes);
}
inline float16x4_t vget_low_f16(const float16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return float16x4_t(tm, lanes);
}
inline float16x4_t vget_high_f16(const float16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i + 4);
    return float16x4_t(tm, lanes);
}
inline float32x2_t vget_low_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 2> lanes = {a.getLane(0), a.getLane(1)};
    return float32x2_t(tm, lanes);
}
inline float32x2_t vget_high_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 2> lanes = {a.getLane(2), a.getLane(3)};
    return float32x2_t(tm, lanes);
}

inline int16x8_t vcombine_s16(const int16x4_t& lo, const int16x4_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 4; i++) { lanes[i] = lo.getLane(i); lanes[i+4] = hi.getLane(i); }
    return int16x8_t(tm, lanes);
}
inline int8x16_t vcombine_s8(const int8x8_t& lo, const int8x8_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 16> lanes;
    for (int i = 0; i < 8; i++) { lanes[i] = lo.getLane(i); lanes[i+8] = hi.getLane(i); }
    return int8x16_t(tm, lanes);
}
inline int32x4_t vcombine_s32(const int32x2_t& lo, const int32x2_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 2; i++) { lanes[i] = lo.getLane(i); lanes[i+2] = hi.getLane(i); }
    return int32x4_t(tm, lanes);
}
inline float32x4_t vcombine_f32(const float32x2_t& lo, const float32x2_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 2; i++) { lanes[i] = lo.getLane(i); lanes[i+2] = hi.getLane(i); }
    return float32x4_t(tm, lanes);
}
inline uint8x16_t vcombine_u8(const uint8x8_t& lo, const uint8x8_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 16> lanes;
    for (int i = 0; i < 8; i++) { lanes[i] = lo.getLane(i); lanes[i+8] = hi.getLane(i); }
    return uint8x16_t(tm, lanes);
}
inline uint16x8_t vcombine_u16(const uint16x4_t& lo, const uint16x4_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 4; i++) { lanes[i] = lo.getLane(i); lanes[i+4] = hi.getLane(i); }
    return uint16x8_t(tm, lanes);
}

// vgetq_lane_u64: extract a 64-bit lane (used in NaN-detection codepath of qs8)
inline uint64_t vgetq_lane_u64(const NeonVector<64, 2>& a, int lane) {
    (void)a; (void)lane; return 0; // concrete-int return — not used in symbolic path
}

// ---------------------------------------------------------------------------
// Saturating arithmetic
// ---------------------------------------------------------------------------
inline int32x4_t vqsubq_s32(const int32x4_t& a, const int32x4_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {32});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term ae = tm.mkTerm(sext, {a.getLane(i)});
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        Term diff = tm.mkTerm(Kind::BITVECTOR_SUB, {ae, be});
        lanes[i] = signed_saturate(tm, diff, 64, 32);
    }
    return int32x4_t(tm, lanes);
}
inline int16x8_t vqaddq_s16(const int16x8_t& a, const int16x8_t& b) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term ae = tm.mkTerm(sext, {a.getLane(i)});
        Term be = tm.mkTerm(sext, {b.getLane(i)});
        Term sum = tm.mkTerm(Kind::BITVECTOR_ADD, {ae, be});
        lanes[i] = signed_saturate(tm, sum, 32, 16);
    }
    return int16x8_t(tm, lanes);
}
inline int16x4_t vqmovn_s32(const int32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = signed_saturate(tm, a.getLane(i), 32, 16);
    return int16x4_t(tm, lanes);
}
inline int8x8_t vqmovn_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = signed_saturate(tm, a.getLane(i), 16, 8);
    return int8x8_t(tm, lanes);
}
inline int16x8_t vqmovn_high_s32(const int16x4_t& lo, const int32x4_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = lo.getLane(i);
    for (int i = 0; i < 4; i++) lanes[i + 4] = signed_saturate(tm, hi.getLane(i), 32, 16);
    return int16x8_t(tm, lanes);
}
inline int8x16_t vqmovn_high_s16(const int8x8_t& lo, const int16x8_t& hi) {
    auto& tm = g_ctx->tm; std::array<Term, 16> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = lo.getLane(i);
    for (int i = 0; i < 8; i++) lanes[i + 8] = signed_saturate(tm, hi.getLane(i), 16, 8);
    return int8x16_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VQRDMULHQ_S16 — Signed Saturating Rounding Doubling Multiply High
// ---------------------------------------------------------------------------
inline int16x8_t vqrdmulhq_s16(const int16x8_t& a, const int16x8_t& b) {
    auto& tm = g_ctx->tm;
    Op sext16 = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    std::array<Term, 8> lanes;
    Term round_const = mk_bv_val(tm, 32, 1 << 15);
    for (int i = 0; i < 8; i++) {
        Term ae = tm.mkTerm(sext16, {a.getLane(i)});
        Term be = tm.mkTerm(sext16, {b.getLane(i)});
        Term prod = tm.mkTerm(Kind::BITVECTOR_MULT, {ae, be});
        Term doubled = tm.mkTerm(Kind::BITVECTOR_ADD, {prod, prod});
        Term rounded = tm.mkTerm(Kind::BITVECTOR_ADD, {doubled, round_const});
        Term shifted = tm.mkTerm(Kind::BITVECTOR_ASHR, {rounded, mk_bv_val(tm, 32, 16)});
        lanes[i] = signed_saturate(tm, shifted, 32, 16);
    }
    return int16x8_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VRSHLQ_S32 — Signed rounding shift left by signed amount per lane
// ---------------------------------------------------------------------------
inline int32x4_t vrshlq_s32(const int32x4_t& a, const int32x4_t& b) {
    auto& tm = g_ctx->tm;
    Term zero32 = mk_bv_val(tm, 32, 0);
    Term one64 = mk_bv_val(tm, 64, 1);
    Term zero64 = mk_bv_val(tm, 64, 0);
    Op extract7_0 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {7u, 0u});
    Op extract31_0 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {31u, 0u});
    Op sext24 = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {24});
    Op sext32 = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {32});
    Op zext32 = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {32});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term shift_byte = tm.mkTerm(extract7_0, {b.getLane(i)});
        Term shift_s32 = tm.mkTerm(sext24, {shift_byte});
        Term is_right = tm.mkTerm(Kind::BITVECTOR_SLT, {shift_s32, zero32});
        Term neg_shift = tm.mkTerm(Kind::BITVECTOR_NEG, {shift_s32});
        Term a_wide = tm.mkTerm(sext32, {a.getLane(i)});
        Term neg_shift_64 = tm.mkTerm(zext32, {neg_shift});
        Term shift_minus_1 = tm.mkTerm(Kind::BITVECTOR_SUB, {neg_shift_64, one64});
        Term round_const = tm.mkTerm(Kind::BITVECTOR_SHL, {one64, shift_minus_1});
        Term neg_shift_is_zero = tm.mkTerm(Kind::EQUAL, {neg_shift, zero32});
        round_const = tm.mkTerm(Kind::ITE, {neg_shift_is_zero, zero64, round_const});
        Term rounded = tm.mkTerm(Kind::BITVECTOR_ADD, {a_wide, round_const});
        Term right_result_64 = tm.mkTerm(Kind::BITVECTOR_ASHR, {rounded, neg_shift_64});
        Term right_result = tm.mkTerm(extract31_0, {right_result_64});
        Term left_result = tm.mkTerm(Kind::BITVECTOR_SHL, {a.getLane(i), shift_s32});
        lanes[i] = tm.mkTerm(Kind::ITE, {is_right, right_result, left_result});
    }
    return int32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// VMLA_S32 — multiply-accumulate (NOT fused for integer)
// ---------------------------------------------------------------------------
inline int32x4_t vmlaq_s32(const int32x4_t& acc, const int32x4_t& b, const int32x4_t& c) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term prod = tm.mkTerm(Kind::BITVECTOR_MULT, {b.getLane(i), c.getLane(i)});
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_ADD, {acc.getLane(i), prod});
    }
    return int32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// FP arithmetic (float32) — vector-vector
// ---------------------------------------------------------------------------
template <size_t N>
inline NeonVector<32, N> fp32_binop(const NeonVector<32, N>& a, const NeonVector<32, N>& b, Kind op) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term a_fp = load_as_fp32(tm, a.getLane(i));
        Term b_fp = load_as_fp32(tm, b.getLane(i));
        Term res_fp;
        if (op == Kind::FLOATINGPOINT_MAX || op == Kind::FLOATINGPOINT_MIN) {
            // ARM FMAX/FMIN propagate NaNs, unlike SMT fp.max/fp.min and
            // RVV vfmax/vfmin. Payloads and exception flags are outside the
            // verifier's NaN-equivalent output contract.
            Term any_nan = tm.mkTerm(Kind::OR, {
                tm.mkTerm(Kind::FLOATINGPOINT_IS_NAN, {a_fp}),
                tm.mkTerm(Kind::FLOATINGPOINT_IS_NAN, {b_fp})});
            res_fp = tm.mkTerm(Kind::ITE, {
                any_nan, tm.mkFloatingPointNaN(8, 24),
                tm.mkTerm(op, {a_fp, b_fp})});
        } else {
            res_fp = tm.mkTerm(op, {rm, a_fp, b_fp});
        }
        lanes[i] = store_fp32_as_bv(tm, res_fp);
    }
    return NeonVector<32, N>(tm, lanes);
}
inline float32x4_t vaddq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_ADD); }
inline float32x4_t vsubq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_SUB); }
inline float32x4_t vmulq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_MULT); }
inline float32x4_t vdivq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_DIV); }
inline float32x4_t vminq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_MIN); }
inline float32x4_t vmaxq_f32(const float32x4_t& a, const float32x4_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_MAX); }
inline float32x2_t vsub_f32 (const float32x2_t& a, const float32x2_t& b) { return fp32_binop(a, b, Kind::FLOATINGPOINT_SUB); }

inline float32x4_t vfmaq_f32(const float32x4_t& a, const float32x4_t& b, const float32x4_t& c) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term cf = load_as_fp32(tm, c.getLane(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, bf, cf, af});
        lanes[i] = store_fp32_as_bv(tm, res);
    }
    return float32x4_t(tm, lanes);
}
inline float32x4_t vmlaq_f32(const float32x4_t& a, const float32x4_t& b, const float32x4_t& c) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term cf = load_as_fp32(tm, c.getLane(i));
        Term prod = tm.mkTerm(Kind::FLOATINGPOINT_MULT, {rm, bf, cf});
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, prod});
        lanes[i] = store_fp32_as_bv(tm, res);
    }
    return float32x4_t(tm, lanes);
}
inline float32x4_t vmlsq_f32(const float32x4_t& a, const float32x4_t& b, const float32x4_t& c) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term cf = load_as_fp32(tm, c.getLane(i));
        Term prod = tm.mkTerm(Kind::FLOATINGPOINT_MULT, {rm, bf, cf});
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_SUB, {rm, af, prod});
        lanes[i] = store_fp32_as_bv(tm, res);
    }
    return float32x4_t(tm, lanes);
}
inline float32x4_t vabsq_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        lanes[i] = store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af}));
    }
    return float32x4_t(tm, lanes);
}

// FP compare → uint32 mask
inline uint32x4_t vcgeq_f32(const float32x4_t& a, const float32x4_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GEQ, {af, bf});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 32, -1), mk_bv_val(tm, 32, 0)});
    }
    return uint32x4_t(tm, lanes);
}
inline uint32x4_t vcgtq_f32(const float32x4_t& a, const float32x4_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {af, bf});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 32, -1), mk_bv_val(tm, 32, 0)});
    }
    return uint32x4_t(tm, lanes);
}
inline uint32x4_t vcltq_f32(const float32x4_t& a, const float32x4_t& b) { return vcgtq_f32(b, a); }

// "absolute" compares (vcalt/vcagt = compare with abs(b)) — used by vapproxgelu/velu
inline uint32x4_t vcaltq_f32(const float32x4_t& a, const float32x4_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term aa = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af});
        Term ba = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {bf});
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {aa, ba});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 32, -1), mk_bv_val(tm, 32, 0)});
    }
    return uint32x4_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// FP conversions
// ---------------------------------------------------------------------------
inline float32x4_t vcvtq_f32_s32(const int32x4_t& a) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_SBV, {8, 24});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term fp = tm.mkTerm(cvt, {rm, a.getLane(i)});
        lanes[i] = store_fp32_as_bv(tm, fp);
    }
    return float32x4_t(tm, lanes);
}
inline int32x4_t vcvtq_s32_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm;
    Term rtz = tm.mkRoundingMode(RoundingMode::ROUND_TOWARD_ZERO);
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_SBV, {32});
    std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        lanes[i] = tm.mkTerm(cvt, {rtz, af});
    }
    return int32x4_t(tm, lanes);
}

// FP reinterpret no-ops
inline float32x4_t vreinterpretq_f32_s32(const int32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return float32x4_t(tm, lanes);
}
inline int32x4_t vreinterpretq_s32_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) lanes[i] = a.getLane(i);
    return int32x4_t(tm, lanes);
}
inline float16x8_t vreinterpretq_f16_u16(const uint16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return float16x8_t(tm, lanes);
}
inline uint16x8_t vreinterpretq_u16_f16(const float16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return uint16x8_t(tm, lanes);
}
inline int16x8_t vreinterpretq_s16_f16(const float16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return int16x8_t(tm, lanes);
}
inline float16x8_t vreinterpretq_f16_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) lanes[i] = a.getLane(i);
    return float16x8_t(tm, lanes);
}
// uint64x2_t reinterpret of int32x4_t (used in qs8 NaN-detection codepath)
inline NeonVector<64, 2> vreinterpretq_u64_s32(const int32x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> lanes;
    for (int i = 0; i < 2; i++) {
        // little-endian: lane[i] = concat(s32[2i+1], s32[2i])
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_CONCAT, {a.getLane(2*i + 1), a.getLane(2*i)});
    }
    return NeonVector<64, 2>(tm, lanes);
}

// ---------------------------------------------------------------------------
// FP16 ops (vminq_f16 / vmaxq_f16 / vaddq_f16 / vfmaq_f16 / vdivq_f16) on vec8
// ---------------------------------------------------------------------------
template <size_t N>
inline NeonVector<16, N> fp16_binop(const NeonVector<16, N>& a, const NeonVector<16, N>& b, Kind op) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, N> lanes;
    for (size_t i = 0; i < N; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        Term bf = load_as_fp16(tm, b.getLane(i));
        Term res = (op == Kind::FLOATINGPOINT_MAX || op == Kind::FLOATINGPOINT_MIN)
                    ? tm.mkTerm(op, {af, bf})
                    : tm.mkTerm(op, {rm, af, bf});
        lanes[i] = store_fp16_as_bv(tm, res);
    }
    return NeonVector<16, N>(tm, lanes);
}
inline float16x8_t vaddq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_ADD); }
inline float16x8_t vminq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_MIN); }
inline float16x8_t vmaxq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_MAX); }
inline float16x8_t vdivq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_DIV); }
inline float16x8_t vfmaq_f16(const float16x8_t& a, const float16x8_t& b, const float16x8_t& c) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        Term bf = load_as_fp16(tm, b.getLane(i));
        Term cf = load_as_fp16(tm, c.getLane(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, bf, cf, af});
        lanes[i] = store_fp16_as_bv(tm, res);
    }
    return float16x8_t(tm, lanes);
}
inline float16x8_t vabsq_f16(const float16x8_t& a) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        lanes[i] = store_fp16_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af}));
    }
    return float16x8_t(tm, lanes);
}
inline uint16x8_t vcagtq_f16(const float16x8_t& a, const float16x8_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        Term bf = load_as_fp16(tm, b.getLane(i));
        Term aa = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af});
        Term ba = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {bf});
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {aa, ba});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 16, -1), mk_bv_val(tm, 16, 0)});
    }
    return uint16x8_t(tm, lanes);
}
inline uint32x4_t vcagtq_f32(const float32x4_t& a, const float32x4_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        Term af = load_as_fp32(tm, a.getLane(i));
        Term bf = load_as_fp32(tm, b.getLane(i));
        Term aa = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af});
        Term ba = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {bf});
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {aa, ba});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 32, -1), mk_bv_val(tm, 32, 0)});
    }
    return uint32x4_t(tm, lanes);
}
inline uint16x8_t vcltq_f16(const float16x8_t& a, const float16x8_t& b) {
    auto& tm = g_ctx->tm; std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        Term bf = load_as_fp16(tm, b.getLane(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {af, bf});
        lanes[i] = tm.mkTerm(Kind::ITE, {cmp, mk_bv_val(tm, 16, -1), mk_bv_val(tm, 16, 0)});
    }
    return uint16x8_t(tm, lanes);
}

// FP16 ↔ int16 conversions
inline int16x8_t vcvtnq_s16_f16(const float16x8_t& a) {
    // NEON vcvtn (round-to-nearest, ties-to-even) FP→int contract:
    //   NaN → 0, ±inf saturate, finite OOR saturate.
    auto& tm = g_ctx->tm;
    Term rne = tm.mkRoundingMode(RoundingMode::ROUND_NEAREST_TIES_TO_EVEN);
    Term nan_result = mk_bv_val(tm, 16, (int64_t)0);
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term af = load_as_fp16(tm, a.getLane(i));
        lanes[i] = fp_to_int_lane(tm, af, /*eb=*/5, /*sb=*/11,
                                  /*dst_bits=*/16, /*is_signed=*/true,
                                  rne, nan_result);
    }
    return int16x8_t(tm, lanes);
}
inline float16x8_t vcvtq_f16_s16(const int16x8_t& a) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_SBV, {5, 11});
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        Term fp = tm.mkTerm(cvt, {rm, a.getLane(i)});
        lanes[i] = store_fp16_as_bv(tm, fp);
    }
    return float16x8_t(tm, lanes);
}

// ===========================================================================
// External function for f16-vmulcaddc — declared as a no-op stub so the source
// kernel compiles. (Actual semantics would come from XNNPACK; the harness
// presumably does not exercise this codepath, so we only need a definition.)
// ===========================================================================
// (Intentionally not added here — if needed by a harness, add to the harness file.)

// ===========================================================================
// SymbolicScalar<T> overloads for vdup/vmov — enables --symbolic-params kernels.
// Mirror of bitwuzla tree lines 2706-2777.  Integer lanes hold raw BV terms;
// float32 lanes hold BV terms (per concrete vdupq_n_f32 above), so the float
// overloads pipe through store_fp32_as_bv before filling lanes.
// ===========================================================================
inline int8x8_t vdup_n_s8(SymbolicScalar<int8_t> v) {
    std::array<Term, 8> l; l.fill(v.term());
    return int8x8_t(g_ctx->tm, l);
}
inline uint8x8_t vdup_n_u8(SymbolicScalar<uint8_t> v) {
    std::array<Term, 8> l; l.fill(v.term());
    return uint8x8_t(g_ctx->tm, l);
}
inline int16x4_t vdup_n_s16(SymbolicScalar<int16_t> v) {
    std::array<Term, 4> l; l.fill(v.term());
    return int16x4_t(g_ctx->tm, l);
}
inline int8x16_t vdupq_n_s8(SymbolicScalar<int8_t> v) {
    std::array<Term, 16> l; l.fill(v.term());
    return int8x16_t(g_ctx->tm, l);
}
inline uint8x16_t vdupq_n_u8(SymbolicScalar<uint8_t> v) {
    std::array<Term, 16> l; l.fill(v.term());
    return uint8x16_t(g_ctx->tm, l);
}
inline int16x8_t vdupq_n_s16(SymbolicScalar<int16_t> v) {
    std::array<Term, 8> l; l.fill(v.term());
    return int16x8_t(g_ctx->tm, l);
}
inline uint16x8_t vdupq_n_u16(SymbolicScalar<uint16_t> v) {
    std::array<Term, 8> l; l.fill(v.term());
    return uint16x8_t(g_ctx->tm, l);
}
inline int32x4_t vdupq_n_s32(SymbolicScalar<int32_t> v) {
    std::array<Term, 4> l; l.fill(v.term());
    return int32x4_t(g_ctx->tm, l);
}
inline uint32x4_t vdupq_n_u32(SymbolicScalar<uint32_t> v) {
    std::array<Term, 4> l; l.fill(v.term());
    return uint32x4_t(g_ctx->tm, l);
}
inline int32x2_t vdup_n_s32(SymbolicScalar<int32_t> v) {
    std::array<Term, 2> l; l.fill(v.term());
    return int32x2_t(g_ctx->tm, l);
}
// Width-bridging overloads — accept any integer SymbolicScalar and cast to lane width.
inline int16x8_t vdupq_n_s16(SymbolicScalar<int32_t> v) { return vdupq_n_s16(v.template cast<int16_t>()); }
inline int16x8_t vdupq_n_s16(SymbolicScalar<int8_t> v)  { return vdupq_n_s16(v.template cast<int16_t>()); }
inline int32x4_t vdupq_n_s32(SymbolicScalar<int16_t> v) { return vdupq_n_s32(v.template cast<int32_t>()); }
inline int8x8_t  vdup_n_s8(SymbolicScalar<int32_t> v)   { return vdup_n_s8(v.template cast<int8_t>()); }
inline int8x8_t  vdup_n_s8(SymbolicScalar<int16_t> v)   { return vdup_n_s8(v.template cast<int8_t>()); }
inline uint8x8_t vdup_n_u8(SymbolicScalar<uint32_t> v)  { return vdup_n_u8(v.template cast<uint8_t>()); }
inline uint8x8_t vdup_n_u8(SymbolicScalar<uint16_t> v)  { return vdup_n_u8(v.template cast<uint8_t>()); }
inline int16x4_t vdup_n_s16(SymbolicScalar<int32_t> v)  { return vdup_n_s16(v.template cast<int16_t>()); }
// vmov aliases
inline int8x16_t  vmovq_n_s8(SymbolicScalar<int8_t> v)    { return vdupq_n_s8(v); }
inline int16x8_t  vmovq_n_s16(SymbolicScalar<int16_t> v)  { return vdupq_n_s16(v); }
inline int16x8_t  vmovq_n_s16(SymbolicScalar<int32_t> v)  { return vdupq_n_s16(v.template cast<int16_t>()); }
inline int32x4_t  vmovq_n_s32(SymbolicScalar<int32_t> v)  { return vdupq_n_s32(v); }
inline uint8x16_t vmovq_n_u8(SymbolicScalar<uint8_t> v)   { return vdupq_n_u8(v); }
inline uint16x8_t vmovq_n_u16(SymbolicScalar<uint16_t> v) { return vdupq_n_u16(v); }
inline uint32x4_t vmovq_n_u32(SymbolicScalar<uint32_t> v) { return vdupq_n_u32(v); }

// FP vdup with SymbolicScalar<float> — store BV pattern in lanes (matches concrete vdupq_n_f32).
inline float32x4_t vdupq_n_f32(SymbolicScalar<float> v) {
    auto& tm = g_ctx->tm;
    Term bv = store_fp32_as_bv(tm, v.term());
    std::array<Term, 4> l; l.fill(bv);
    return float32x4_t(tm, l);
}
inline float32x2_t vdup_n_f32(SymbolicScalar<float> v) {
    auto& tm = g_ctx->tm;
    Term bv = store_fp32_as_bv(tm, v.term());
    std::array<Term, 2> l; l.fill(bv);
    return float32x2_t(tm, l);
}
inline float32x4_t vmovq_n_f32(SymbolicScalar<float> v) { return vdupq_n_f32(v); }

// ===========================================================================
// XNNPACK SIMD abstraction shim — f16-neonfp16arith
// ===========================================================================
// Provides the symbol surface that upstream XNNPACK NEON kernels assume from
// `src/xnnpack/simd/f16-neonfp16arith.h`.  Lets unmodified upstream sources
// compile in salt's verification harness without manual lowering.

// Bare-NEON intrinsics the shim builds on (not previously defined in this tree).
inline float16x8_t vsubq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_SUB); }
inline float16x8_t vmulq_f16(const float16x8_t& a, const float16x8_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_MULT); }
inline float16x8_t vdupq_n_f16(float v) {
    auto& tm = g_ctx->tm;
    salt_float16 fp(v);
    Term bv = mk_bv_val(tm, 16, fp.value);
    std::array<Term, 8> lanes; lanes.fill(bv);
    return float16x8_t(tm, lanes);
}
inline float16x4_t vdup_n_f16(float v) {
    auto& tm = g_ctx->tm;
    salt_float16 fp(v);
    Term bv = mk_bv_val(tm, 16, fp.value);
    std::array<Term, 4> lanes; lanes.fill(bv);
    return float16x4_t(tm, lanes);
}
inline float16x8_t vld1q_f16(const salt_float16* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<16, 8>(b.ptrToByteOffset(p));
}
inline void vst1q_f16(salt_float16* p, const float16x8_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<16, 8>(b.ptrToByteOffset(p), v);
}
inline float16x4_t vld1_dup_f16(const salt_float16* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 16);
    std::array<Term, 4> lanes; lanes.fill(v);
    return float16x4_t(tm, lanes);
}
inline void vst1_lane_f16(salt_float16* p, const float16x4_t& val, int lane) {
    auto& b = g_ctx->findBuffer(p);
    b.storeScalar(b.ptrToByteOffset(p), val.getLane(lane), 16);
}
inline float16x8_t vld1q_dup_f16(const salt_float16* p) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    Term v = b.loadScalar(b.ptrToByteOffset(p), 16);
    std::array<Term, 8> lanes; lanes.fill(v);
    return float16x8_t(tm, lanes);
}
inline float16x4_t vadd_f16(const float16x4_t& a, const float16x4_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 4> lanes;
    for (size_t i = 0; i < 4; i++) {
        Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
        Term af = tm.mkTerm(op, {a.getLane(i)});
        Term bf = tm.mkTerm(op, {b.getLane(i)});
        Term sf = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
        Sort bv16 = tm.mkBitVectorSort(16);
        Term bv = tm.mkConst(bv16, "_neon_f16_2bv_" + std::to_string(fp32_bv_counter()++));
        Term fp_from_bv = tm.mkTerm(op, {bv});
        g_ctx->solver->assertFormula(tm.mkTerm(Kind::EQUAL, {fp_from_bv, sf}));
        lanes[i] = bv;
    }
    return float16x4_t(tm, lanes);
}
inline float16x4_t vmul_f16(const float16x4_t& a, const float16x4_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::array<Term, 4> lanes;
    for (size_t i = 0; i < 4; i++) {
        Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
        Term af = tm.mkTerm(op, {a.getLane(i)});
        Term bf = tm.mkTerm(op, {b.getLane(i)});
        Term sf = tm.mkTerm(Kind::FLOATINGPOINT_MULT, {rm, af, bf});
        Sort bv16 = tm.mkBitVectorSort(16);
        Term bv = tm.mkConst(bv16, "_neon_f16_2bv_" + std::to_string(fp32_bv_counter()++));
        Term fp_from_bv = tm.mkTerm(op, {bv});
        g_ctx->solver->assertFormula(tm.mkTerm(Kind::EQUAL, {fp_from_bv, sf}));
        lanes[i] = bv;
    }
    return float16x4_t(tm, lanes);
}
inline float16x4_t vsub_f16(const float16x4_t& a, const float16x4_t& b) { return fp16_binop(a, b, Kind::FLOATINGPOINT_SUB); }

using xnn_simd_f16_t = float16x8_t;
constexpr size_t xnn_simd_size_f16  = 8;
constexpr size_t xnn_simd_bytes_f16 = 16;

// Unaligned vector load/store at f16 granularity.
inline xnn_simd_f16_t xnn_loadu_f16(const xnn_float16* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<16, 8>(b.ptrToByteOffset(p));
}
inline void xnn_storeu_f16(xnn_float16* p, const xnn_simd_f16_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<16, 8>(b.ptrToByteOffset(p), v);
}
// Tail load: lanes [0, n) ← memory; lanes [n, 8) ← 0.
inline xnn_simd_f16_t xnn_load_tail_f16(const xnn_float16* p, size_t n) {
    auto& tm = g_ctx->tm;
    auto& b  = g_ctx->findBuffer(p);
    size_t off = b.ptrToByteOffset(p);
    Term zero = mk_bv_val(tm, 16, 0);
    std::array<Term, 8> lanes;
    for (size_t i = 0; i < 8; i++) {
        lanes[i] = (i < n) ? b.loadScalar(off + i * 2, 16) : zero;
    }
    return float16x8_t(tm, lanes);
}
// Tail store: write lanes [0, n) of v; bytes past p[n] untouched.
inline void xnn_store_tail_f16(xnn_float16* p, const xnn_simd_f16_t& v, size_t n) {
    auto& b = g_ctx->findBuffer(p);
    size_t off = b.ptrToByteOffset(p);
    for (size_t i = 0; i < n; i++) {
        b.storeScalar(off + i * 2, v.getLane(i), 16);
    }
}
inline xnn_simd_f16_t xnn_add_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b) { return vaddq_f16(a, b); }
inline xnn_simd_f16_t xnn_sub_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b) { return vsubq_f16(a, b); }
inline xnn_simd_f16_t xnn_mul_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b) { return vmulq_f16(a, b); }
inline xnn_simd_f16_t xnn_min_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b) { return vminq_f16(a, b); }
inline xnn_simd_f16_t xnn_max_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b) { return vmaxq_f16(a, b); }
// XNNPACK signature: xnn_fmadd_f16(a, b, c) computes a*b + c.
// NEON signature:    vfmaq_f16(c, a, b)     computes c + a*b.  Operand reorder.
inline xnn_simd_f16_t xnn_fmadd_f16(const xnn_simd_f16_t& a, const xnn_simd_f16_t& b, const xnn_simd_f16_t& c) {
    return vfmaq_f16(c, a, b);
}
// Bit-level left shift on the f16 representation (shifts the underlying u16).
inline xnn_simd_f16_t xnn_sll_f16(const xnn_simd_f16_t& a, int n) {
    auto& tm = g_ctx->tm;
    Term shift = mk_bv_val(tm, 16, (uint64_t)n);
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        lanes[i] = tm.mkTerm(Kind::BITVECTOR_SHL, {a.getLane(i), shift});
    }
    return float16x8_t(tm, lanes);
}

// salt_neon_gather2_s32 — verification-only NEON table gather (mirrors the
// bitwuzla version in src/verification/neon/intrinsics.hpp). Replaces the
// scalar extract→cast→pointer-load idiom for int32 LUT access (e.g. f32-velu).
// Returns int32x2_t (BV32 lanes) gathered from the registered buffer at
// `base` using the two 32-bit byte offsets packed in `packed_idx[half]`.
inline int32x2_t salt_neon_gather2_s32(
    const void* base, const uint64x2_t& packed_idx, int half)
{
    auto& tm = g_ctx->tm;
    auto& buf = g_ctx->findBuffer(base);
    size_t base_off = buf.ptrToByteOffset(base);
    constexpr size_t elem_bytes = 4;

    if (half < 0 || half > 1) {
        throw std::runtime_error(
            "salt_neon_gather2_s32: half must be 0 or 1, got " + std::to_string(half));
    }
    if (base_off + elem_bytes > buf.numBytes()) {
        throw std::runtime_error(
            "salt_neon_gather2_s32: base pointer leaves no room for a single element");
    }

    size_t max_valid_start = buf.numBytes() - base_off - elem_bytes;

    std::vector<Term> cached(max_valid_start + 1);
    for (size_t k = 0; k <= max_valid_start; k++) {
        cached[k] = buf.loadScalar(base_off + k, 32);
    }

    Term packed = packed_idx.getLane(half);
    Op extract_lo = tm.mkOp(Kind::BITVECTOR_EXTRACT, {31u, 0u});
    Op extract_hi = tm.mkOp(Kind::BITVECTOR_EXTRACT, {63u, 32u});
    Term off_lo = tm.mkTerm(extract_lo, {packed});
    Term off_hi = tm.mkTerm(extract_hi, {packed});

    static thread_local size_t oob_seq = 0;
    size_t call_id = oob_seq++;
    Sort bv32 = tm.mkBitVectorSort(32);

    auto gather_one = [&](Term sym_off, size_t lane_id) -> Term {
        Term val = tm.mkConst(bv32,
            "neon_gather_oob_" + std::to_string(call_id) + "_" + std::to_string(lane_id));
        for (size_t k = 0; k <= max_valid_start; k++) {
            val = tm.mkTerm(Kind::ITE,
                {tm.mkTerm(Kind::EQUAL, {sym_off, mk_bv_val(tm, 32, k)}),
                 cached[k], val});
        }
        return val;
    };

    std::array<Term, 2> lanes;
    lanes[0] = gather_one(off_lo, 0);
    lanes[1] = gather_one(off_hi, 1);
    return int32x2_t(tm, lanes);
}

// ---------------------------------------------------------------------------
// uint8 NEON intrinsics — used by x8-lut and byte-level kernels.
// ---------------------------------------------------------------------------

inline uint8x16_t vmovq_n_u8(uint8_t v)  { return vdupq_n_u8(v); }

inline uint8x16_t vsubq_u8(const uint8x16_t& a, const uint8x16_t& b) {
    return neon_vsub_impl(a, b);
}

inline uint8x16_t vld1q_u8(const uint8_t* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<8, 16>(b.ptrToByteOffset(p));
}

inline void vst1q_u8(uint8_t* p, const uint8x16_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<8, 16>(b.ptrToByteOffset(p), v);
}

inline void vst1_u8(uint8_t* p, const uint8x8_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<8, 8>(b.ptrToByteOffset(p), v);
}

// LD1x4: load 4 consecutive uint8x16 vectors.
inline VectorTuple<uint8x16_t, 4> vld1q_u8_x4(const uint8_t* p) {
    VectorTuple<uint8x16_t, 4> result;
    for (int k = 0; k < 4; k++) result.val[k] = vld1q_u8(p + k * 16);
    return result;
}

// QTBL4: 64-entry table lookup (out-of-range → 0).
inline uint8x16_t vqtbl4q_u8(const VectorTuple<uint8x16_t, 4>& tbl,
                              const uint8x16_t& idx) {
    auto& tm = g_ctx->tm;
    std::array<Term, 16> lanes;
    Term zero = mk_bv_val(tm, 8, 0);
    for (int i = 0; i < 16; i++) {
        Term result = zero;
        for (int j = 63; j >= 0; j--) {
            Term entry = tbl.val[j / 16].getLane(j % 16);
            Term cmp = tm.mkTerm(Kind::EQUAL,
                {idx.getLane(i), mk_bv_val(tm, 8, j)});
            result = tm.mkTerm(Kind::ITE, {cmp, entry, result});
        }
        lanes[i] = result;
    }
    return uint8x16_t(tm, lanes);
}

// QTBX4: same as QTBL4 but preserves `dest` for out-of-range indices.
inline uint8x16_t vqtbx4q_u8(const uint8x16_t& dest,
                              const VectorTuple<uint8x16_t, 4>& tbl,
                              const uint8x16_t& idx) {
    auto& tm = g_ctx->tm;
    std::array<Term, 16> lanes;
    for (int i = 0; i < 16; i++) {
        Term result = dest.getLane(i);
        for (int j = 63; j >= 0; j--) {
            Term entry = tbl.val[j / 16].getLane(j % 16);
            Term cmp = tm.mkTerm(Kind::EQUAL,
                {idx.getLane(i), mk_bv_val(tm, 8, j)});
            result = tm.mkTerm(Kind::ITE, {cmp, entry, result});
        }
        lanes[i] = result;
    }
    return uint8x16_t(tm, lanes);
}

inline uint8x8_t vget_low_u8(const uint8x16_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) l[i] = a.getLane(i);
    return uint8x8_t(tm, l);
}

inline uint8x8_t vget_high_u8(const uint8x16_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) l[i] = a.getLane(i + 8);
    return uint8x8_t(tm, l);
}

inline uint8x8_t vext_u8(const uint8x8_t& a, const uint8x8_t& b, int n) {
    auto& tm = g_ctx->tm;
    std::array<Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        int idx = i + n;
        lanes[i] = (idx < 8) ? a.getLane(idx) : b.getLane(idx - 8);
    }
    return uint8x8_t(tm, lanes);
}

inline uint32x2_t vreinterpret_u32_u8(const uint8x8_t& a) {
    return vreinterpret_u32_s8(a);
}

inline uint16x4_t vreinterpret_u16_u8(const uint8x8_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) {
        l[i] = tm.mkTerm(Kind::BITVECTOR_CONCAT,
                          {a.getLane(i*2 + 1), a.getLane(i*2)});
    }
    return uint16x4_t(tm, l);
}

inline void vst1_lane_u8(uint8_t* p, const uint8x8_t& v, int lane) {
    auto& b = g_ctx->findBuffer(p);
    b.storeScalar(b.ptrToByteOffset(p), v.getLane(lane), 8);
}

// ===========================================================================
// BF16 (Brain Float 16) — bf16-gemm support.
//   Lane storage: raw 16-bit IEEE pattern (NeonVector<16, N>).
//   bf16→fp32:    exact (concat with 16 zero bits, view as fp32).
//   fp32→bf16:    RNE rounding via XNNPACK biased-truncate idiom.
// ===========================================================================

// Concrete-uint16 vmovq_n_u16 (the existing one only takes SymbolicScalar).
inline uint16x8_t vmovq_n_u16(uint16_t v) { return vdupq_n_u16(v); }

// vceqq_u16: element-wise equality, returns 0xFFFF on equal else 0x0000.
inline uint16x8_t vceqq_u16(const uint16x8_t& a, const uint16x8_t& b) {
    auto& tm = g_ctx->tm;
    Term ones  = mk_bv_val(tm, 16, (int64_t)0xFFFF);
    Term zeros = mk_bv_val(tm, 16, (int64_t)0);
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) {
        Term eq = tm.mkTerm(Kind::EQUAL, {a.getLane(i), b.getLane(i)});
        l[i] = tm.mkTerm(Kind::ITE, {eq, ones, zeros});
    }
    return uint16x8_t(tm, l);
}
// vceq_u8: element-wise equality, returns 0xFF on equal else 0x00 (8-lane).
inline uint8x8_t vceq_u8(const uint8x8_t& a, const uint8x8_t& b) {
    auto& tm = g_ctx->tm;
    Term ones  = mk_bv_val(tm, 8, (int64_t)0xFF);
    Term zeros = mk_bv_val(tm, 8, (int64_t)0);
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) {
        Term eq = tm.mkTerm(Kind::EQUAL, {a.getLane(i), b.getLane(i)});
        l[i] = tm.mkTerm(Kind::ITE, {eq, ones, zeros});
    }
    return uint8x8_t(tm, l);
}
// vbsl_u8: bitwise select.  result[i] = (m[i] & a[i]) | (~m[i] & b[i]).
inline uint8x8_t vbsl_u8(const uint8x8_t& m, const uint8x8_t& a, const uint8x8_t& b) {
    return neon_vbsl_impl(m, a, b);
}
// vlut4_u8: 4-entry table lookup.  result[i] = T[idx[i] & 3].
// Verifier-only helper modeling a small variant of vqtbl1q_u8.
inline uint8x8_t vlut4_u8(const uint8x8_t& idx,
                          uint8_t T0, uint8_t T1, uint8_t T2, uint8_t T3) {
    auto& tm = g_ctx->tm;
    Term mask3 = mk_bv_val(tm, 8, (int64_t)3);
    Term k0 = mk_bv_val(tm, 8, (int64_t)0);
    Term k1 = mk_bv_val(tm, 8, (int64_t)1);
    Term k2 = mk_bv_val(tm, 8, (int64_t)2);
    Term v0 = mk_bv_val(tm, 8, (int64_t)T0);
    Term v1 = mk_bv_val(tm, 8, (int64_t)T1);
    Term v2 = mk_bv_val(tm, 8, (int64_t)T2);
    Term v3 = mk_bv_val(tm, 8, (int64_t)T3);
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) {
        Term masked = tm.mkTerm(Kind::BITVECTOR_AND, {idx.getLane(i), mask3});
        Term ite = tm.mkTerm(Kind::ITE,
                    {tm.mkTerm(Kind::EQUAL, {masked, k0}), v0,
                     tm.mkTerm(Kind::ITE,
                       {tm.mkTerm(Kind::EQUAL, {masked, k1}), v1,
                        tm.mkTerm(Kind::ITE,
                          {tm.mkTerm(Kind::EQUAL, {masked, k2}), v2, v3})})});
        l[i] = ite;
    }
    return uint8x8_t(tm, l);
}

// vpaddq_f32: pairwise add. Output = [a0+a1, a2+a3, b0+b1, b2+b3].
inline float32x4_t vpaddq_f32(const float32x4_t& a, const float32x4_t& b) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    auto pair = [&](Term x_bv, Term y_bv) {
        Term sum_fp = tm.mkTerm(Kind::FLOATINGPOINT_ADD,
                                {rm, load_as_fp32(tm, x_bv), load_as_fp32(tm, y_bv)});
        return store_fp32_as_bv(tm, sum_fp);
    };
    std::array<Term, 4> l;
    l[0] = pair(a.getLane(0), a.getLane(1));
    l[1] = pair(a.getLane(2), a.getLane(3));
    l[2] = pair(b.getLane(0), b.getLane(1));
    l[3] = pair(b.getLane(2), b.getLane(3));
    return float32x4_t(tm, l);
}

// vext_u16(a, b, n): concat(b,a) >> (n*16), take low 4 lanes.
inline uint16x4_t vext_u16(const uint16x4_t& a, const uint16x4_t& b, int n) {
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) {
        int src = i + n;
        l[i] = (src < 4) ? a.getLane(src) : b.getLane(src - 4);
    }
    return uint16x4_t(g_ctx->tm, l);
}

// vreinterpret_u32_u16: lane-combine 4×u16 → 2×u32.
inline uint32x2_t vreinterpret_u32_u16(const uint16x4_t& a) {
    auto& tm = g_ctx->tm;
    std::array<Term, 2> l;
    for (int i = 0; i < 2; i++) {
        // Little-endian: lane[2i] is low, lane[2i+1] is high → concat(high, low).
        l[i] = tm.mkTerm(Kind::BITVECTOR_CONCAT,
                         {a.getLane(2*i + 1), a.getLane(2*i)});
    }
    return uint32x2_t(tm, l);
}

// ---- BF16 reinterprets (no-op on lanes) -----------------------------------
inline bfloat16x4_t vreinterpret_bf16_u16(const uint16x4_t& a) {
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) l[i] = a.getLane(i);
    return bfloat16x4_t(g_ctx->tm, l);
}
inline uint16x4_t vreinterpret_u16_bf16(const bfloat16x4_t& a) {
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) l[i] = a.getLane(i);
    return uint16x4_t(g_ctx->tm, l);
}
inline bfloat16x8_t vreinterpretq_bf16_u16(const uint16x8_t& a) {
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) l[i] = a.getLane(i);
    return bfloat16x8_t(g_ctx->tm, l);
}
inline uint16x8_t vreinterpretq_u16_bf16(const bfloat16x8_t& a) {
    std::array<Term, 8> l;
    for (int i = 0; i < 8; i++) l[i] = a.getLane(i);
    return uint16x8_t(g_ctx->tm, l);
}
inline uint32x2_t vreinterpret_u32_bf16(const bfloat16x4_t& a) {
    return vreinterpret_u32_u16(vreinterpret_u16_bf16(a));
}

// ---- BF16 loads / stores --------------------------------------------------
inline bfloat16x8_t vld1q_bf16(const bfloat16_t* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<16, 8>(b.ptrToByteOffset(p));
}
inline bfloat16x4_t vld1_bf16(const bfloat16_t* p) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadNeon<16, 4>(b.ptrToByteOffset(p));
}
inline bfloat16x4_t vld1_lane_bf16(const bfloat16_t* p,
                                    const bfloat16x4_t& v, int lane) {
    auto r = v;
    auto& b = g_ctx->findBuffer(p);
    r.setLane(lane, b.loadScalar(b.ptrToByteOffset(p), 16));
    return r;
}
inline void vst1_bf16(bfloat16_t* p, const bfloat16x4_t& v) {
    auto& b = g_ctx->findBuffer(p);
    b.storeNeon<16, 4>(b.ptrToByteOffset(p), v);
}
inline void vst1_lane_bf16(bfloat16_t* p, const bfloat16x4_t& v, int lane) {
    auto& b = g_ctx->findBuffer(p);
    b.storeScalar(b.ptrToByteOffset(p), v.getLane(lane), 16);
}

// ---- BF16 ↔ FP32 conversions ----------------------------------------------
// vcvt_f32_bf16: bf16 → fp32 is exact (BF16 mantissa fits in fp32 mantissa).
// Implementation: concat bv16 with 16 zero bits → bv32 → load_as_fp32.
inline float32x4_t vcvt_f32_bf16(const bfloat16x4_t& a) {
    auto& tm = g_ctx->tm;
    Term zero16 = mk_bv_val(tm, 16, (int64_t)0);
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) {
        Term bv32 = tm.mkTerm(Kind::BITVECTOR_CONCAT, {a.getLane(i), zero16});
        // Store bv32 directly — it already encodes the fp32 IEEE pattern;
        // downstream fp32 ops will round-trip through load_as_fp32.
        l[i] = bv32;
    }
    return float32x4_t(tm, l);
}

// vcvt_bf16_f32: fp32 → bf16 with RNE rounding (BFCVTN).
// Uses XNNPACK's biased-truncate idiom: bf16 = ((bv32 + 0x7FFF + ((bv32>>16)&1)) >> 16)[15:0].
// SOUNDNESS NOTE: handles NaN/inf as deterministic bit ops on the IEEE pattern,
// but NaN's fp32 BV is ambiguous in cvc5 (multiple bv32 satisfy fp32_from_bits).
// If a caller exercises NaN inputs and verification fails, this needs an
// fp_convert.hpp-style faithful wrapper (mirroring vcvtnq_s16_f16).
inline bfloat16x4_t vcvt_bf16_f32(const float32x4_t& a) {
    auto& tm = g_ctx->tm;
    Term bias_lo = mk_bv_val(tm, 32, (int64_t)0x7FFF);
    Term one_32  = mk_bv_val(tm, 32, (int64_t)1);
    Term shift16 = mk_bv_val(tm, 32, (int64_t)16);
    Op extract_low_bit = tm.mkOp(Kind::BITVECTOR_EXTRACT, {16u, 16u});  // bit 16
    Op extract_top16   = tm.mkOp(Kind::BITVECTOR_EXTRACT, {31u, 16u});
    std::array<Term, 4> l;
    for (int i = 0; i < 4; i++) {
        Term fp = load_as_fp32(tm, a.getLane(i));
        Term bv = store_fp32_as_bv(tm, fp);
        // round_bit = (bv >> 16) & 1
        Term round_bit_1bit = tm.mkTerm(extract_low_bit, {bv});
        Term round_bit = tm.mkTerm(Kind::BITVECTOR_CONCAT,
                                    {mk_bv_val(tm, 31, (int64_t)0), round_bit_1bit});
        Term sum1 = tm.mkTerm(Kind::BITVECTOR_ADD, {bv, bias_lo});
        Term sum2 = tm.mkTerm(Kind::BITVECTOR_ADD, {sum1, round_bit});
        l[i] = tm.mkTerm(extract_top16, {sum2});
    }
    return bfloat16x4_t(tm, l);
}

// vbfdotq_f32(r, a, b): pairwise BF16 dot product accumulating into f32.
//   For i in 0..3:  out[i] = r[i] + bf16_to_f32(a[2i])   * bf16_to_f32(b[2i])
//                                  + bf16_to_f32(a[2i+1]) * bf16_to_f32(b[2i+1])
// Arm BFDOT contract (per ARM ARM): Round-to-Odd, FZ subnormal in/out, default-NaN.
// Delegates to bfdot_lane_strict in fp_bf16.hpp for the full strict-Arm semantics.
inline float32x4_t vbfdotq_f32(const float32x4_t& r,
                                const bfloat16x8_t& a,
                                const bfloat16x8_t& b) {
    auto& tm = g_ctx->tm;
    std::array<Term, 4> out;
    for (int i = 0; i < 4; i++) {
        out[i] = bfdot_lane_strict(tm,
                                    r.getLane(i),
                                    a.getLane(2*i),     b.getLane(2*i),
                                    a.getLane(2*i + 1), b.getLane(2*i + 1));
    }
    return float32x4_t(tm, out);
}

} // namespace salt_cvc5
