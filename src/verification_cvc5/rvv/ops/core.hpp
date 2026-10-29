#pragma once
// Hand-written core RVV intrinsics (vsetvl, hand-tuned load/store,
// fp helpers, etc.) — foundational set, NOT generated.
// Relocated verbatim from intrinsics.hpp (now the shared infra base).
#include "../intrinsics.hpp"
namespace salt_cvc5 {

inline size_t __riscv_vsetvl_e16m1(size_t avl) { return _rvv_vsetvl(avl, 16, 1); }
inline size_t __riscv_vsetvl_e8m1(size_t avl)  { return _rvv_vsetvl(avl,  8, 1); }

// vle/vse for i8m1 — used by s8-maxpool.
inline vint8m1_t __riscv_vle8_v_i8m1(const int8_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 8);
}
inline void __riscv_vse8_v_i8m1(int8_t* p, const vint8m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 8, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}

// Signed vector max/min for i8m1 — used by s8-maxpool clamp + per-lane max.
inline vint8m1_t __riscv_vmax_vv_i8m1(const vint8m1_t& a, const vint8m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), b.getElement(i)});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.getElement(i)));
    }
    return RVVVector(tm, 8, r);
}
inline vint8m1_t __riscv_vmax_vx_i8m1(const vint8m1_t& a, int8_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 8, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, c, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}
inline vint8m1_t __riscv_vmin_vx_i8m1(const vint8m1_t& a, int8_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 8, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, c, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}

// Unsigned vector max/min for u8m1 — used by u8-maxpool clamp + per-lane max.
inline vuint8m1_t __riscv_vmaxu_vv_u8m1(const vuint8m1_t& a, const vuint8m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_UGE, {a.getElement(i), b.getElement(i)});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.getElement(i)));
    }
    return RVVVector(tm, 8, r);
}
inline vuint8m1_t __riscv_vmaxu_vx_u8m1(const vuint8m1_t& a, uint8_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 8, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_UGE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, c, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}
inline vuint8m1_t __riscv_vminu_vx_u8m1(const vuint8m1_t& a, uint8_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 8, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_ULE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, c, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}

// ===========================================================================
// VID — element index sequence
// ===========================================================================
inline RVVVector __riscv_vid_v_u32m2(size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(mk_bv_val(tm, 32, static_cast<int64_t>(i)));
    return RVVVector(tm, 32, r);
}

// ===========================================================================
// VMV broadcast — scalar to all lanes
// ===========================================================================
inline vuint16m1_t __riscv_vmv_v_x_u16m1(uint16_t v, size_t vl) {
    auto& tm = g_ctx->tm;
    Term val = mk_bv_val(tm, 16, static_cast<int64_t>(v));
    return RVVVector(tm, 16, std::vector<Term>(vl, val));
}

// ===========================================================================
// REINTERPRET (no-ops on element storage)
// ===========================================================================
inline RVVVector __riscv_vreinterpret_v_i32m2_u32m2(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_u32m2_i32m2(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_u16m1_f16m1(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_f16m1_u16m1(const RVVVector& a) { return a; }

// ===========================================================================
// VADD / VSUB / VMUL / VSLL — concrete-scalar broadcast helpers
// ===========================================================================
inline RVVVector __riscv_vadd_vx_u32m2(const RVVVector& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, static_cast<int64_t>(b));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline RVVVector __riscv_vadd_vx_i32m2(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline RVVVector __riscv_vsub_vx_i32m2(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsub(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline RVVVector __riscv_vmul_vx_i32m2(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvmul(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline RVVVector __riscv_vsll_vx_i32m2(const RVVVector& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}

// ===========================================================================
// MIN/MAX vx (signed integer)
// ===========================================================================
inline RVVVector __riscv_vmax_vx_i32m2(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, cond, a.getElement(i), bv));
    }
    return RVVVector(tm, 32, r);
}
inline RVVVector __riscv_vmin_vx_i32m2(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, cond, a.getElement(i), bv));
    }
    return RVVVector(tm, 32, r);
}

// ===========================================================================
// MASK ops: vmslt / vmsge against scalar, vmand
// (b16 = 1-bit-per-element; ratio EEW/SEW=2 so naming mirrors RVV spec)
// ===========================================================================
inline MaskVector __riscv_vmslt_vx_i32m2_b16(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getElement(i), bv});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmsge_vx_i32m2_b16(const RVVVector& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), bv});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmand_mm_b16(const MaskVector& a, const MaskVector& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        bits.push_back(fold_bvand(tm, a.getBit(i), b.getBit(i)));
    }
    return MaskVector(tm, bits);
}

// ===========================================================================
// FP16 helpers (BV16 ↔ FP16) and binary FP ops
// ===========================================================================
inline Term rvv_load_as_fp16(TermManager& tm, Term bv) {
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
    return tm.mkTerm(op, {bv});
}

inline size_t& rvv_fp16_bv_counter() {
    static size_t counter = 0;
    return counter;
}

inline Term rvv_store_fp16_as_bv(TermManager& tm, Term fp_val) {
    Sort bv16 = tm.mkBitVectorSort(16);
    Term bv = tm.mkConst(bv16, "_rvv_fp16_2bv_" + std::to_string(rvv_fp16_bv_counter()++));
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
    Term fp_from_bv = tm.mkTerm(op, {bv});
    g_ctx->solver->assertFormula(fold_eq(tm, fp_from_bv, fp_val));
    return bv;
}

inline RVVVector rvv_fp16_binop(const RVVVector& a, const RVVVector& b, Kind op, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    bool needs_rm = (op != Kind::FLOATINGPOINT_MAX && op != Kind::FLOATINGPOINT_MIN);
    std::vector<Term> result; result.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp16(tm, a.getElement(i));
        Term b_fp = rvv_load_as_fp16(tm, b.getElement(i));
        Term res_fp = needs_rm ? tm.mkTerm(op, {rm, a_fp, b_fp})
                               : tm.mkTerm(op, {a_fp, b_fp});
        result.push_back(rvv_store_fp16_as_bv(tm, res_fp));
    }
    return RVVVector(tm, 16, result);
}

inline vfloat16m1_t __riscv_vfmin_vv_f16m1(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat16m1_t __riscv_vfmax_vv_f16m1(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_MAX, vl);
}
inline vfloat16m1_t __riscv_vfadd_vv_f16m1(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_ADD, vl);
}
inline vfloat16m1_t __riscv_vfmul_vv_f16m1(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat16m1_t __riscv_vfsub_vv_f16m1(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_SUB, vl);
}
// vlse16 stride=0 broadcast load for f16m1.
inline vfloat16m1_t __riscv_vlse16_v_f16m1(const salt_float16* p, ptrdiff_t stride, size_t vl) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    size_t base = b.ptrToByteOffset(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    if (stride == 0) {
        Term v0 = b.loadScalar(base, 16);
        for (size_t i = 0; i < vl; i++) lanes.push_back(v0);
    } else {
        for (size_t i = 0; i < vl; i++)
            lanes.push_back(b.loadScalar(base + i * (size_t)stride, 16));
    }
    return RVVVector(tm, 16, lanes);
}
inline vfloat16m1_t __riscv_vlse16_v_f16m1(const xnn_float16* p, ptrdiff_t stride, size_t vl) {
    return __riscv_vlse16_v_f16m1(reinterpret_cast<const salt_float16*>(p), stride, vl);
}

// vfmacc: vd = vd + vs1 * vs2 → FMA(vs1, vs2, vd)
inline vfloat16m1_t __riscv_vfmacc_vv_f16m1(const vfloat16m1_t& vd, const vfloat16m1_t& vs1,
                                              const vfloat16m1_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> result; result.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp  = rvv_load_as_fp16(tm, vd.getElement(i));
        Term vs1_fp = rvv_load_as_fp16(tm, vs1.getElement(i));
        Term vs2_fp = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term res_fp = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vs1_fp, vs2_fp, vd_fp});
        result.push_back(rvv_store_fp16_as_bv(tm, res_fp));
    }
    return RVVVector(tm, 16, result);
}

// ===========================================================================
// VLE16 / VSE16 — full vector load/store (FP16 vector)
// ===========================================================================
inline vfloat16m1_t __riscv_vle16_v_f16m1(const salt_float16* ptr, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    return buf.loadRVV(buf.ptrToByteOffset(ptr), vl, 16);
}
inline void __riscv_vse16_v_f16m1(salt_float16* ptr, const vfloat16m1_t& val, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeRVV(buf.ptrToByteOffset(ptr), val);
}
// xnn_float16 thin overloads — kernels that don't pre-cast (e.g. f16-vmulcaddc)
// pass xnn_float16* directly. Layout-compatible with salt_float16 (asserted in salt.hpp).
inline vfloat16m1_t __riscv_vle16_v_f16m1(const xnn_float16* ptr, size_t vl) {
    return __riscv_vle16_v_f16m1(reinterpret_cast<const salt_float16*>(ptr), vl);
}
inline void __riscv_vse16_v_f16m1(xnn_float16* ptr, const vfloat16m1_t& val, size_t vl) {
    __riscv_vse16_v_f16m1(reinterpret_cast<salt_float16*>(ptr), val, vl);
}

// ===========================================================================
// vfloat16m1x3_t tuple type and segmented gather
// ===========================================================================
struct vfloat16m1x3_t {
    vfloat16m1_t val[3];
    vfloat16m1x3_t() = default;
    vfloat16m1x3_t(const vfloat16m1_t& v0, const vfloat16m1_t& v1, const vfloat16m1_t& v2)
        : val{v0, v1, v2} {}
};

inline vfloat16m1_t __riscv_vget_v_f16m1x3_f16m1(const vfloat16m1x3_t& src, size_t index) {
    return src.val[index];
}

// vluxei32 internal — gather elem_bits-wide values from `base + byte_off[i]`,
// returning an OOB-safe symbolic ITE chain over every valid offset (matches
// the bitwuzla tree's rvv_vluxei32_impl).
inline RVVVector rvv_vluxei32_impl(const void* base, const RVVVector& byte_offsets,
                                    size_t vl, size_t elem_bits) {
    auto& tm = g_ctx->tm;
    auto& buf = g_ctx->findBuffer(base);
    size_t base_off = buf.ptrToByteOffset(base);
    size_t elem_bytes = elem_bits / 8;

    if (base_off + elem_bytes > buf.numBytes()) {
        throw std::runtime_error(
            "vluxei32: base pointer leaves no room for a single element");
    }
    size_t max_valid_start = buf.numBytes() - base_off - elem_bytes;

    std::vector<Term> cached(max_valid_start + 1);
    for (size_t k = 0; k <= max_valid_start; k++) {
        cached[k] = buf.loadScalar(base_off + k, elem_bits);
    }

    static thread_local size_t oob_seq = 0;
    size_t call_id = oob_seq++;

    std::vector<Term> result; result.reserve(vl);
    Sort elem_sort = tm.mkBitVectorSort(static_cast<uint32_t>(elem_bits));

    for (size_t i = 0; i < vl; i++) {
        Term sym_off = byte_offsets.getElement(i);
        Term val = tm.mkConst(elem_sort,
            "vlux_oob_" + std::to_string(call_id) + "_" + std::to_string(i));
        for (size_t k = 0; k <= max_valid_start; k++) {
            val = fold_ite(tm, fold_eq(tm, sym_off, mk_bv_val(tm, 32, static_cast<int64_t>(k))),
                 cached[k], val);
        }
        result.push_back(val);
    }
    return RVVVector(tm, elem_bits, result);
}

// vluxseg3ei32: indexed unordered segmented load, nseg=3, EEW=32 indices.
// 3 channels are contiguous in memory, so shifting `base` by `seg` (in
// salt_float16 units = 2 bytes) reuses the scalar gather.
inline vfloat16m1x3_t __riscv_vluxseg3ei32_v_f16m1x3(const salt_float16* base,
                                                      const vuint32m2_t& byte_off,
                                                      size_t vl) {
    RVVVector s0 = rvv_vluxei32_impl(base + 0, byte_off, vl, 16);
    RVVVector s1 = rvv_vluxei32_impl(base + 1, byte_off, vl, 16);
    RVVVector s2 = rvv_vluxei32_impl(base + 2, byte_off, vl, 16);
    return vfloat16m1x3_t(s0, s1, s2);
}

// vmerge_vvm f16m1: mask=1 → b, mask=0 → a.
inline vfloat16m1_t __riscv_vmerge_vvm_f16m1(const vfloat16m1_t& a,
                                               const vfloat16m1_t& b,
                                               const vbool16_t& mask, size_t vl) {
    auto& tm = g_ctx->tm;
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, b.getElement(i), a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}

// ===========================================================================
// PHASE 2 ADDITIONS — full kernels/target/ surface
// ===========================================================================

// ---------------------------------------------------------------------------
// FP32 helpers (BV32 ↔ FP32) — analogous to the FP16 helpers above
// ---------------------------------------------------------------------------
inline Term rvv_load_as_fp32(TermManager& tm, Term bv) {
    auto it = g_fp_bv_cache.find(bv.getId());   // memoized store→load: skip the FP↔BV round-trip
    if (it != g_fp_bv_cache.end()) return it->second;
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
    return tm.mkTerm(op, {bv});
}

inline size_t& rvv_fp32_bv_counter() {
    static size_t counter = 0;
    return counter;
}

inline Term rvv_store_fp32_as_bv(TermManager& tm, Term fp_val) {
    Sort bv32 = tm.mkBitVectorSort(32);
    Term bv = tm.mkConst(bv32, "_rvv_fp32_2bv_" + std::to_string(rvv_fp32_bv_counter()++));
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {8, 24});
    Term fp_from_bv = tm.mkTerm(op, {bv});
    g_ctx->solver->assertFormula(fold_eq(tm, fp_from_bv, fp_val));
    g_fp_bv_cache[bv.getId()] = fp_val;   // so rvv_load_as_fp32(bv) returns fp_val directly
    return bv;
}

// mk_fp32_from_float is defined in neon/intrinsics.hpp; both files
// share salt_cvc5 namespace and salt.hpp includes neon before rvv.

// ---------------------------------------------------------------------------
// Saturation / rounding helpers (translated from bitwuzla tree ~lines 26-117).
// ---------------------------------------------------------------------------
constexpr unsigned __RISCV_VXRM_RNU = 0;
constexpr unsigned __RISCV_VXRM_RNE = 1;
constexpr unsigned __RISCV_VXRM_RDN = 2;
constexpr unsigned __RISCV_VXRM_ROD = 3;

inline Term rounded_shift_right(TermManager& tm, Term val, size_t shift,
                                 size_t bits, unsigned vxrm, bool is_signed) {
    if (shift == 0) return val;

    Term shift_amt = mk_bv_val(tm, bits, static_cast<int64_t>(shift));
    Term shifted = is_signed
        ? tm.mkTerm(Kind::BITVECTOR_ASHR, {val, shift_amt})
        : fold_bvlshr(tm, val, shift_amt);

    if (vxrm == __RISCV_VXRM_RDN) return shifted;

    Op extract_round = tm.mkOp(Kind::BITVECTOR_EXTRACT,
        {static_cast<uint32_t>(shift - 1), static_cast<uint32_t>(shift - 1)});
    Term round_bit = tm.mkTerm(extract_round, {val});
    Op zext_op = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {static_cast<uint32_t>(bits - 1)});
    Term round_ext = tm.mkTerm(zext_op, {round_bit});

    if (vxrm == __RISCV_VXRM_RNU) {
        return fold_bvadd(tm, shifted, round_ext);
    }
    if (vxrm == __RISCV_VXRM_RNE) {
        // RNE: round up iff round_bit=1 AND (lower bits nonzero OR result odd).
        // For shift==1 there are no lower bits, so the OR collapses to result_odd.
        Op extract_bit0 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {0u, 0u});
        Term result_bit0 = tm.mkTerm(extract_bit0, {shifted});
        Term result_odd = fold_eq(tm, result_bit0, mk_bv_val(tm, 1, 1));
        Term tie_breaker;
        if (shift >= 2) {
            Op extract_lower = tm.mkOp(Kind::BITVECTOR_EXTRACT,
                {static_cast<uint32_t>(shift - 2), 0u});
            Term lower = tm.mkTerm(extract_lower, {val});
            Term lower_zero = fold_eq(tm, lower, mk_bv_val(tm, shift - 1, 0));
            tie_breaker = tm.mkTerm(Kind::OR,
                {tm.mkTerm(Kind::NOT, {lower_zero}), result_odd});
        } else {
            tie_breaker = result_odd;
        }
        Term should_round = tm.mkTerm(Kind::AND, {
            fold_eq(tm, round_bit, mk_bv_val(tm, 1, 1)),
            tie_breaker
        });
        Term one = mk_bv_val(tm, bits, 1);
        Term zero = mk_bv_val(tm, bits, 0);
        Term adj = fold_ite(tm, should_round, one, zero);
        return fold_bvadd(tm, shifted, adj);
    }
    if (vxrm == __RISCV_VXRM_ROD) {
        Op extract_trunc = tm.mkOp(Kind::BITVECTOR_EXTRACT,
            {static_cast<uint32_t>(shift - 1), 0u});
        Term truncated = tm.mkTerm(extract_trunc, {val});
        Term trunc_zero = fold_eq(tm, truncated, mk_bv_val(tm, shift, 0));
        Term one = mk_bv_val(tm, bits, 1);
        Term bit0_set = fold_bvor(tm, shifted, one);
        return fold_ite(tm, trunc_zero, shifted, bit0_set);
    }
    return shifted;
}

inline Term signed_clip(TermManager& tm, Term wide_val, size_t wide_bits, size_t narrow_bits) {
    int64_t max_val = (1LL << (narrow_bits - 1)) - 1;
    int64_t min_val = -(1LL << (narrow_bits - 1));
    Term t_max = mk_bv_val(tm, wide_bits, max_val);
    Term t_min = mk_bv_val(tm, wide_bits, min_val);
    Term gt_max = tm.mkTerm(Kind::BITVECTOR_SGT, {wide_val, t_max});
    Term lt_min = tm.mkTerm(Kind::BITVECTOR_SLT, {wide_val, t_min});
    Term clamped = tm.mkTerm(Kind::ITE, {gt_max, t_max,
        fold_ite(tm, lt_min, t_min, wide_val)});
    Op extract_op = tm.mkOp(Kind::BITVECTOR_EXTRACT,
        {static_cast<uint32_t>(narrow_bits - 1), 0u});
    return tm.mkTerm(extract_op, {clamped});
}

inline Term unsigned_clip(TermManager& tm, Term wide_val, size_t wide_bits, size_t narrow_bits) {
    uint64_t max_val = (narrow_bits >= 64) ? ~0ULL : ((1ULL << narrow_bits) - 1);
    Term t_max = mk_bv_val(tm, wide_bits, static_cast<int64_t>(max_val));
    Term t_zero = mk_bv_val(tm, wide_bits, 0);
    Term gt_max = tm.mkTerm(Kind::BITVECTOR_UGT, {wide_val, t_max});
    Term lt_zero = tm.mkTerm(Kind::BITVECTOR_SLT, {wide_val, t_zero});
    Term clamped = tm.mkTerm(Kind::ITE, {gt_max, t_max,
        fold_ite(tm, lt_zero, t_zero, wide_val)});
    Op extract_op = tm.mkOp(Kind::BITVECTOR_EXTRACT,
        {static_cast<uint32_t>(narrow_bits - 1), 0u});
    return tm.mkTerm(extract_op, {clamped});
}

// ---------------------------------------------------------------------------
// VSETVL — additional LMUL variants. All clamp vlmax to ≥1 (see vsetvl_e16m1).
// ---------------------------------------------------------------------------
inline size_t __riscv_vsetvl_e8m2(size_t avl)  { return _rvv_vsetvl(avl,  8, 2); }
inline size_t __riscv_vsetvl_e32m2(size_t avl) { return _rvv_vsetvl(avl, 32, 2); }
inline size_t __riscv_vsetvl_e32m4(size_t avl) { return _rvv_vsetvl(avl, 32, 4); }
inline size_t __riscv_vsetvl_e32m8(size_t avl) { return _rvv_vsetvl(avl, 32, 8); }

// VSETVLMAX — VLMAX queries (no AVL): used by f32-rsum's m8 acc init.
// Same formula as _rvv_vsetvl, but with avl=∞ effectively → returns full VLMAX.
inline size_t __riscv_vsetvlmax_e32m1() { return _rvv_vsetvl(SIZE_MAX, 32, 1); }
inline size_t __riscv_vsetvlmax_e32m4() { return _rvv_vsetvl(SIZE_MAX, 32, 4); }
inline size_t __riscv_vsetvlmax_e32m8() { return _rvv_vsetvl(SIZE_MAX, 32, 8); }

// ---------------------------------------------------------------------------
// Loads / stores — additional widths/LMUL
// ---------------------------------------------------------------------------
inline vint8m2_t __riscv_vle8_v_i8m2(const int8_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p); return b.loadRVV(b.ptrToByteOffset(p), vl, 8);
}
inline vfloat32m4_t __riscv_vle32_v_f32m4(const float* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p); return b.loadRVV(b.ptrToByteOffset(p), vl, 32);
}
inline vfloat32m8_t __riscv_vle32_v_f32m8(const float* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p); return b.loadRVV(b.ptrToByteOffset(p), vl, 32);
}
inline void __riscv_vse8_v_i8m2(int8_t* p, const vint8m2_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p); b.storeRVV(b.ptrToByteOffset(p), v);
}
inline void __riscv_vse32_v_f32m4(float* p, const vfloat32m4_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p); b.storeRVV(b.ptrToByteOffset(p), v);
}
inline void __riscv_vse32_v_f32m8(float* p, const vfloat32m8_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p); b.storeRVV(b.ptrToByteOffset(p), v);
}

// ---------------------------------------------------------------------------
// Reinterpret no-ops (additional variants used by target/ kernels)
// ---------------------------------------------------------------------------
inline RVVVector __riscv_vreinterpret_v_f32m8_i32m8(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_i32m8_f32m8(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_i32m8_u32m8(const RVVVector& a) { return a; }

// ---------------------------------------------------------------------------
// Integer arithmetic — concrete scalar variants (additional widths/LMUL)
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vadd_vv_i32m8(const vint32m8_t& a, const vint32m8_t& b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 32, r);
}
inline vint32m8_t __riscv_vwmul_vv_i32m8(const vint16m4_t& a, const vint16m4_t& b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term be = tm.mkTerm(sext, {b.getElement(i)});
        r.push_back(fold_bvmul(tm, ae, be));
    }
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// VSEXT / VWSUB — sign-extension and widening subtract
// ---------------------------------------------------------------------------
inline vint16m4_t __riscv_vsext_vf2_i16m4(const vint8m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vint32m8_t __riscv_vsext_vf2_i32m8(const vint16m4_t& a, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// VNCLIP — narrowing clip with rounding (signed)
// ---------------------------------------------------------------------------
inline vint16m4_t __riscv_vnclip_wx_i16m4(const vint32m8_t& op1, size_t shift,
                                            unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 32, vxrm, true);
        r.push_back(signed_clip(tm, shifted, 32, 16));
    }
    return RVVVector(tm, 16, r);
}
inline vint8m2_t __riscv_vnclip_wx_i8m2(const vint16m4_t& op1, size_t shift,
                                          unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 16, vxrm, true);
        r.push_back(signed_clip(tm, shifted, 16, 8));
    }
    return RVVVector(tm, 8, r);
}

// ---------------------------------------------------------------------------
// VSSRA — scaling shift-right arithmetic (signed; concrete-shift variant)
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vssra_vx_i32m8(const vint32m8_t& op1, size_t shift,
                                           unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(rounded_shift_right(tm, op1.getElement(i), shift, 32, vxrm, true));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// VMV broadcast — concrete-scalar (additional types/LMUL)
// (Symbolic-scalar overloads with the same names live below.)
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vmv_v_x_i32m8(int32_t v, size_t vl) {
    auto& tm = g_ctx->tm; Term val = mk_bv_val(tm, 32, v);
    return RVVVector(tm, 32, std::vector<Term>(vl, val));
}
inline vint16m4_t __riscv_vmv_v_x_i16m4(int16_t v, size_t vl) {
    auto& tm = g_ctx->tm; Term val = mk_bv_val(tm, 16, v);
    return RVVVector(tm, 16, std::vector<Term>(vl, val));
}

// ---------------------------------------------------------------------------
// VMACC — concrete-scalar multiply-accumulate
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vmacc_vx_i32m8(const vint32m8_t& vd, int32_t rs1,
                                          const vint32m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rs1_bv = mk_bv_val(tm, 32, rs1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term prod = fold_bvmul(tm, rs1_bv, vs2.getElement(i));
        r.push_back(fold_bvadd(tm, vd.getElement(i), prod));
    }
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// VSADD / VRSUB / VSUB — saturating, reverse-subtract, plain (concrete forms)
// (Symbolic-scalar overloads with the same names live below.)
// ---------------------------------------------------------------------------
inline vint16m4_t __riscv_vsadd_vx_i16m4(const vint16m4_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 16, b);
    std::vector<Term> r; r.reserve(vl);
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term be = tm.mkTerm(sext, {bv});
        Term sum = fold_bvadd(tm, ae, be);
        r.push_back(signed_clip(tm, sum, 32, 16));
    }
    return RVVVector(tm, 16, r);
}
inline vint16m4_t __riscv_vrsub_vx_i16m4(const vint16m4_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 16, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsub(tm, bv, a.getElement(i)));
    return RVVVector(tm, 16, r);
}
inline vint16m4_t __riscv_vsub_vx_i16m4(const vint16m4_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 16, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsub(tm, a.getElement(i), bv));
    return RVVVector(tm, 16, r);
}
inline vint16m4_t __riscv_vwsub_vx_i16m4(const vint8m2_t& a, int8_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 8, b);
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    Term be = tm.mkTerm(sext, {bv});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        r.push_back(fold_bvsub(tm, ae, be));
    }
    return RVVVector(tm, 16, r);
}

// ---------------------------------------------------------------------------
// VAND / VSLL / VMUL / VSUB / VADD — additional concrete-scalar variants
// (Symbolic overloads with the same names live below.)
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vmul_vx_i32m8(const vint32m8_t& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvmul(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline vint32m8_t __riscv_vand_vx_i32m8(const vint32m8_t& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvand(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline vint32m8_t __riscv_vadd_vx_i32m8(const vint32m8_t& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
// Shift helpers (concrete shift amounts) — vsll_vx_i16m4 is overloaded by
// SymbolicScalar variant below.
inline vint16m4_t __riscv_vsll_vx_i16m4(const vint16m4_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm; Term sh = mk_bv_val(tm, 16, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 16, r);
}
inline vint32m8_t __riscv_vsll_vx_i32m8(const vint32m8_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm; Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}
inline vuint32m8_t __riscv_vsll_vx_u32m8(const vuint32m8_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm; Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// MAX/MIN signed (additional widths) — concrete-scalar forms
// (Symbolic overloads live below.)
// ---------------------------------------------------------------------------
inline vint8m2_t __riscv_vmax_vx_i8m2(const vint8m2_t& a, int8_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 8, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, cond, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}
inline vint8m2_t __riscv_vmin_vx_i8m2(const vint8m2_t& a, int8_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 8, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getElement(i), bv});
        r.push_back(fold_ite(tm, cond, a.getElement(i), bv));
    }
    return RVVVector(tm, 8, r);
}

// ---------------------------------------------------------------------------
// vmerge_vxm — merge concrete-scalar with mask
// ---------------------------------------------------------------------------
inline RVVVector rvv_vmerge_vxm_impl(const RVVVector& a, int64_t b,
                                      const MaskVector& mask, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, bits, b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, bv, a.getElement(i)));
    }
    return RVVVector(tm, bits, r);
}
inline vint16m4_t __riscv_vmerge_vxm_i16m4(const vint16m4_t& a, int16_t b,
                                             const MaskVector& mask, size_t vl) {
    return rvv_vmerge_vxm_impl(a, b, mask, vl, 16);
}

// vmerge_vvm f32m8: mask=1 → b, mask=0 → a
inline vfloat32m8_t __riscv_vmerge_vvm_f32m8(const vfloat32m8_t& a,
                                               const vfloat32m8_t& b,
                                               const vbool4_t& mask, size_t vl) {
    auto& tm = g_ctx->tm; Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, b.getElement(i), a.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}
// vmv_v_x_u32m8: broadcast scalar to all vl lanes of a u32m8 vector.
inline vuint32m8_t __riscv_vmv_v_x_u32m8(uint32_t s, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sv = mk_bv_val(tm, 32, (int64_t)(uint64_t)s);
    std::vector<Term> r(vl, sv);
    return RVVVector(tm, 32, r);
}
// vmerge_vxm u32m8: mask=1 → scalar s, mask=0 → a[i].
inline vuint32m8_t __riscv_vmerge_vxm_u32m8(const vuint32m8_t& a, uint32_t s,
                                             const vbool4_t& mask, size_t vl) {
    auto& tm = g_ctx->tm; Term one = mk_bv_val(tm, 1, 1);
    Term sv  = mk_bv_val(tm, 32, (int64_t)(uint64_t)s);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, sv, a.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}
// vmfgt_vv f32m8 → b4: lane-wise FP greater-than producing a bit mask.
inline vbool4_t __riscv_vmfgt_vv_f32m8_b4(const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        Term bf = rvv_load_as_fp32(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {af, bf});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
// vse32_v_u32m8: store vl lanes of u32m8 to memory.
inline void __riscv_vse32_v_u32m8(uint32_t* p, const vuint32m8_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    for (size_t i = 0; i < vl; i++) {
        b.storeScalar(b.ptrToByteOffset(p) + i * 4, v.getElement(i), 32);
    }
}

// ---------------------------------------------------------------------------
// VLUXEI — indexed (gather) load — additional EEW=32 / SEW=32 variant
// ---------------------------------------------------------------------------
inline vint32m8_t __riscv_vluxei32_v_i32m8(const int32_t* base,
                                             const vuint32m8_t& off, size_t vl) {
    return rvv_vluxei32_impl(base, off, vl, 32);
}

// Masked indexed (gather) load, f32m1.  Masked-off lanes take the maskedoff
// (merge) operand.  Reuses the scalar gather; for vid-derived (concrete)
// byte offsets the per-lane ITE chain collapses to a direct load.
inline vfloat32m1_t __riscv_vluxei32_v_f32m1_m(const vbool32_t& mask,
                                                const vfloat32m1_t& maskedoff,
                                                const float* base,
                                                const vuint32m1_t& off, size_t vl) {
    auto& tm = g_ctx->tm;
    RVVVector gathered = rvv_vluxei32_impl(base, off, vl, 32);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, cond, gathered.getElement(i), maskedoff.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// FP32 vector arithmetic (vv, vf)
// ---------------------------------------------------------------------------
inline RVVVector rvv_fp32_binop(const RVVVector& a, const RVVVector& b, Kind op, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    bool needs_rm = (op != Kind::FLOATINGPOINT_MAX && op != Kind::FLOATINGPOINT_MIN);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp32(tm, a.getElement(i));
        Term b_fp = rvv_load_as_fp32(tm, b.getElement(i));
        Term res_fp = needs_rm ? tm.mkTerm(op, {rm, a_fp, b_fp})
                               : tm.mkTerm(op, {a_fp, b_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res_fp));
    }
    return RVVVector(tm, 32, r);
}
inline RVVVector rvv_fp32_binop_vf(const RVVVector& a, Term b_fp, Kind op, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    bool needs_rm = (op != Kind::FLOATINGPOINT_MAX && op != Kind::FLOATINGPOINT_MIN);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp32(tm, a.getElement(i));
        Term res_fp = needs_rm ? tm.mkTerm(op, {rm, a_fp, b_fp})
                               : tm.mkTerm(op, {a_fp, b_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res_fp));
    }
    return RVVVector(tm, 32, r);
}

inline vfloat32m4_t __riscv_vfadd_vv_f32m4(const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_ADD,vl); }
inline vfloat32m8_t __riscv_vfadd_vv_f32m8(const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_ADD,vl); }
inline vfloat32m4_t __riscv_vfsub_vv_f32m4(const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_SUB,vl); }
inline vfloat32m8_t __riscv_vfsub_vv_f32m8(const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_SUB,vl); }
inline vfloat32m4_t __riscv_vfmul_vv_f32m4(const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_MULT,vl); }
inline vfloat32m8_t __riscv_vfmul_vv_f32m8(const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_MULT,vl); }
inline vfloat32m8_t __riscv_vfdiv_vv_f32m8(const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) { return rvv_fp32_binop(a,b,Kind::FLOATINGPOINT_DIV,vl); }

// concrete-float vf forms (used by harnesses passing literal floats).
// __riscv_vfadd_vf_f32m8 / __riscv_vfsub_vf_f32m8 / __riscv_vfmul_vf_f32m8
// also have SymbolicScalar<float> overloads below for symbolic params.
inline vfloat32m8_t __riscv_vfadd_vf_f32m8(const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_ADD, vl);
}
inline vfloat32m8_t __riscv_vfsub_vf_f32m8(const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_SUB, vl);
}
inline vfloat32m8_t __riscv_vfmul_vf_f32m8(const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat32m4_t __riscv_vfmin_vf_f32m4(const vfloat32m4_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat32m4_t __riscv_vfmax_vf_f32m4(const vfloat32m4_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_MAX, vl);
}
inline vfloat32m8_t __riscv_vfmin_vf_f32m8(const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat32m8_t __riscv_vfmax_vf_f32m8(const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b), Kind::FLOATINGPOINT_MAX, vl);
}

// FP16 scalar min/max (vf forms used by f16-vmulcaddc)
inline RVVVector rvv_fp16_binop_vf_term(const RVVVector& a, Term b_fp, Kind op, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    bool needs_rm = (op != Kind::FLOATINGPOINT_MAX && op != Kind::FLOATINGPOINT_MIN);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp16(tm, a.getElement(i));
        Term res_fp = needs_rm ? tm.mkTerm(op, {rm, a_fp, b_fp})
                               : tm.mkTerm(op, {a_fp, b_fp});
        r.push_back(rvv_store_fp16_as_bv(tm, res_fp));
    }
    return RVVVector(tm, 16, r);
}
inline vfloat16m1_t __riscv_vfmin_vf_f16m1(const vfloat16m1_t& a, salt_float16 b, size_t vl) {
    auto& tm = g_ctx->tm;
    return rvv_fp16_binop_vf_term(a, mk_fp16_from_f16(tm, b), Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat16m1_t __riscv_vfmax_vf_f16m1(const vfloat16m1_t& a, salt_float16 b, size_t vl) {
    auto& tm = g_ctx->tm;
    return rvv_fp16_binop_vf_term(a, mk_fp16_from_f16(tm, b), Kind::FLOATINGPOINT_MAX, vl);
}

// ---------------------------------------------------------------------------
// FP FMA: vfmacc (vd = vd + vs1 * vs2), vfmadd (vd = vd * vs1 + vs2)
// ---------------------------------------------------------------------------
inline vfloat32m8_t __riscv_vfmacc_vv_f32m8(const vfloat32m8_t& vd,
                                              const vfloat32m8_t& vs1,
                                              const vfloat32m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v1 = rvv_load_as_fp32(tm, vs1.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, v1, v2, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m8_t __riscv_vfmacc_vf_f32m8(const vfloat32m8_t& vd, float rs1,
                                              const vfloat32m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term rs1_fp = mk_fp32_from_float(tm, rs1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, rs1_fp, v2, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m4_t __riscv_vfmadd_vv_f32m4(const vfloat32m4_t& vd,
                                              const vfloat32m4_t& vs1,
                                              const vfloat32m4_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v1 = rvv_load_as_fp32(tm, vs1.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vd_fp, v1, v2});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}

// FP16 vfmadd (vd = vd * vs1 + vs2) — used by f16-vmulcaddc
inline vfloat16m1_t __riscv_vfmadd_vv_f16m1(const vfloat16m1_t& vd,
                                              const vfloat16m1_t& vs1,
                                              const vfloat16m1_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp16(tm, vd.getElement(i));
        Term v1 = rvv_load_as_fp16(tm, vs1.getElement(i));
        Term v2 = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vd_fp, v1, v2});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}

// ---------------------------------------------------------------------------
// FP broadcast scalar → vector (concrete-float; symbolic overload below)
// ---------------------------------------------------------------------------
inline vfloat32m8_t __riscv_vfmv_v_f_f32m8(float src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, src));
    return RVVVector(tm, 32, std::vector<Term>(vl, bv));
}

// ---------------------------------------------------------------------------
// FP conversions: int32 → float32 and vice versa
// ---------------------------------------------------------------------------
inline vfloat32m8_t __riscv_vfcvt_f_x_v_f32m8(const vint32m8_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_SBV, {8, 24});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(rvv_store_fp32_as_bv(tm, tm.mkTerm(cvt, {rm, a.getElement(i)})));
    return RVVVector(tm, 32, r);
}
inline vint32m8_t __riscv_vfcvt_x_f_v_i32m8(const vfloat32m8_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_SBV, {32});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(cvt, {rm, rvv_load_as_fp32(tm, a.getElement(i))}));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// FP compare (mask producing) — concrete-scalar form (symbolic overload below)
// ---------------------------------------------------------------------------
inline MaskVector __riscv_vmflt_vf_f32m8_b4(const vfloat32m8_t& a, float b, size_t vl) {
    auto& tm = g_ctx->tm; Term b_fp = mk_fp32_from_float(tm, b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp32(tm, a.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {a_fp, b_fp});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// ---------------------------------------------------------------------------
// Integer compare (vmslt against int16, b4 mask) — concrete form (symbolic below)
// ---------------------------------------------------------------------------
inline MaskVector __riscv_vmslt_vx_i16m4_b4(const vint16m4_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 16, b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getElement(i), bv});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmslt_vx_i32m8_b4(const vint32m8_t& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, 32, b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getElement(i), bv});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// ===========================================================================
// SymbolicScalar overloads — for kernels that have symbolic scalar parameters
// (qs8-vaddc, f32-velu, f32-vapproxgelu, etc.).  These mirror the bitwuzla
// tree's symbolic-scalar overloads ~lines 2697-3260.
// ===========================================================================

// --- helpers for symbolic shift over integer types ---
inline Term rounded_shift_right_symbolic(TermManager& tm, Term val, Term shift_term,
                                          size_t bits, unsigned vxrm, bool is_signed) {
    Term result = val;
    for (size_t s = 31; s >= 1; s--) {
        Term concrete_shifted = rounded_shift_right(tm, val, s, bits, vxrm, is_signed);
        Term eq = fold_eq(tm, shift_term, mk_bv_val(tm, bits, static_cast<int64_t>(s)));
        result = fold_ite(tm, eq, concrete_shifted, result);
    }
    return result;
}

// --- generic BV vx helper ---
inline RVVVector rvv_sym_bv_binop_vx(const RVVVector& a, Term b, Kind op, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(op, {a.getElement(i), b}));
    return RVVVector(tm, bits, r);
}
inline RVVVector rvv_sym_bv_rsub_vx(const RVVVector& a, Term b, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsub(tm, b, a.getElement(i)));
    return RVVVector(tm, bits, r);
}

// --- vadd_vx / vsub_vx / vmul_vx / vand_vx (symbolic) ---
inline vint32m8_t __riscv_vadd_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) { return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_ADD, vl, 32); }
inline vint32m8_t __riscv_vsub_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) { return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_SUB, vl, 32); }
inline vint32m8_t __riscv_vmul_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) { return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_MULT, vl, 32); }
inline vint32m8_t __riscv_vand_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) { return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_AND, vl, 32); }
inline vuint16m4_t __riscv_vadd_vx_u16m4(const vuint16m4_t& a, SymbolicScalar<uint16_t> b, size_t vl) { return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_ADD, vl, 16); }

// --- vrsub_vx (symbolic) ---
inline vint16m4_t __riscv_vrsub_vx_i16m4(const vint16m4_t& a, SymbolicScalar<int16_t> b, size_t vl) { return rvv_sym_bv_rsub_vx(a, b.term(), vl, 16); }

// --- vsadd_vx (symbolic) ---
inline vint16m4_t __riscv_vsadd_vx_i16m4(const vint16m4_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Term be = tm.mkTerm(sext, {b.term()});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term sum = fold_bvadd(tm, ae, be);
        r.push_back(signed_clip(tm, sum, 32, 16));
    }
    return RVVVector(tm, 16, r);
}

// --- vmv_v_x (symbolic) ---
inline vint32m8_t __riscv_vmv_v_x_i32m8(SymbolicScalar<int32_t> v, size_t vl) {
    return RVVVector(g_ctx->tm, 32, std::vector<Term>(vl, v.term()));
}
inline vint16m4_t __riscv_vmv_v_x_i16m4(SymbolicScalar<int16_t> v, size_t vl) {
    return RVVVector(g_ctx->tm, 16, std::vector<Term>(vl, v.term()));
}
inline vuint16m1_t __riscv_vmv_v_x_u16m1(SymbolicScalar<uint16_t> v, size_t vl) {
    return RVVVector(g_ctx->tm, 16, std::vector<Term>(vl, v.term()));
}

// --- vmacc_vx (symbolic) ---
inline vint32m8_t __riscv_vmacc_vx_i32m8(const vint32m8_t& vd, SymbolicScalar<int32_t> rs1,
                                           const vint32m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term prod = fold_bvmul(tm, rs1.term(), vs2.getElement(i));
        r.push_back(fold_bvadd(tm, vd.getElement(i), prod));
    }
    return RVVVector(tm, 32, r);
}

// --- vssra_vx (symbolic shift via ITE cascade) ---
// Truncate/zero-extend any-width shift Term to a 32-bit BV (matches bitwuzla's _shift_to_32).
inline Term _shift_to_32(TermManager& tm, Term t, size_t src_bits) {
    if (src_bits > 32)
        return tm.mkTerm(tm.mkOp(Kind::BITVECTOR_EXTRACT, {31, 0}), {t});
    if (src_bits < 32)
        return tm.mkTerm(tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {(uint32_t)(32 - src_bits)}), {t});
    return t;
}
inline vint32m8_t __riscv_vssra_vx_i32m8(const vint32m8_t& op1,
                                           SymbolicScalar<int32_t> shift,
                                           unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(rounded_shift_right_symbolic(tm, op1.getElement(i), shift.term(), 32, vxrm, true));
    return RVVVector(tm, 32, r);
}
// size_t (uint64) overloads — truncate shift to 32 bits, delegate.
inline vint32m8_t __riscv_vssra_vx_i32m8(const vint32m8_t& op1,
                                           SymbolicScalar<size_t> shift,
                                           unsigned vxrm, size_t vl) {
    Term s32 = _shift_to_32(g_ctx->tm, shift.term(), 64);
    return __riscv_vssra_vx_i32m8(op1, SymbolicScalar<int32_t>(s32), vxrm, vl);
}

// --- vmax_vx / vmin_vx (symbolic int32) ---
inline vint32m8_t __riscv_vmax_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), b.term()});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.term()));
    }
    return RVVVector(tm, 32, r);
}
inline vint32m8_t __riscv_vmin_vx_i32m8(const vint32m8_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getElement(i), b.term()});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.term()));
    }
    return RVVVector(tm, 32, r);
}

// --- vmax_vx / vmin_vx (symbolic int8) ---
inline vint8m2_t __riscv_vmax_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int8_t> b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SGE, {a.getElement(i), b.term()});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.term()));
    }
    return RVVVector(tm, 8, r);
}
inline vint8m2_t __riscv_vmin_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int8_t> b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term c = tm.mkTerm(Kind::BITVECTOR_SLE, {a.getElement(i), b.term()});
        r.push_back(fold_ite(tm, c, a.getElement(i), b.term()));
    }
    return RVVVector(tm, 8, r);
}

// --- vsll_vx (symbolic) ---
inline vint16m4_t __riscv_vsll_vx_i16m4(const vint16m4_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    return rvv_sym_bv_binop_vx(a, b.term(), Kind::BITVECTOR_SHL, vl, 16);
}
// Note: __riscv_vsll_vx_i32m2 with size_t shift already exists at the top of
// this file; SymbolicScalar overload available via the template below if needed.

// --- vwsub_vx (symbolic, int8 → int16) ---
inline vint16m4_t __riscv_vwsub_vx_i16m4(const vint8m2_t& op1, SymbolicScalar<int8_t> op2, size_t vl) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    Term op2_ext = tm.mkTerm(sext, {op2.term()});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_ext = tm.mkTerm(sext, {op1.getElement(i)});
        r.push_back(fold_bvsub(tm, a_ext, op2_ext));
    }
    return RVVVector(tm, 16, r);
}

// --- vwmul_vx (symbolic, int16 → int32) ---
inline vint32m8_t __riscv_vwmul_vx_i32m8(const vint16m4_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Term be = tm.mkTerm(sext, {b.term()});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        r.push_back(fold_bvmul(tm, ae, be));
    }
    return RVVVector(tm, 32, r);
}

// --- vmslt_vx i16m4 b4 (symbolic) ---
inline MaskVector __riscv_vmslt_vx_i16m4_b4(const vint16m4_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_SLT, {a.getElement(i), b.term()});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// --- vmerge_vxm i16m4 (symbolic) ---
inline vint16m4_t __riscv_vmerge_vxm_i16m4(const vint16m4_t& a, SymbolicScalar<int16_t> b,
                                             const MaskVector& mask, size_t vl) {
    auto& tm = g_ctx->tm; Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, b.term(), a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}

// --- FP32 vf (symbolic float) helpers ---
inline RVVVector rvv_sym_fp32_binop_vf(const RVVVector& a, Term b_fp, Kind op, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    bool needs_rm = (op != Kind::FLOATINGPOINT_MAX && op != Kind::FLOATINGPOINT_MIN);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp32(tm, a.getElement(i));
        Term res = needs_rm ? tm.mkTerm(op, {rm, a_fp, b_fp})
                            : tm.mkTerm(op, {a_fp, b_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}

inline vfloat32m8_t __riscv_vfadd_vf_f32m8(const vfloat32m8_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_ADD, vl); }
inline vfloat32m8_t __riscv_vfsub_vf_f32m8(const vfloat32m8_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_SUB, vl); }
inline vfloat32m4_t __riscv_vfsub_vf_f32m4(const vfloat32m4_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_SUB, vl); }  // raddstoreexpminusmax (u4v): vx = vi - *max (symbolic broadcast)
inline vfloat32m2_t __riscv_vfsub_vf_f32m2(const vfloat32m2_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_SUB, vl); }  // u2v variant
inline vfloat32m8_t __riscv_vfmul_vf_f32m8(const vfloat32m8_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_MULT, vl); }

inline vfloat32m4_t __riscv_vfmin_vf_f32m4(const vfloat32m4_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_MIN, vl); }
inline vfloat32m4_t __riscv_vfmax_vf_f32m4(const vfloat32m4_t& a, SymbolicScalar<float> b, size_t vl) { return rvv_sym_fp32_binop_vf(a, b.term(), Kind::FLOATINGPOINT_MAX, vl); }

// --- vfmacc_vf (symbolic) ---
inline vfloat32m8_t __riscv_vfmacc_vf_f32m8(const vfloat32m8_t& vd, SymbolicScalar<float> rs1,
                                              const vfloat32m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, rs1.term(), v2, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}

// --- vfmv_v_f (symbolic) ---
inline vfloat32m8_t __riscv_vfmv_v_f_f32m8(SymbolicScalar<float> src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, src.term());
    return RVVVector(tm, 32, std::vector<Term>(vl, bv));
}

// --- vmflt_vf (symbolic FP compare) ---
inline MaskVector __riscv_vmflt_vf_f32m8_b4(const vfloat32m8_t& a, SymbolicScalar<float> b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term a_fp = rvv_load_as_fp32(tm, a.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {a_fp, b.term()});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// ---------------------------------------------------------------------------
// Widening cast overloads — accept wider symbolic types and truncate.
// (Mirrors the bitwuzla tree's widening-cast section ~lines 3225-3260.)
// ---------------------------------------------------------------------------
inline vint16m4_t __riscv_vmv_v_x_i16m4(SymbolicScalar<int32_t> v, size_t vl) {
    return __riscv_vmv_v_x_i16m4(v.cast<int16_t>(), vl);
}
inline vint16m4_t __riscv_vrsub_vx_i16m4(const vint16m4_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vrsub_vx_i16m4(a, b.cast<int16_t>(), vl);
}
inline vint16m4_t __riscv_vmerge_vxm_i16m4(const vint16m4_t& a, SymbolicScalar<int32_t> b,
                                             const MaskVector& mask, size_t vl) {
    return __riscv_vmerge_vxm_i16m4(a, b.cast<int16_t>(), mask, vl);
}
inline vint16m4_t __riscv_vsadd_vx_i16m4(const vint16m4_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vsadd_vx_i16m4(a, b.cast<int16_t>(), vl);
}
inline vint8m2_t __riscv_vmax_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vmax_vx_i8m2(a, b.cast<int8_t>(), vl);
}
inline vint8m2_t __riscv_vmax_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    return __riscv_vmax_vx_i8m2(a, b.cast<int8_t>(), vl);
}
inline vint8m2_t __riscv_vmin_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vmin_vx_i8m2(a, b.cast<int8_t>(), vl);
}
inline vint8m2_t __riscv_vmin_vx_i8m2(const vint8m2_t& a, SymbolicScalar<int16_t> b, size_t vl) {
    return __riscv_vmin_vx_i8m2(a, b.cast<int8_t>(), vl);
}
inline MaskVector __riscv_vmslt_vx_i16m4_b4(const vint16m4_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vmslt_vx_i16m4_b4(a, b.cast<int16_t>(), vl);
}
inline vint16m4_t __riscv_vwsub_vx_i16m4(const vint8m2_t& a, SymbolicScalar<int32_t> b, size_t vl) {
    return __riscv_vwsub_vx_i16m4(a, b.cast<int8_t>(), vl);
}

// ===========================================================================
// f16m8 (LMUL=8) ops needed by f16-vexp and similar wide-FP16 kernels.
// All vfloat16m*/vuint16m* aliases are the same RVVVector — these wrappers
// just delegate to the existing element-wise helpers with the caller's vl.
// ===========================================================================
using vuint16m8_t = RVVVector;
using vuint16m1_t = RVVVector;
using vuint16m2_t = RVVVector;
using vuint16m4_t = RVVVector;

inline size_t __riscv_vsetvl_e16m8(size_t avl) {
    return _rvv_vsetvl(avl, 16, 8);
}

inline vfloat16m8_t __riscv_vfmv_v_f_f16m8(salt_float16 src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp16_as_bv(tm, mk_fp16_from_f16(tm, src));
    return RVVVector(tm, 16, std::vector<Term>(vl, bv));
}

inline vfloat16m8_t __riscv_vfadd_vv_f16m8(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_ADD, vl);
}
inline vfloat16m8_t __riscv_vfsub_vv_f16m8(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_SUB, vl);
}
inline vfloat16m8_t __riscv_vfmul_vv_f16m8(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat16m8_t __riscv_vfmul_vf_f16m8(const vfloat16m8_t& a, salt_float16 b, size_t vl) {
    auto& tm = g_ctx->tm;
    return rvv_fp16_binop_vf_term(a, mk_fp16_from_f16(tm, b), Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat16m8_t __riscv_vfmin_vf_f16m8(const vfloat16m8_t& a, salt_float16 b, size_t vl) {
    auto& tm = g_ctx->tm;
    return rvv_fp16_binop_vf_term(a, mk_fp16_from_f16(tm, b), Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat16m8_t __riscv_vfmax_vf_f16m8(const vfloat16m8_t& a, salt_float16 b, size_t vl) {
    auto& tm = g_ctx->tm;
    return rvv_fp16_binop_vf_term(a, mk_fp16_from_f16(tm, b), Kind::FLOATINGPOINT_MAX, vl);
}

// vfmacc: vd = vd + vs1 * vs2 → FMA(vs1, vs2, vd)
inline vfloat16m8_t __riscv_vfmacc_vv_f16m8(const vfloat16m8_t& vd, const vfloat16m8_t& vs1,
                                              const vfloat16m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp  = rvv_load_as_fp16(tm, vd.getElement(i));
        Term vs1_fp = rvv_load_as_fp16(tm, vs1.getElement(i));
        Term vs2_fp = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term res    = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vs1_fp, vs2_fp, vd_fp});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}
inline vfloat16m8_t __riscv_vfmacc_vf_f16m8(const vfloat16m8_t& vd, salt_float16 vs1,
                                              const vfloat16m8_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term vs1_fp = mk_fp16_from_f16(tm, vs1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp  = rvv_load_as_fp16(tm, vd.getElement(i));
        Term vs2_fp = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term res    = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vs1_fp, vs2_fp, vd_fp});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}

// Memory ops — m8 mirrors of the m1 versions.
inline vfloat16m8_t __riscv_vle16_v_f16m8(const salt_float16* ptr, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    return buf.loadRVV(buf.ptrToByteOffset(ptr), vl, 16);
}
inline void __riscv_vse16_v_f16m8(salt_float16* ptr, const vfloat16m8_t& val, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeRVV(buf.ptrToByteOffset(ptr), val);
}
inline vfloat16m8_t __riscv_vle16_v_f16m8(const xnn_float16* ptr, size_t vl) {
    return __riscv_vle16_v_f16m8(reinterpret_cast<const salt_float16*>(ptr), vl);
}
inline void __riscv_vse16_v_f16m8(xnn_float16* ptr, const vfloat16m8_t& val, size_t vl) {
    __riscv_vse16_v_f16m8(reinterpret_cast<salt_float16*>(ptr), val, vl);
}

// Reinterpret f16 ↔ u16 — RVVVector is type-erased, so these are no-ops.
inline RVVVector __riscv_vreinterpret_v_u16m8_f16m8(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_f16m8_u16m8(const RVVVector& a) { return a; }

// uint16 immediate left shift, lane-wise.
inline vuint16m8_t __riscv_vsll_vx_u16m8(const vuint16m8_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 16, (uint64_t)shift);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    }
    return RVVVector(tm, 16, r);
}

// ===========================================================================
// f16m4 (LMUL=4) ops needed by f16-vsigmoid and similar mid-LMUL kernels.
// ===========================================================================
inline size_t __riscv_vsetvl_e16m4(size_t avl) {
    return _rvv_vsetvl(avl, 16, 4);
}
inline size_t __riscv_vsetvlmax_e16m4() {
    return g_ctx->vlen / 16 * 4;
}

inline vuint16m4_t __riscv_vmv_v_x_u16m4(uint16_t v, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (uint64_t)v);
    return RVVVector(tm, 16, std::vector<Term>(vl, bv));
}
inline vfloat16m4_t __riscv_vmv_v_v_f16m4(const vfloat16m4_t& src, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(src.getElement(i));
    return RVVVector(tm, 16, r);
}
inline vfloat32m4_t __riscv_vmv_v_v_f32m4(const vfloat32m4_t& src, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(src.getElement(i));
    return RVVVector(tm, 32, r);
}

// uint16 load/store at m4.
inline vuint16m4_t __riscv_vle16_v_u16m4(const uint16_t* ptr, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    return buf.loadRVV(buf.ptrToByteOffset(ptr), vl, 16);
}
inline void __riscv_vse16_v_u16m4(uint16_t* ptr, const vuint16m4_t& val, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeRVV(buf.ptrToByteOffset(ptr), val);
}

// FP abs — clears sign bit.
inline vfloat16m4_t __riscv_vfabs_v_f16m4(const vfloat16m4_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}

inline vfloat16m4_t __riscv_vfadd_vv_f16m4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_ADD, vl);
}
inline vfloat16m4_t __riscv_vfsub_vv_f16m4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_SUB, vl);
}
inline vfloat16m4_t __riscv_vfmul_vv_f16m4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat16m4_t __riscv_vfdiv_vv_f16m4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_DIV, vl);
}
inline vfloat16m4_t __riscv_vfmacc_vv_f16m4(const vfloat16m4_t& vd, const vfloat16m4_t& vs1,
                                              const vfloat16m4_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp  = rvv_load_as_fp16(tm, vd.getElement(i));
        Term vs1_fp = rvv_load_as_fp16(tm, vs1.getElement(i));
        Term vs2_fp = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term res    = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, vs1_fp, vs2_fp, vd_fp});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}

// FP compare → b4 mask.
inline vbool4_t __riscv_vmfgt_vv_f16m4_b4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {af, bf});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline vbool4_t __riscv_vmflt_vv_f16m4_b4(const vfloat16m4_t& a, const vfloat16m4_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {af, bf});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// vmerge: mask=1 → b, mask=0 → a.  Vector-vector and vector-scalar forms.
inline vfloat16m4_t __riscv_vmerge_vvm_f16m4(const vfloat16m4_t& a, const vfloat16m4_t& b,
                                               const vbool4_t& mask, size_t vl) {
    auto& tm = g_ctx->tm; Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, b.getElement(i), a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}
inline vuint16m4_t __riscv_vmerge_vxm_u16m4(const vuint16m4_t& a, uint16_t b,
                                              const vbool4_t& mask, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (uint64_t)b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, bv, a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}

// Reinterprets — RVVVector is type-erased, all no-ops.
inline RVVVector __riscv_vreinterpret_v_f16m4_i16m4(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_i16m4_f16m4(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_f16m4_u16m4(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_u16m4_f16m4(const RVVVector& a) { return a; }

// ===========================================================================
// f16m8 (LMUL=8) ops — mirror of the m4 batch above.  Mask ratio for e16m8
// is SEW/LMUL = 16/8 = 2, so masks use vbool2_t.
// ===========================================================================
using vbool2_t = MaskVector;

inline size_t __riscv_vsetvlmax_e16m8() {
    return g_ctx->vlen / 16 * 8;
}

inline vuint16m8_t __riscv_vmv_v_x_u16m8(uint16_t v, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (uint64_t)v);
    return RVVVector(tm, 16, std::vector<Term>(vl, bv));
}
inline vfloat16m8_t __riscv_vmv_v_v_f16m8(const vfloat16m8_t& src, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(src.getElement(i));
    return RVVVector(tm, 16, r);
}

inline vuint16m8_t __riscv_vle16_v_u16m8(const uint16_t* ptr, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    return buf.loadRVV(buf.ptrToByteOffset(ptr), vl, 16);
}
inline void __riscv_vse16_v_u16m8(uint16_t* ptr, const vuint16m8_t& val, size_t vl) {
    auto& buf = g_ctx->findBuffer(ptr);
    buf.storeRVV(buf.ptrToByteOffset(ptr), val);
}

inline vfloat16m8_t __riscv_vfabs_v_f16m8(const vfloat16m8_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_ABS, {af});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}
inline vfloat16m8_t __riscv_vfdiv_vv_f16m8(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    return rvv_fp16_binop(a, b, Kind::FLOATINGPOINT_DIV, vl);
}

inline vbool2_t __riscv_vmfgt_vv_f16m8_b2(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_GT, {af, bf});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline vbool2_t __riscv_vmflt_vv_f16m8_b2(const vfloat16m8_t& a, const vfloat16m8_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_LT, {af, bf});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

inline vfloat16m8_t __riscv_vmerge_vvm_f16m8(const vfloat16m8_t& a, const vfloat16m8_t& b,
                                               const vbool2_t& mask, size_t vl) {
    auto& tm = g_ctx->tm; Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, b.getElement(i), a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}
inline vuint16m8_t __riscv_vmerge_vxm_u16m8(const vuint16m8_t& a, uint16_t b,
                                              const vbool2_t& mask, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (uint64_t)b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, bv, a.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}

// int16 immediate left shift (arithmetic shift on signed view = logical on bits).
inline vint16m8_t __riscv_vsll_vx_i16m8(const vint16m8_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 16, (uint64_t)shift);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    }
    return RVVVector(tm, 16, r);
}

inline RVVVector __riscv_vreinterpret_v_f16m8_i16m8(const RVVVector& a) { return a; }
inline RVVVector __riscv_vreinterpret_v_i16m8_f16m8(const RVVVector& a) { return a; }

// ---------------------------------------------------------------------------
// uint8 m8 RVV intrinsics — used by x8-lut.
// ---------------------------------------------------------------------------
using vuint8m8_t = RVVVector;

inline size_t __riscv_vsetvl_e8m8(size_t avl) {
    return _rvv_vsetvl(avl, 8, 8);
}

inline vuint8m8_t __riscv_vle8_v_u8m8(const uint8_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 8);
}

inline void __riscv_vse8_v_u8m8(uint8_t* p, const vuint8m8_t& v, size_t /*vl*/) {
    auto& b = g_ctx->findBuffer(p);
    b.storeRVV(b.ptrToByteOffset(p), v);
}

// VRGATHER — table lookup by symbolic indices.
inline RVVVector rvv_vrgather_vv_impl(const RVVVector& src, const RVVVector& idx,
                                       size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    Term zero = mk_bv_val(tm, bits, 0);
    size_t idx_bits = idx.elemBits();
    std::vector<Term> r;
    r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term result = zero;
        for (size_t j = src.getVL(); j > 0; j--) {
            Term cmp = fold_eq(tm, idx.getElement(i), mk_bv_val(tm, idx_bits, j - 1));
            result = fold_ite(tm, cmp, src.getElement(j - 1), result);
        }
        r.push_back(result);
    }
    return RVVVector(tm, bits, r);
}

inline vuint8m8_t __riscv_vrgather_vv_u8m8(const vuint8m8_t& s,
                                            const vuint8m8_t& i, size_t vl) {
    return rvv_vrgather_vv_impl(s, i, vl, 8);
}

// ---------------------------------------------------------------------------
// f16-qs8-vcvt support: m8 NaN mask, FP→i16 with rounding mode,
// i16m8 saturating add / merge, i16m8 → i8m4 narrowing clip.
// ---------------------------------------------------------------------------

// FRM (FP rounding mode) constants — RISC-V encoding.
// Consumed by intrinsics with the `_rm` suffix (e.g. vfcvt_x_f_v_*_rm) via
// rm_term_from_frm() in core/fp_convert.hpp. DYN (frm=7) and reserved
// encodings throw — kernels using DYN must read fcsr first.
constexpr unsigned __RISCV_FRM_RNE = 0;  // round to nearest, ties to even
constexpr unsigned __RISCV_FRM_RTZ = 1;
constexpr unsigned __RISCV_FRM_RDN = 2;
constexpr unsigned __RISCV_FRM_RUP = 3;
constexpr unsigned __RISCV_FRM_RMM = 4;

inline vbool2_t __riscv_vmfne_vv_f16m8_b2(const vfloat16m8_t& a,
                                           const vfloat16m8_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        // FP NEQ: !(a == b). Returns true for NaN inputs since NaN != NaN.
        Term eq = tm.mkTerm(Kind::FLOATINGPOINT_EQ, {af, bf});
        Term ne = tm.mkTerm(Kind::NOT, {eq});
        bits.push_back(fold_ite(tm, ne, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

inline vint16m8_t __riscv_vfcvt_x_f_v_i16m8_rm(const vfloat16m8_t& a,
                                                unsigned frm, size_t vl) {
    // RVV vfcvt.x.f.v: NaN→INT_MAX, ±inf/finite-OOR saturate.
    // rm taken from frm arg (RVV per-instruction rounding mode).
    auto& tm = g_ctx->tm;
    Term rm = rm_term_from_frm(tm, frm);
    Term nan_result = mk_bv_val(tm, 16, INT16_MAX);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term fp = rvv_load_as_fp16(tm, a.getElement(i));
        r.push_back(fp_to_int_lane(tm, fp, /*eb=*/5, /*sb=*/11,
                                   /*dst_bits=*/16, /*is_signed=*/true,
                                   rm, nan_result));
    }
    return RVVVector(tm, 16, r);
}

inline vint16m8_t __riscv_vmerge_vxm_i16m8(const vint16m8_t& a, int16_t b,
                                            const vbool2_t& mask, size_t vl) {
    return rvv_vmerge_vxm_impl(a, (int64_t)b, mask, vl, 16);
}

inline vint16m8_t __riscv_vsadd_vx_i16m8(const vint16m8_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    // Saturating signed add: extend to 32 bits, add, clip back to int16 range.
    Term bv32 = mk_bv_val(tm, 32, (int64_t)b);
    Term lo = mk_bv_val(tm, 32, (int64_t)INT16_MIN);
    Term hi = mk_bv_val(tm, 32, (int64_t)INT16_MAX);
    Op sext16to32 = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Op extract16 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {15u, 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term wide = tm.mkTerm(sext16to32, {a.getElement(i)});
        Term sum  = fold_bvadd(tm, wide, bv32);
        Term gt   = tm.mkTerm(Kind::BITVECTOR_SGT, {sum, hi});
        Term lt   = tm.mkTerm(Kind::BITVECTOR_SLT, {sum, lo});
        Term clamped = tm.mkTerm(Kind::ITE, {gt, hi,
                          fold_ite(tm, lt, lo, sum)});
        r.push_back(tm.mkTerm(extract16, {clamped}));
    }
    return RVVVector(tm, 16, r);
}

inline vint8m4_t __riscv_vnclip_wx_i8m4(const vint16m8_t& op1, size_t shift,
                                          unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 16, vxrm, true);
        r.push_back(signed_clip(tm, shifted, 16, 8));
    }
    return RVVVector(tm, 8, r);
}

// ===========================================================================
// Parity port from bitwuzla — concrete intrinsics for op-families absent in
// cvc5.  Semantics tracked in op-semantics/rvv-intrinsics.md.  All helpers
// below mirror the bitwuzla-tree implementations 1:1, with mk_term→mkTerm,
// BV_*→BITVECTOR_*, and Op-from-mkOp for indexed kinds.
// ===========================================================================

// ---------------------------------------------------------------------------
// Widening arith helpers (vw*): sext/zext narrow operands to 2x width then op.
// ---------------------------------------------------------------------------
inline RVVVector rvv_vwadd_vv_impl(const RVVVector& a, const RVVVector& b,
                                   size_t vl, size_t narrow_bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND,
                     {(uint32_t)narrow_bits});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {a.getElement(i)});
        Term be = tm.mkTerm(ext, {b.getElement(i)});
        r.push_back(fold_bvadd(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwadd_vx_impl(const RVVVector& a, int64_t b, size_t vl,
                                   size_t narrow_bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND,
                     {(uint32_t)narrow_bits});
    Term be = tm.mkTerm(ext, {mk_bv_val(tm, narrow_bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {a.getElement(i)});
        r.push_back(fold_bvadd(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwadd_wv_impl(const RVVVector& a, const RVVVector& b,
                                   size_t vl, size_t narrow_bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND,
                     {(uint32_t)narrow_bits});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term be = tm.mkTerm(ext, {b.getElement(i)});
        r.push_back(fold_bvadd(tm, a.getElement(i), be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwsub_vv_impl(const RVVVector& a, const RVVVector& b,
                                   size_t vl, size_t narrow_bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND,
                     {(uint32_t)narrow_bits});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {a.getElement(i)});
        Term be = tm.mkTerm(ext, {b.getElement(i)});
        r.push_back(fold_bvsub(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwsub_vx_impl(const RVVVector& a, int64_t b, size_t vl,
                                   size_t narrow_bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND,
                     {(uint32_t)narrow_bits});
    Term be = tm.mkTerm(ext, {mk_bv_val(tm, narrow_bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {a.getElement(i)});
        r.push_back(fold_bvsub(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwmul_vv_impl(const RVVVector& a, const RVVVector& b,
                                   size_t vl, size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)narrow_bits});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term be = tm.mkTerm(sext, {b.getElement(i)});
        r.push_back(fold_bvmul(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwmul_vx_impl(const RVVVector& a, int64_t b, size_t vl,
                                   size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)narrow_bits});
    Term be = tm.mkTerm(sext, {mk_bv_val(tm, narrow_bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        r.push_back(fold_bvmul(tm, ae, be));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwmacc_vv_impl(const RVVVector& acc, const RVVVector& a,
                                    const RVVVector& b, size_t vl, size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)narrow_bits});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term be = tm.mkTerm(sext, {b.getElement(i)});
        Term prod = fold_bvmul(tm, ae, be);
        r.push_back(fold_bvadd(tm, acc.getElement(i), prod));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}
inline RVVVector rvv_vwmacc_vx_impl(const RVVVector& acc, int64_t rs1,
                                    const RVVVector& b, size_t vl, size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)narrow_bits});
    Term rs1_ext = tm.mkTerm(sext, {mk_bv_val(tm, narrow_bits, rs1)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term be = tm.mkTerm(sext, {b.getElement(i)});
        Term prod = fold_bvmul(tm, rs1_ext, be);
        r.push_back(fold_bvadd(tm, acc.getElement(i), prod));
    }
    return RVVVector(tm, narrow_bits * 2, r);
}

// vwadd: signed
inline vint16m2_t __riscv_vwadd_vv_i16m2(const vint8m1_t& a, const vint8m1_t& b, size_t vl) { return rvv_vwadd_vv_impl(a,b,vl,8,true); }
inline vint32m4_t __riscv_vwadd_vv_i32m4(const vint16m2_t& a, const vint16m2_t& b, size_t vl) { return rvv_vwadd_vv_impl(a,b,vl,16,true); }
inline vint32m8_t __riscv_vwadd_vv_i32m8(const vint16m4_t& a, const vint16m4_t& b, size_t vl) { return rvv_vwadd_vv_impl(a,b,vl,16,true); }
inline vint16m2_t __riscv_vwadd_vx_i16m2(const vint8m1_t& a, int8_t b, size_t vl) { return rvv_vwadd_vx_impl(a,b,vl,8,true); }
inline vint16m4_t __riscv_vwadd_vx_i16m4(const vint8m2_t& a, int8_t b, size_t vl) { return rvv_vwadd_vx_impl(a,b,vl,8,true); }
inline vint32m2_t __riscv_vwadd_vx_i32m2(const vint16m1_t& a, int16_t b, size_t vl) { return rvv_vwadd_vx_impl(a,b,vl,16,true); }
inline vint32m4_t __riscv_vwadd_vx_i32m4(const vint16m2_t& a, int16_t b, size_t vl) { return rvv_vwadd_vx_impl(a,b,vl,16,true); }
inline vint32m8_t __riscv_vwadd_vx_i32m8(const vint16m4_t& a, int16_t b, size_t vl) { return rvv_vwadd_vx_impl(a,b,vl,16,true); }
inline vint16m2_t __riscv_vwadd_wv_i16m2(const vint16m2_t& a, const vint8m1_t& b, size_t vl) { return rvv_vwadd_wv_impl(a,b,vl,8,true); }
inline vint32m4_t __riscv_vwadd_wv_i32m4(const vint32m4_t& a, const vint16m2_t& b, size_t vl) { return rvv_vwadd_wv_impl(a,b,vl,16,true); }
inline vint32m8_t __riscv_vwadd_wv_i32m8(const vint32m8_t& a, const vint16m4_t& b, size_t vl) { return rvv_vwadd_wv_impl(a,b,vl,16,true); }

// vwaddu: unsigned
inline vuint16m2_t __riscv_vwaddu_vv_u16m2(const vuint8m1_t& a, const vuint8m1_t& b, size_t vl) { return rvv_vwadd_vv_impl(a,b,vl,8,false); }
inline vuint32m4_t __riscv_vwaddu_vv_u32m4(const vuint16m2_t& a, const vuint16m2_t& b, size_t vl) { return rvv_vwadd_vv_impl(a,b,vl,16,false); }
inline vuint16m2_t __riscv_vwaddu_wv_u16m2(const vuint16m2_t& a, const vuint8m1_t& b, size_t vl) { return rvv_vwadd_wv_impl(a,b,vl,8,false); }
inline vuint32m4_t __riscv_vwaddu_wv_u32m4(const vuint32m4_t& a, const vuint16m2_t& b, size_t vl) { return rvv_vwadd_wv_impl(a,b,vl,16,false); }

// vwsub_vv (signed)
inline vint16m2_t __riscv_vwsub_vv_i16m2(const vint8m1_t& a, const vint8m1_t& b, size_t vl) { return rvv_vwsub_vv_impl(a,b,vl,8,true); }
inline vint16m4_t __riscv_vwsub_vv_i16m4(const vint8m2_t& a, const vint8m2_t& b, size_t vl) { return rvv_vwsub_vv_impl(a,b,vl,8,true); }
inline vint32m4_t __riscv_vwsub_vv_i32m4(const vint16m2_t& a, const vint16m2_t& b, size_t vl) { return rvv_vwsub_vv_impl(a,b,vl,16,true); }
inline vint32m8_t __riscv_vwsub_vv_i32m8(const vint16m4_t& a, const vint16m4_t& b, size_t vl) { return rvv_vwsub_vv_impl(a,b,vl,16,true); }
inline vint16m2_t __riscv_vwsub_vx_i16m2(const vint8m1_t& a, int8_t b, size_t vl) { return rvv_vwsub_vx_impl(a,b,vl,8,true); }

// vwsubu_vx (unsigned)
inline vuint16m2_t __riscv_vwsubu_vx_u16m2(const vuint8m1_t& a, uint8_t b, size_t vl) { return rvv_vwsub_vx_impl(a,(int64_t)b,vl,8,false); }
inline vuint16m4_t __riscv_vwsubu_vx_u16m4(const vuint8m2_t& a, uint8_t b, size_t vl) { return rvv_vwsub_vx_impl(a,(int64_t)b,vl,8,false); }

// vwmul (signed) — m4 already exists for symbolic, add concrete m4 + m8
inline vint32m4_t __riscv_vwmul_vv_i32m4(const vint16m2_t& a, const vint16m2_t& b, size_t vl) { return rvv_vwmul_vv_impl(a,b,vl,16); }
inline vint32m4_t __riscv_vwmul_vx_i32m4(const vint16m2_t& a, int16_t b, size_t vl) { return rvv_vwmul_vx_impl(a,b,vl,16); }

// vwmacc (signed)
inline vint32m1_t __riscv_vwmacc_vv_i32m1(const vint32m1_t& acc, const vint16mf2_t& a, const vint16mf2_t& b, size_t vl) { return rvv_vwmacc_vv_impl(acc,a,b,vl,16); }
inline vint32m4_t __riscv_vwmacc_vv_i32m4(const vint32m4_t& acc, const vint16m2_t& a, const vint16m2_t& b, size_t vl) { return rvv_vwmacc_vv_impl(acc,a,b,vl,16); }
inline vint32m8_t __riscv_vwmacc_vv_i32m8(const vint32m8_t& acc, const vint16m4_t& a, const vint16m4_t& b, size_t vl) { return rvv_vwmacc_vv_impl(acc,a,b,vl,16); }
inline vint32m1_t __riscv_vwmacc_vx_i32m1(const vint32m1_t& acc, int16_t rs1, const vint16mf2_t& b, size_t vl) { return rvv_vwmacc_vx_impl(acc,rs1,b,vl,16); }
inline vint32m4_t __riscv_vwmacc_vx_i32m4(const vint32m4_t& acc, int16_t rs1, const vint16m2_t& b, size_t vl) { return rvv_vwmacc_vx_impl(acc,rs1,b,vl,16); }
inline vint32m8_t __riscv_vwmacc_vx_i32m8(const vint32m8_t& acc, int16_t rs1, const vint16m4_t& b, size_t vl) { return rvv_vwmacc_vx_impl(acc,rs1,b,vl,16); }
// symbolic-scalar overload (qd8: a0[i] via salt_scalar.cast<int16_t>()) — sext16→32 both
// operands, mult32, add: matches the NEON vmlal term structure so the nodes hash-cons.
inline vint32m8_t __riscv_vwmacc_vx_i32m8(const vint32m8_t& acc, SymbolicScalar<int16_t> rs1, const vint16m4_t& b, size_t vl) {
    auto& tm = g_ctx->tm; Op sx16 = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Term sb = tm.mkTerm(sx16, {rs1.term()});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ey = tm.mkTerm(sx16, {b.getElement(i)});
        Term p = tm.mkTerm(Kind::BITVECTOR_MULT, {sb, ey});
        r.push_back(tm.mkTerm(Kind::BITVECTOR_ADD, {acc.getElement(i), p}));
    }
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// vwcvt / vwcvtu: widening identity (sign/zero extend, no op).
// ---------------------------------------------------------------------------
inline vint16m2_t __riscv_vwcvt_x_x_v_i16m2(const vint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vint16m4_t __riscv_vwcvt_x_x_v_i16m4(const vint8m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {8});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vint32m4_t __riscv_vwcvt_x_x_v_i32m4(const vint16m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}
inline vuint16m1_t __riscv_vwcvtu_x_x_v_u16m1(const vuint8mf2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {8});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vuint16m2_t __riscv_vwcvtu_x_x_v_u16m2(const vuint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {8});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vuint16m4_t __riscv_vwcvtu_x_x_v_u16m4(const vuint8m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {8});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
inline vuint32m4_t __riscv_vwcvtu_x_x_v_u32m4(const vuint16m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {16});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// vwredsum / vredsum: reductions.  Result is a 1-element wide vector.
// ---------------------------------------------------------------------------
inline vint32m1_t __riscv_vwredsum_vs_i16m2_i32m1(const vint16m2_t& src, const vint32m1_t& init, size_t vl) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Term acc = init.getElement(0);
    for (size_t i = 0; i < vl; i++) {
        Term ext = tm.mkTerm(sext, {src.getElement(i)});
        acc = fold_bvadd(tm, acc, ext);
    }
    return RVVVector(tm, 32, std::vector<Term>{acc});
}
inline vint32m1_t __riscv_vwredsum_vs_i16m4_i32m1(const vint16m4_t& src, const vint32m1_t& init, size_t vl) {
    auto& tm = g_ctx->tm;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {16});
    Term acc = init.getElement(0);
    for (size_t i = 0; i < vl; i++) {
        Term ext = tm.mkTerm(sext, {src.getElement(i)});
        acc = fold_bvadd(tm, acc, ext);
    }
    return RVVVector(tm, 32, std::vector<Term>{acc});
}
inline vint32m1_t __riscv_vredsum_vs_i32m1_i32m1(const vint32m1_t& src, const vint32m1_t& init, size_t vl) {
    auto& tm = g_ctx->tm;
    Term acc = init.getElement(0);
    for (size_t i = 0; i < vl; i++) acc = fold_bvadd(tm, acc, src.getElement(i));
    return RVVVector(tm, 32, std::vector<Term>{acc});
}
inline vint32m1_t __riscv_vredsum_vs_i32m4_i32m1(const vint32m4_t& src, const vint32m1_t& init, size_t vl) {
    auto& tm = g_ctx->tm;
    Term acc = init.getElement(0);
    for (size_t i = 0; i < vl; i++) acc = fold_bvadd(tm, acc, src.getElement(i));
    return RVVVector(tm, 32, std::vector<Term>{acc});
}
inline vint32m1_t __riscv_vredsum_vs_i32m8_i32m1(const vint32m8_t& src, const vint32m1_t& init, size_t vl) {
    auto& tm = g_ctx->tm;
    Term acc = init.getElement(0);
    for (size_t i = 0; i < vl; i++) acc = fold_bvadd(tm, acc, src.getElement(i));
    return RVVVector(tm, 32, std::vector<Term>{acc});
}

// ---------------------------------------------------------------------------
// vncvt: narrowing identity (truncate low half).
// ---------------------------------------------------------------------------
inline RVVVector rvv_vncvt_impl(const RVVVector& a, size_t vl, size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op extract = tm.mkOp(Kind::BITVECTOR_EXTRACT, {(uint32_t)(narrow_bits - 1), 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(extract, {a.getElement(i)}));
    return RVVVector(tm, narrow_bits, r);
}
inline vint8m1_t  __riscv_vncvt_x_x_w_i8m1 (const vint16m2_t& a, size_t vl) { return rvv_vncvt_impl(a,vl,8); }
inline vint8m2_t  __riscv_vncvt_x_x_w_i8m2 (const vint16m4_t& a, size_t vl) { return rvv_vncvt_impl(a,vl,8); }
inline vint16m2_t __riscv_vncvt_x_x_w_i16m2(const vint32m4_t& a, size_t vl) { return rvv_vncvt_impl(a,vl,16); }
inline vint16m4_t __riscv_vncvt_x_x_w_i16m4(const vint32m8_t& a, size_t vl) { return rvv_vncvt_impl(a,vl,16); }
inline vuint8m1_t __riscv_vncvt_x_x_w_u8m1 (const vuint16m2_t& a, size_t vl) { return rvv_vncvt_impl(a,vl,8); }

// ---------------------------------------------------------------------------
// vnsra_wx: narrowing arithmetic shift right (no rounding, no saturation).
// Result is low half of the (signed) shifted wide value.
// ---------------------------------------------------------------------------
inline RVVVector rvv_vnsra_impl(const RVVVector& a, size_t shift, size_t vl,
                                size_t wide_bits, size_t narrow_bits) {
    auto& tm = g_ctx->tm;
    Op extract = tm.mkOp(Kind::BITVECTOR_EXTRACT, {(uint32_t)(narrow_bits - 1), 0u});
    Term sh = mk_bv_val(tm, wide_bits, shift);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = tm.mkTerm(Kind::BITVECTOR_ASHR, {a.getElement(i), sh});
        r.push_back(tm.mkTerm(extract, {shifted}));
    }
    return RVVVector(tm, narrow_bits, r);
}
inline vint8m1_t  __riscv_vnsra_wx_i8m1 (const vint16m2_t& a, size_t shift, size_t vl) { return rvv_vnsra_impl(a,shift,vl,16,8); }
inline vint8m2_t  __riscv_vnsra_wx_i8m2 (const vint16m4_t& a, size_t shift, size_t vl) { return rvv_vnsra_impl(a,shift,vl,16,8); }
inline vint16m2_t __riscv_vnsra_wx_i16m2(const vint32m4_t& a, size_t shift, size_t vl) { return rvv_vnsra_impl(a,shift,vl,32,16); }
inline vint16m4_t __riscv_vnsra_wx_i16m4(const vint32m8_t& a, size_t shift, size_t vl) { return rvv_vnsra_impl(a,shift,vl,32,16); }

// ---------------------------------------------------------------------------
// vnclipu_wx: narrowing clip (unsigned, with optional rounding via vxrm).
// ---------------------------------------------------------------------------
inline vuint8m1_t __riscv_vnclipu_wx_u8m1(const vuint16m2_t& op1, size_t shift,
                                            unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 16, vxrm, false);
        r.push_back(unsigned_clip(tm, shifted, 16, 8));
    }
    return RVVVector(tm, 8, r);
}
inline vuint8m2_t __riscv_vnclipu_wx_u8m2(const vuint16m4_t& op1, size_t shift,
                                            unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 16, vxrm, false);
        r.push_back(unsigned_clip(tm, shifted, 16, 8));
    }
    return RVVVector(tm, 8, r);
}
inline vuint16m2_t __riscv_vnclipu_wx_u16m2(const vuint32m4_t& op1, size_t shift,
                                              unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 32, vxrm, false);
        r.push_back(unsigned_clip(tm, shifted, 32, 16));
    }
    return RVVVector(tm, 16, r);
}
inline vuint16m4_t __riscv_vnclipu_wx_u16m4(const vuint32m8_t& op1, size_t shift,
                                              unsigned vxrm, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = rounded_shift_right(tm, op1.getElement(i), shift, 32, vxrm, false);
        r.push_back(unsigned_clip(tm, shifted, 32, 16));
    }
    return RVVVector(tm, 16, r);
}

// ---------------------------------------------------------------------------
// vaadd / vaaddu: averaging add.  res[i] = (a[i] + b[i] + round) >> 1
// where rounding bit is set per vxrm (RNU adds 1, RDN adds 0, etc.).
// ---------------------------------------------------------------------------
inline RVVVector rvv_vaadd_vv_impl(const RVVVector& op1, const RVVVector& op2,
                                   unsigned vxrm, size_t vl, size_t bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    size_t W = bits + 1;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND, {1});
    Op extract = tm.mkOp(Kind::BITVECTOR_EXTRACT, {(uint32_t)(bits - 1), 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {op1.getElement(i)});
        Term be = tm.mkTerm(ext, {op2.getElement(i)});
        Term sum = fold_bvadd(tm, ae, be);
        Term shifted = rounded_shift_right(tm, sum, 1, W, vxrm, is_signed);
        r.push_back(tm.mkTerm(extract, {shifted}));
    }
    return RVVVector(tm, bits, r);
}
inline RVVVector rvv_vaadd_vx_impl(const RVVVector& op1, int64_t op2,
                                   unsigned vxrm, size_t vl, size_t bits, bool is_signed) {
    auto& tm = g_ctx->tm;
    size_t W = bits + 1;
    Op ext = tm.mkOp(is_signed ? Kind::BITVECTOR_SIGN_EXTEND : Kind::BITVECTOR_ZERO_EXTEND, {1});
    Op extract = tm.mkOp(Kind::BITVECTOR_EXTRACT, {(uint32_t)(bits - 1), 0u});
    Term op2_ext = tm.mkTerm(ext, {mk_bv_val(tm, bits, op2)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(ext, {op1.getElement(i)});
        Term sum = fold_bvadd(tm, ae, op2_ext);
        Term shifted = rounded_shift_right(tm, sum, 1, W, vxrm, is_signed);
        r.push_back(tm.mkTerm(extract, {shifted}));
    }
    return RVVVector(tm, bits, r);
}
inline vint8m2_t   __riscv_vaadd_vv_i8m2  (const vint8m2_t& a,   const vint8m2_t& b,   unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,8,true); }
inline vint16m4_t  __riscv_vaadd_vv_i16m4 (const vint16m4_t& a,  const vint16m4_t& b,  unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,16,true); }
inline vint32m8_t  __riscv_vaadd_vv_i32m8 (const vint32m8_t& a,  const vint32m8_t& b,  unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,32,true); }
inline vuint8m2_t  __riscv_vaaddu_vv_u8m2 (const vuint8m2_t& a,  const vuint8m2_t& b,  unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,8,false); }
inline vuint16m4_t __riscv_vaaddu_vv_u16m4(const vuint16m4_t& a, const vuint16m4_t& b, unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,16,false); }
inline vuint32m8_t __riscv_vaaddu_vv_u32m8(const vuint32m8_t& a, const vuint32m8_t& b, unsigned vxrm, size_t vl) { return rvv_vaadd_vv_impl(a,b,vxrm,vl,32,false); }
inline vint8m2_t   __riscv_vaadd_vx_i8m2  (const vint8m2_t& a,   int8_t b,    unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,b,vxrm,vl,8,true); }
inline vint16m4_t  __riscv_vaadd_vx_i16m4 (const vint16m4_t& a,  int16_t b,   unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,b,vxrm,vl,16,true); }
inline vint32m8_t  __riscv_vaadd_vx_i32m8 (const vint32m8_t& a,  int32_t b,   unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,b,vxrm,vl,32,true); }
inline vuint8m2_t  __riscv_vaaddu_vx_u8m2 (const vuint8m2_t& a,  uint8_t b,   unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,(int64_t)b,vxrm,vl,8,false); }
inline vuint16m4_t __riscv_vaaddu_vx_u16m4(const vuint16m4_t& a, uint16_t b,  unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,(int64_t)b,vxrm,vl,16,false); }
inline vuint32m8_t __riscv_vaaddu_vx_u32m8(const vuint32m8_t& a, uint32_t b,  unsigned vxrm, size_t vl) { return rvv_vaadd_vx_impl(a,(int64_t)b,vxrm,vl,32,false); }

// ---------------------------------------------------------------------------
// vssub_vx: saturating signed subtract.
// ---------------------------------------------------------------------------
inline RVVVector rvv_vssub_vx_impl(const RVVVector& a, int64_t b, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    size_t W = bits * 2;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)bits});
    Term be = tm.mkTerm(sext, {mk_bv_val(tm, bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term diff = fold_bvsub(tm, ae, be);
        r.push_back(signed_clip(tm, diff, W, bits));
    }
    return RVVVector(tm, bits, r);
}
inline vint8m1_t  __riscv_vssub_vx_i8m1 (const vint8m1_t& a,  int8_t b,  size_t vl) { return rvv_vssub_vx_impl(a,b,vl,8); }
inline vint8m2_t  __riscv_vssub_vx_i8m2 (const vint8m2_t& a,  int8_t b,  size_t vl) { return rvv_vssub_vx_impl(a,b,vl,8); }
inline vint16m1_t __riscv_vssub_vx_i16m1(const vint16m1_t& a, int16_t b, size_t vl) { return rvv_vssub_vx_impl(a,b,vl,16); }
inline vint16m2_t __riscv_vssub_vx_i16m2(const vint16m2_t& a, int16_t b, size_t vl) { return rvv_vssub_vx_impl(a,b,vl,16); }
inline vint16m4_t __riscv_vssub_vx_i16m4(const vint16m4_t& a, int16_t b, size_t vl) { return rvv_vssub_vx_impl(a,b,vl,16); }
inline vint32m1_t __riscv_vssub_vx_i32m1(const vint32m1_t& a, int32_t b, size_t vl) { return rvv_vssub_vx_impl(a,b,vl,32); }
inline vint32m4_t __riscv_vssub_vx_i32m4(const vint32m4_t& a, int32_t b, size_t vl) { return rvv_vssub_vx_impl(a,b,vl,32); }

// Additional vsadd_vx LMUL variants (i8, i16, i32 — m8 was added earlier)
inline RVVVector rvv_vsadd_vx_impl_i(const RVVVector& a, int64_t b, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    size_t W = bits * 2;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)bits});
    Term be = tm.mkTerm(sext, {mk_bv_val(tm, bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term sum = fold_bvadd(tm, ae, be);
        r.push_back(signed_clip(tm, sum, W, bits));
    }
    return RVVVector(tm, bits, r);
}
// vsadd_vx i16m4 + i16m8 already exist earlier; only add the missing widths.
inline vint8m1_t  __riscv_vsadd_vx_i8m1 (const vint8m1_t& a,  int8_t b,  size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,8); }
inline vint8m2_t  __riscv_vsadd_vx_i8m2 (const vint8m2_t& a,  int8_t b,  size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,8); }
inline vint16m1_t __riscv_vsadd_vx_i16m1(const vint16m1_t& a, int16_t b, size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,16); }
inline vint16m2_t __riscv_vsadd_vx_i16m2(const vint16m2_t& a, int16_t b, size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,16); }
inline vint32m1_t __riscv_vsadd_vx_i32m1(const vint32m1_t& a, int32_t b, size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,32); }
inline vint32m4_t __riscv_vsadd_vx_i32m4(const vint32m4_t& a, int32_t b, size_t vl) { return rvv_vsadd_vx_impl_i(a,b,vl,32); }

// ---------------------------------------------------------------------------
// vsmul_vx: fractional multiply with saturation.
// res = sat(round((a * b) >> (bits - 1)))
// ---------------------------------------------------------------------------
inline RVVVector rvv_vsmul_vx_impl(const RVVVector& a, int64_t b, unsigned vxrm,
                                   size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    size_t W = bits * 2;
    Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {(uint32_t)bits});
    Term be = tm.mkTerm(sext, {mk_bv_val(tm, bits, b)});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term ae = tm.mkTerm(sext, {a.getElement(i)});
        Term prod = fold_bvmul(tm, ae, be);
        Term shifted = rounded_shift_right(tm, prod, bits - 1, W, vxrm, true);
        r.push_back(signed_clip(tm, shifted, W, bits));
    }
    return RVVVector(tm, bits, r);
}
inline vint16m1_t __riscv_vsmul_vx_i16m1(const vint16m1_t& a, int16_t b, unsigned vxrm, size_t vl) { return rvv_vsmul_vx_impl(a,b,vxrm,vl,16); }
inline vint16m2_t __riscv_vsmul_vx_i16m2(const vint16m2_t& a, int16_t b, unsigned vxrm, size_t vl) { return rvv_vsmul_vx_impl(a,b,vxrm,vl,16); }
inline vint16m4_t __riscv_vsmul_vx_i16m4(const vint16m4_t& a, int16_t b, unsigned vxrm, size_t vl) { return rvv_vsmul_vx_impl(a,b,vxrm,vl,16); }
inline vint32m1_t __riscv_vsmul_vx_i32m1(const vint32m1_t& a, int32_t b, unsigned vxrm, size_t vl) { return rvv_vsmul_vx_impl(a,b,vxrm,vl,32); }
inline vint32m4_t __riscv_vsmul_vx_i32m4(const vint32m4_t& a, int32_t b, unsigned vxrm, size_t vl) { return rvv_vsmul_vx_impl(a,b,vxrm,vl,32); }

// ---------------------------------------------------------------------------
// vssrl_vx: scaling shift right logical (unsigned, with rounding per vxrm).
// ---------------------------------------------------------------------------
inline RVVVector rvv_vssrl_impl(const RVVVector& op1, size_t shift,
                                unsigned vxrm, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(rounded_shift_right(tm, op1.getElement(i), shift, bits, vxrm, false));
    return RVVVector(tm, bits, r);
}
inline vuint8m1_t  __riscv_vssrl_vx_u8m1 (const vuint8m1_t& a,  size_t s, unsigned vxrm, size_t vl) { return rvv_vssrl_impl(a,s,vxrm,vl,8); }
inline vuint8m2_t  __riscv_vssrl_vx_u8m2 (const vuint8m2_t& a,  size_t s, unsigned vxrm, size_t vl) { return rvv_vssrl_impl(a,s,vxrm,vl,8); }
inline vuint16m2_t __riscv_vssrl_vx_u16m2(const vuint16m2_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssrl_impl(a,s,vxrm,vl,16); }
inline vuint16m4_t __riscv_vssrl_vx_u16m4(const vuint16m4_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssrl_impl(a,s,vxrm,vl,16); }
inline vuint32m8_t __riscv_vssrl_vx_u32m8(const vuint32m8_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssrl_impl(a,s,vxrm,vl,32); }

// Additional vssra_vx LMUL variants (m8 already exists earlier in file)
inline RVVVector rvv_vssra_impl(const RVVVector& op1, size_t shift,
                                unsigned vxrm, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(rounded_shift_right(tm, op1.getElement(i), shift, bits, vxrm, true));
    return RVVVector(tm, bits, r);
}
inline vint8m1_t  __riscv_vssra_vx_i8m1 (const vint8m1_t& a,  size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,8); }
inline vint8m2_t  __riscv_vssra_vx_i8m2 (const vint8m2_t& a,  size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,8); }
inline vint16m2_t __riscv_vssra_vx_i16m2(const vint16m2_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,16); }
inline vint16m4_t __riscv_vssra_vx_i16m4(const vint16m4_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,16); }
inline vint32m1_t __riscv_vssra_vx_i32m1(const vint32m1_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,32); }
inline vint32m2_t __riscv_vssra_vx_i32m2(const vint32m2_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,32); }
inline vint32m4_t __riscv_vssra_vx_i32m4(const vint32m4_t& a, size_t s, unsigned vxrm, size_t vl) { return rvv_vssra_impl(a,s,vxrm,vl,32); }

// ---------------------------------------------------------------------------
// vsra_vx: arithmetic shift right (no rounding, no saturation).
// ---------------------------------------------------------------------------
inline RVVVector rvv_vsra_vx_impl(const RVVVector& a, size_t shift, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, bits, shift);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(Kind::BITVECTOR_ASHR, {a.getElement(i), sh}));
    return RVVVector(tm, bits, r);
}
inline vint16m2_t __riscv_vsra_vx_i16m2(const vint16m2_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,16); }
inline vint16m4_t __riscv_vsra_vx_i16m4(const vint16m4_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,16); }
inline vint32m1_t __riscv_vsra_vx_i32m1(const vint32m1_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,32); }
inline vint32m2_t __riscv_vsra_vx_i32m2(const vint32m2_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,32); }
inline vint32m4_t __riscv_vsra_vx_i32m4(const vint32m4_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,32); }
inline vint32m8_t __riscv_vsra_vx_i32m8(const vint32m8_t& a, size_t s, size_t vl) { return rvv_vsra_vx_impl(a,s,vl,32); }

// ---------------------------------------------------------------------------
// FP arithmetic: vfdiv_vf, vfsqrt_v, vfneg_v, vfnmsac_vv,
// vfcvt_rtz_x_f_v, vfmerge_vfm
// ---------------------------------------------------------------------------
inline vfloat32m1_t __riscv_vfdiv_vf_f32m1(const vfloat32m1_t& a, float b, size_t vl) { return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm,b), Kind::FLOATINGPOINT_DIV, vl); }
inline vfloat32m2_t __riscv_vfdiv_vf_f32m2(const vfloat32m2_t& a, float b, size_t vl) { return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm,b), Kind::FLOATINGPOINT_DIV, vl); }
inline vfloat32m4_t __riscv_vfdiv_vf_f32m4(const vfloat32m4_t& a, float b, size_t vl) { return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm,b), Kind::FLOATINGPOINT_DIV, vl); }

inline RVVVector rvv_fp32_unop_via_kind(const RVVVector& a, Kind op, size_t vl,
                                        bool needs_rm) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        Term res = needs_rm ? tm.mkTerm(op, {rm, af}) : tm.mkTerm(op, {af});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m1_t __riscv_vfneg_v_f32m1(const vfloat32m1_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_NEG, vl, false); }
inline vfloat32m2_t __riscv_vfneg_v_f32m2(const vfloat32m2_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_NEG, vl, false); }
inline vfloat32m4_t __riscv_vfneg_v_f32m4(const vfloat32m4_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_NEG, vl, false); }
inline vfloat32m1_t __riscv_vfsqrt_v_f32m1(const vfloat32m1_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_SQRT, vl, true); }
inline vfloat32m2_t __riscv_vfsqrt_v_f32m2(const vfloat32m2_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_SQRT, vl, true); }
inline vfloat32m4_t __riscv_vfsqrt_v_f32m4(const vfloat32m4_t& a, size_t vl) { return rvv_fp32_unop_via_kind(a, Kind::FLOATINGPOINT_SQRT, vl, true); }

// f16 variants (one m1 each — used by f16-vrsqrt etc.)
inline RVVVector rvv_fp16_unop_via_kind(const RVVVector& a, Kind op, size_t vl,
                                        bool needs_rm) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term res = needs_rm ? tm.mkTerm(op, {rm, af}) : tm.mkTerm(op, {af});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}
inline vfloat16m1_t __riscv_vfneg_v_f16m1(const vfloat16m1_t& a, size_t vl) { return rvv_fp16_unop_via_kind(a, Kind::FLOATINGPOINT_NEG, vl, false); }
inline vfloat16m1_t __riscv_vfsqrt_v_f16m1(const vfloat16m1_t& a, size_t vl) { return rvv_fp16_unop_via_kind(a, Kind::FLOATINGPOINT_SQRT, vl, true); }

// vfnmsac_vv: vd = vd - vs1 * vs2  (fused multiply-subtract)
inline RVVVector rvv_vfnmsac_vv_f32_impl(const RVVVector& vd, const RVVVector& vs1,
                                         const RVVVector& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp  = rvv_load_as_fp32(tm, vd.getElement(i));
        Term vs1_fp = rvv_load_as_fp32(tm, vs1.getElement(i));
        Term vs2_fp = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term neg_vs1 = tm.mkTerm(Kind::FLOATINGPOINT_NEG, {vs1_fp});
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, neg_vs1, vs2_fp, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m1_t __riscv_vfnmsac_vv_f32m1(const vfloat32m1_t& vd, const vfloat32m1_t& vs1, const vfloat32m1_t& vs2, size_t vl) { return rvv_vfnmsac_vv_f32_impl(vd,vs1,vs2,vl); }
inline vfloat32m2_t __riscv_vfnmsac_vv_f32m2(const vfloat32m2_t& vd, const vfloat32m2_t& vs1, const vfloat32m2_t& vs2, size_t vl) { return rvv_vfnmsac_vv_f32_impl(vd,vs1,vs2,vl); }
inline vfloat32m4_t __riscv_vfnmsac_vv_f32m4(const vfloat32m4_t& vd, const vfloat32m4_t& vs1, const vfloat32m4_t& vs2, size_t vl) { return rvv_vfnmsac_vv_f32_impl(vd,vs1,vs2,vl); }
// f16 nmsac
inline vfloat16m1_t __riscv_vfnmsac_vv_f16m1(const vfloat16m1_t& vd, const vfloat16m1_t& vs1, const vfloat16m1_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp16(tm, vd.getElement(i));
        Term vs1_fp = rvv_load_as_fp16(tm, vs1.getElement(i));
        Term vs2_fp = rvv_load_as_fp16(tm, vs2.getElement(i));
        Term neg_vs1 = tm.mkTerm(Kind::FLOATINGPOINT_NEG, {vs1_fp});
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, neg_vs1, vs2_fp, vd_fp});
        r.push_back(rvv_store_fp16_as_bv(tm, res));
    }
    return RVVVector(tm, 16, r);
}

// vfcvt_rtz_x_f: float32 → signed int32 (round toward zero, ignoring vfm rm)
inline RVVVector rvv_vfcvt_rtz_x_f_v_i32_impl(const RVVVector& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rtz = tm.mkRoundingMode(RoundingMode::ROUND_TOWARD_ZERO);
    Op cvt = tm.mkOp(Kind::FLOATINGPOINT_TO_SBV, {32});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        r.push_back(tm.mkTerm(cvt, {rtz, af}));
    }
    return RVVVector(tm, 32, r);
}
inline vint32m1_t __riscv_vfcvt_rtz_x_f_v_i32m1(const vfloat32m1_t& a, size_t vl) { return rvv_vfcvt_rtz_x_f_v_i32_impl(a,vl); }
inline vint32m2_t __riscv_vfcvt_rtz_x_f_v_i32m2(const vfloat32m2_t& a, size_t vl) { return rvv_vfcvt_rtz_x_f_v_i32_impl(a,vl); }
inline vint32m4_t __riscv_vfcvt_rtz_x_f_v_i32m4(const vfloat32m4_t& a, size_t vl) { return rvv_vfcvt_rtz_x_f_v_i32_impl(a,vl); }
inline vint32m8_t __riscv_vfcvt_rtz_x_f_v_i32m8(const vfloat32m8_t& a, size_t vl) { return rvv_vfcvt_rtz_x_f_v_i32_impl(a,vl); }

// vfmerge_vfm: select between scalar broadcast and existing element by mask.
inline RVVVector rvv_vfmerge_vfm_f32_impl(const RVVVector& a, float b,
                                          const MaskVector& mask, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, b));
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        r.push_back(fold_ite(tm, sel, bv, a.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m1_t __riscv_vfmerge_vfm_f32m1(const vfloat32m1_t& a, float b, const MaskVector& mask, size_t vl) { return rvv_vfmerge_vfm_f32_impl(a,b,mask,vl); }
inline vfloat32m2_t __riscv_vfmerge_vfm_f32m2(const vfloat32m2_t& a, float b, const MaskVector& mask, size_t vl) { return rvv_vfmerge_vfm_f32_impl(a,b,mask,vl); }
inline vfloat32m4_t __riscv_vfmerge_vfm_f32m4(const vfloat32m4_t& a, float b, const MaskVector& mask, size_t vl) { return rvv_vfmerge_vfm_f32_impl(a,b,mask,vl); }
inline vfloat32m8_t __riscv_vfmerge_vfm_f32m8(const vfloat32m8_t& a, float b, const MaskVector& mask, size_t vl) { return rvv_vfmerge_vfm_f32_impl(a,b,mask,vl); }

// ---------------------------------------------------------------------------
// FP comparisons: vmfeq_vv, vmfne_vv (extra LMUL), vmfge_vf, vmfgt_vf,
// vmfle_vf, vmflt_vf.  Result is a bool mask (1 bit per element).
// ---------------------------------------------------------------------------
inline MaskVector rvv_fp32_cmp_vv_impl(const RVVVector& a, const RVVVector& b,
                                       Kind cmp_kind, size_t vl, bool negate) {
    auto& tm = g_ctx->tm;
    Term one = mk_bv_val(tm, 1, 1), zero = mk_bv_val(tm, 1, 0);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        Term bf = rvv_load_as_fp32(tm, b.getElement(i));
        Term cmp = tm.mkTerm(cmp_kind, {af, bf});
        bits.push_back(fold_ite(tm, cmp, negate ? zero : one, negate ? one  : zero));
    }
    return MaskVector(tm, bits);
}
inline MaskVector rvv_fp32_cmp_vf_impl(const RVVVector& a, float b,
                                       Kind cmp_kind, size_t vl, bool negate) {
    auto& tm = g_ctx->tm;
    Term bf = mk_fp32_from_float(tm, b);
    Term one = mk_bv_val(tm, 1, 1), zero = mk_bv_val(tm, 1, 0);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        Term cmp = tm.mkTerm(cmp_kind, {af, bf});
        bits.push_back(fold_ite(tm, cmp, negate ? zero : one, negate ? one  : zero));
    }
    return MaskVector(tm, bits);
}
// vmfeq_vv (additional LMUL — m1, m4)
inline MaskVector __riscv_vmfeq_vv_f32m1_b32(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_EQ,vl,false); }
inline MaskVector __riscv_vmfeq_vv_f32m4_b8 (const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_EQ,vl,false); }
// vmfne_vv f32 (m1, m4, m8)
inline MaskVector __riscv_vmfne_vv_f32m1_b32(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_EQ,vl,true); }
inline MaskVector __riscv_vmfne_vv_f32m4_b8 (const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_EQ,vl,true); }
inline MaskVector __riscv_vmfne_vv_f32m8_b4 (const vfloat32m8_t& a, const vfloat32m8_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_EQ,vl,true); }
// vmfgt_vv (additional LMUL)
inline MaskVector __riscv_vmfgt_vv_f32m1_b32(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_GT,vl,false); }
inline MaskVector __riscv_vmfgt_vv_f32m4_b8 (const vfloat32m4_t& a, const vfloat32m4_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_GT,vl,false); }
inline MaskVector __riscv_vmflt_vv_f32m1_b32(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) { return rvv_fp32_cmp_vv_impl(a,b,Kind::FLOATINGPOINT_LT,vl,false); }
// vmfgt_vf, vmfge_vf, vmfle_vf, vmflt_vf — mask compare against scalar
inline MaskVector __riscv_vmfgt_vf_f32m1_b32(const vfloat32m1_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_GT,vl,false); }
inline MaskVector __riscv_vmfgt_vf_f32m4_b8 (const vfloat32m4_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_GT,vl,false); }
inline MaskVector __riscv_vmfge_vf_f32m1_b32(const vfloat32m1_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_GEQ,vl,false); }
inline MaskVector __riscv_vmfle_vf_f32m1_b32(const vfloat32m1_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_LEQ,vl,false); }
inline MaskVector __riscv_vmflt_vf_f32m1_b32(const vfloat32m1_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_LT,vl,false); }
inline MaskVector __riscv_vmflt_vf_f32m2_b16(const vfloat32m2_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_LT,vl,false); }
inline MaskVector __riscv_vmflt_vf_f32m4_b8 (const vfloat32m4_t& a, float b, size_t vl) { return rvv_fp32_cmp_vf_impl(a,b,Kind::FLOATINGPOINT_LT,vl,false); }
// f16 vmfne_vv m1
inline MaskVector __riscv_vmfne_vv_f16m1_b16(const vfloat16m1_t& a, const vfloat16m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term one = mk_bv_val(tm, 1, 1), zero = mk_bv_val(tm, 1, 0);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp16(tm, a.getElement(i));
        Term bf = rvv_load_as_fp16(tm, b.getElement(i));
        Term cmp = tm.mkTerm(Kind::FLOATINGPOINT_EQ, {af, bf});
        bits.push_back(fold_ite(tm, cmp, zero, one));
    }
    return MaskVector(tm, bits);
}

// ---------------------------------------------------------------------------
// vslidedown / vslideup / vslide1down: shift-the-vector-window primitives.
// vslidedown: out[i] = a[i+off] (or 0 if past tail).
// vslideup:   out[i] = src[i-off] for i >= off, dst[i] otherwise.
// ---------------------------------------------------------------------------
inline RVVVector rvv_vslidedown_impl(const RVVVector& a, size_t offset, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm; Term zero = mk_bv_val(tm, bits, 0);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back((i + offset < a.getVL()) ? a.getElement(i + offset) : zero);
    return RVVVector(tm, bits, r);
}
inline RVVVector rvv_vslideup_impl(const RVVVector& dst, const RVVVector& src,
                                   size_t offset, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back((i >= offset && (i - offset) < src.getVL())
                    ? src.getElement(i - offset) : dst.getElement(i));
    return RVVVector(tm, bits, r);
}
inline vfloat32m1_t __riscv_vslidedown_vx_f32m1(const vfloat32m1_t& a, size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,32); }
inline vint8m1_t    __riscv_vslidedown_vx_i8m1 (const vint8m1_t& a,    size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,8); }
inline vint16m1_t   __riscv_vslidedown_vx_i16m1(const vint16m1_t& a,   size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,16); }
inline vint32m1_t   __riscv_vslidedown_vx_i32m1(const vint32m1_t& a,   size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,32); }
inline vint32m4_t   __riscv_vslidedown_vx_i32m4(const vint32m4_t& a,   size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,32); }
inline vuint8m1_t   __riscv_vslidedown_vx_u8m1 (const vuint8m1_t& a,   size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,8); }
inline vuint16m1_t  __riscv_vslidedown_vx_u16m1(const vuint16m1_t& a,  size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,16); }
inline vuint32m1_t  __riscv_vslidedown_vx_u32m1(const vuint32m1_t& a,  size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,32); }
inline vuint32m4_t  __riscv_vslidedown_vx_u32m4(const vuint32m4_t& a,  size_t off, size_t vl) { return rvv_vslidedown_impl(a,off,vl,32); }
inline vfloat32m1_t __riscv_vslideup_vx_f32m1(const vfloat32m1_t& dst, const vfloat32m1_t& src, size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,32); }
inline vint8m1_t    __riscv_vslideup_vx_i8m1 (const vint8m1_t& dst,    const vint8m1_t& src,    size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,8); }
inline vint16m1_t   __riscv_vslideup_vx_i16m1(const vint16m1_t& dst,   const vint16m1_t& src,   size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,16); }
inline vint32m1_t   __riscv_vslideup_vx_i32m1(const vint32m1_t& dst,   const vint32m1_t& src,   size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,32); }
inline vuint8m1_t   __riscv_vslideup_vx_u8m1 (const vuint8m1_t& dst,   const vuint8m1_t& src,   size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,8); }
inline vuint16m1_t  __riscv_vslideup_vx_u16m1(const vuint16m1_t& dst,  const vuint16m1_t& src,  size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,16); }
inline vuint32m1_t  __riscv_vslideup_vx_u32m1(const vuint32m1_t& dst,  const vuint32m1_t& src,  size_t off, size_t vl) { return rvv_vslideup_impl(dst,src,off,vl,32); }

inline vint16m1_t  __riscv_vslide1down_vx_i16m1(const vint16m1_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    r.push_back(mk_bv_val(tm, 16, b));
    return RVVVector(tm, 16, r);
}
inline vint32m1_t  __riscv_vslide1down_vx_i32m1(const vint32m1_t& a, int32_t b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    r.push_back(mk_bv_val(tm, 32, b));
    return RVVVector(tm, 32, r);
}
inline vuint16m1_t __riscv_vslide1down_vx_u16m1(const vuint16m1_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    r.push_back(mk_bv_val(tm, 16, b));
    return RVVVector(tm, 16, r);
}
inline vuint32m1_t __riscv_vslide1down_vx_u32m1(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    r.push_back(mk_bv_val(tm, 32, b));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// vsext_vf4: 4x sign-extend (i8 → i32).
// ---------------------------------------------------------------------------
inline vint32m4_t __riscv_vsext_vf4_i32m4(const vint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm; Op sext = tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {24});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(tm.mkTerm(sext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// vmsltu_vx: unsigned mask less-than against a scalar.
// ---------------------------------------------------------------------------
inline MaskVector rvv_vmsltu_vx_impl(const RVVVector& a, uint64_t b, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, bits, (int64_t)b);
    Term one = mk_bv_val(tm, 1, 1), zero = mk_bv_val(tm, 1, 0);
    std::vector<Term> bits_v; bits_v.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::BITVECTOR_ULT, {a.getElement(i), bv});
        bits_v.push_back(fold_ite(tm, cmp, one, zero));
    }
    return MaskVector(tm, bits_v);
}
inline MaskVector __riscv_vmsltu_vx_u8m1_b8 (const vuint8m1_t& a,  uint8_t b,  size_t vl) { return rvv_vmsltu_vx_impl(a,b,vl,8); }
inline MaskVector __riscv_vmsltu_vx_u32m4_b8(const vuint32m4_t& a, uint32_t b, size_t vl) { return rvv_vmsltu_vx_impl(a,b,vl,32); }

// ---------------------------------------------------------------------------
// vxor_vx: bitwise xor with a broadcast scalar.
// ---------------------------------------------------------------------------
inline RVVVector rvv_vxor_vx_impl(const RVVVector& a, int64_t b, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm; Term bv = mk_bv_val(tm, bits, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(fold_bvxor(tm, a.getElement(i), bv));
    return RVVVector(tm, bits, r);
}
inline vint32m4_t __riscv_vxor_vx_i32m4(const vint32m4_t& a, int32_t b, size_t vl) { return rvv_vxor_vx_impl(a,b,vl,32); }
inline vint32m8_t __riscv_vxor_vx_i32m8(const vint32m8_t& a, int32_t b, size_t vl) { return rvv_vxor_vx_impl(a,b,vl,32); }

// ---------------------------------------------------------------------------
// vundefined / vlmul_trunc_v: shape ops.  Undefined returns an empty vector;
// lmul_trunc reinterprets the wider vector as a narrower-LMUL same-element
// vector (no data movement, just a logical truncation of the vector group).
// ---------------------------------------------------------------------------
inline RVVVector __riscv_vundefined_u8m2() { return RVVVector(); }
inline RVVVector __riscv_vlmul_trunc_v_i32m4_i32m1(const RVVVector& a) { return a; }

// vle/vse/vadd for i32m1 — used by qs8-rsum's int32 accumulator path.
inline vint32m1_t __riscv_vle32_v_i32m1(const int32_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 32);
}
inline void __riscv_vse32_v_i32m1(int32_t* p, const vint32m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 32, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}
inline vint32m1_t __riscv_vadd_vv_i32m1(const vint32m1_t& a, const vint32m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 32, r);
}
inline vint32m1_t __riscv_vmul_vv_i32m1(const vint32m1_t& a, const vint32m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvmul(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 32, r);
}
inline vuint8m1_t __riscv_vsll_vx_u8m1(const vuint8m1_t& a, uint8_t n, size_t vl) {
    auto& tm = g_ctx->tm;
    Term shift = mk_bv_val(tm, 8, n);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(Kind::BITVECTOR_SHL, {a.getElement(i), shift}));
    return RVVVector(tm, 8, r);
}
inline vint8m1_t __riscv_vsra_vx_i8m1(const vint8m1_t& a, uint8_t n, size_t vl) {
    auto& tm = g_ctx->tm;
    Term shift = mk_bv_val(tm, 8, n);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(Kind::BITVECTOR_ASHR, {a.getElement(i), shift}));
    return RVVVector(tm, 8, r);
}
inline vint8m1_t  __riscv_vreinterpret_v_u8m1_i8m1(const vuint8m1_t& a) { return a; }
inline vuint8m1_t __riscv_vreinterpret_v_i8m1_u8m1(const vint8m1_t& a)  { return a; }
// __riscv_vlut4_u8m1: 4-entry table lookup. result[i] = T[idx[i] & 3].
// Verifier-only helper modeling a small variant of vrgather_vv_u8m1.
inline vuint8m1_t __riscv_vlut4_u8m1(const vuint8m1_t& idx,
                                      uint8_t T0, uint8_t T1, uint8_t T2, uint8_t T3,
                                      size_t vl) {
    auto& tm = g_ctx->tm;
    Term mask3 = mk_bv_val(tm, 8, (int64_t)3);
    Term k0 = mk_bv_val(tm, 8, (int64_t)0);
    Term k1 = mk_bv_val(tm, 8, (int64_t)1);
    Term k2 = mk_bv_val(tm, 8, (int64_t)2);
    Term v0 = mk_bv_val(tm, 8, (int64_t)T0);
    Term v1 = mk_bv_val(tm, 8, (int64_t)T1);
    Term v2 = mk_bv_val(tm, 8, (int64_t)T2);
    Term v3 = mk_bv_val(tm, 8, (int64_t)T3);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term masked = tm.mkTerm(Kind::BITVECTOR_AND, {idx.getElement(i), mask3});
        Term ite = tm.mkTerm(Kind::ITE,
                    {tm.mkTerm(Kind::EQUAL, {masked, k0}), v0,
                     tm.mkTerm(Kind::ITE,
                       {tm.mkTerm(Kind::EQUAL, {masked, k1}), v1,
                        tm.mkTerm(Kind::ITE,
                          {tm.mkTerm(Kind::EQUAL, {masked, k2}), v2, v3})})});
        r.push_back(ite);
    }
    return RVVVector(tm, 8, r);
}
// vsext_vf4: sign-extend each i8 lane to i32 (4× widening).  vl is the
// destination lane count.
inline vint32m1_t __riscv_vsext_vf4_i32m1(const vint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsext(tm, 24, a.getElement(i)));  // 8 → 32 = +24 bits
    return RVVVector(tm, 32, r);
}
// i16m1 / i16m2 ops used by s8-ibilinear.
inline vint16m1_t __riscv_vle16_v_i16m1(const int16_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 16);
}
inline vint16m2_t __riscv_vsext_vf2_i16m2(const vint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsext(tm, 8, a.getElement(i)));  // 8 → 16
    return RVVVector(tm, 16, r);
}
inline vuint16m2_t __riscv_vzext_vf2_u16m2(const vuint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvzext(tm, 8, a.getElement(i)));  // 8 → 16
    return RVVVector(tm, 16, r);
}
inline vint16m2_t  __riscv_vreinterpret_v_u16m2_i16m2(const vuint16m2_t& a) { return a; }
inline vuint16m2_t __riscv_vreinterpret_v_i16m2_u16m2(const vint16m2_t&  a) { return a; }
inline vint16m2_t __riscv_vsub_vv_i16m2(const vint16m2_t& a, const vint16m2_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvsub(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 16, r);
}
inline vint16m2_t __riscv_vadd_vv_i16m2(const vint16m2_t& a, const vint16m2_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 16, r);
}
inline vint16m2_t __riscv_vmul_vx_i16m2(const vint16m2_t& a, int16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvmul(tm, a.getElement(i), bv));
    return RVVVector(tm, 16, r);
}
// vmul_vv (i16m2): vector × vector — preserves symbolic flow when one
// operand is a broadcasted alpha (loaded via vlse with stride=0).
inline vint16m2_t __riscv_vmul_vv_i16m2(const vint16m2_t& a, const vint16m2_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvmul(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 16, r);
}
// vlse16: strided load — stride=0 broadcasts a single element across vl lanes.
inline vint16m2_t __riscv_vlse16_v_i16m2(const int16_t* p, ptrdiff_t stride, size_t vl) {
    auto& tm = g_ctx->tm;
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        size_t off = b.ptrToByteOffset(p) + i * (size_t)stride;
        lanes.push_back(b.loadScalar(off, 16));
    }
    return RVVVector(tm, 16, lanes);
}
// vmv_x_s_i16m1_i16: extract lane 0 to a scalar int16.  Concrete return value
// unused in symbolic mode; the actual term is preserved through the symbolic
// scalar side channel.  For this kernel the kernel uses the returned scalar
// in vmul_vx — which only sees the C++ int16 type.  This means the symbolic
// flow is lost across this extraction.  As a workaround, we keep a parallel
// 1-lane vector with the same data on the caller side (already done in the
// kernel by using vle16 for the alphas as full vectors).
// Concrete value 0 — kernel uses the result via SymbolicScalar<int16> path
// elsewhere if available; for this minimal first iteration, the scalar mul-vx
// would lose the symbolic term.  We accept that for now since it'll surface
// as a counterexample we can debug.
inline int16_t __riscv_vmv_x_s_i16m1_i16(const vint16m1_t& a) { (void)a; return 0; }

// vzext_vf4: zero-extend each u8 lane to u32.
inline vuint32m1_t __riscv_vzext_vf4_u32m1(const vuint8m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvzext(tm, 24, a.getElement(i)));
    return RVVVector(tm, 32, r);
}
inline vuint32m1_t __riscv_vadd_vv_u32m1(const vuint32m1_t& a, const vuint32m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 32, r);
}

// ---------------------------------------------------------------------------
// vfloat16m1x2_t: 2-segment tuple of f16m1 vectors.
// ---------------------------------------------------------------------------
struct vfloat16m1x2_t {
    vfloat16m1_t val[2];
    vfloat16m1x2_t() = default;
    vfloat16m1x2_t(const vfloat16m1_t& v0, const vfloat16m1_t& v1) : val{v0, v1} {}
};
inline vfloat16m1x2_t __riscv_vset_v_f16m1_f16m1x2(vfloat16m1x2_t dest, size_t index,
                                                    const vfloat16m1_t& val) {
    dest.val[index] = val;
    return dest;
}

// ---------------------------------------------------------------------------
// vsse16: strided store. bstride is in BYTES.
// ---------------------------------------------------------------------------
inline void __riscv_vsse16_v_f16m1(salt_float16* base, ptrdiff_t bstride,
                                   const vfloat16m1_t& value, size_t vl) {
    auto& buf = g_ctx->findBuffer(base);
    ptrdiff_t base_off = (ptrdiff_t)buf.ptrToByteOffset(base);
    for (size_t i = 0; i < vl; i++) {
        ptrdiff_t off = base_off + (ptrdiff_t)i * bstride;
        buf.storeScalar((size_t)off, value.getElement(i), 16);
    }
}
inline void __riscv_vsse16_v_f16m4(salt_float16* base, ptrdiff_t bstride,
                                   const vfloat16m4_t& value, size_t vl) {
    auto& buf = g_ctx->findBuffer(base);
    ptrdiff_t base_off = (ptrdiff_t)buf.ptrToByteOffset(base);
    for (size_t i = 0; i < vl; i++) {
        ptrdiff_t off = base_off + (ptrdiff_t)i * bstride;
        buf.storeScalar((size_t)off, value.getElement(i), 16);
    }
}

// vssseg2e16: strided segment store, nseg=2.
//   *(base + i*bstride + 0*elem_bytes) = v_tuple.val[0][i]
//   *(base + i*bstride + 1*elem_bytes) = v_tuple.val[1][i]
inline void __riscv_vssseg2e16_v_f16m1x2(salt_float16* base, ptrdiff_t bstride,
                                          const vfloat16m1x2_t& v_tuple, size_t vl) {
    auto& buf = g_ctx->findBuffer(base);
    ptrdiff_t base_off = (ptrdiff_t)buf.ptrToByteOffset(base);
    for (size_t i = 0; i < vl; i++) {
        ptrdiff_t off = base_off + (ptrdiff_t)i * bstride;
        buf.storeScalar((size_t)off,     v_tuple.val[0].getElement(i), 16);
        buf.storeScalar((size_t)off + 2, v_tuple.val[1].getElement(i), 16);
    }
}

// vse8_v_i8m4: contiguous int8 store at LMUL=4.  Currently the only
// missing-and-actually-used intrinsic in this batch.
inline void __riscv_vse8_v_i8m4(int8_t* p, const vint8m4_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p); b.storeRVV(b.ptrToByteOffset(p), v);
}

// ===========================================================================
// BF16-GEMM RVV intrinsics — bit ops + mask predicates needed by the LLM-
// translated bf16 kernel. Semantics per op-semantics/rvv-intrinsics.md.
// ===========================================================================

// vand.vx (u16m1) — element-wise AND with scalar.
inline vuint16m1_t __riscv_vand_vx_u16m1(const vuint16m1_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvand(tm, a.getElement(i), bv));
    return RVVVector(tm, 16, r);
}

// vand.vx (u16m1) — masked-undisturbed: where mask==1 do AND, else pass merge.
inline vuint16m1_t __riscv_vand_vx_u16m1_mu(const vbool16_t& mask,
                                             const vuint16m1_t& merge,
                                             const vuint16m1_t& a,
                                             uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv  = mk_bv_val(tm, 16, (int64_t)b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond  = fold_eq(tm, mask.getBit(i), one);
        Term anded = fold_bvand(tm, a.getElement(i), bv);
        r.push_back(fold_ite(tm, cond, anded, merge.getElement(i)));
    }
    return RVVVector(tm, 16, r);
}

// vmseq.vx (u16m1 → b16) — element-wise equality with scalar, returns mask.
inline MaskVector __riscv_vmseq_vx_u16m1_b16(const vuint16m1_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term eq = fold_eq(tm, a.getElement(i), bv);
        bits.push_back(fold_ite(tm, eq, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// vmsne.vx (u16m1 → b16) — element-wise inequality with scalar.
inline MaskVector __riscv_vmsne_vx_u16m1_b16(const vuint16m1_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term eq = fold_eq(tm, a.getElement(i), bv);
        Term ne = tm.mkTerm(Kind::NOT, {eq});
        bits.push_back(fold_ite(tm, ne, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// vmor.mm (b16) — bitwise OR of two masks.
inline MaskVector __riscv_vmor_mm_b16(const vbool16_t& a, const vbool16_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        bits.push_back(fold_bvor(tm, a.getBit(i), b.getBit(i)));
    return MaskVector(tm, bits);
}

// vzext.vf2 (u16m1 → u32m2) — zero-extend each 16-bit lane to 32 bits.
inline vuint32m2_t __riscv_vzext_vf2_u32m2(const vuint16m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {16});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}

// vsll.vx (u32m2) — left shift each 32-bit lane by `shift`.
inline vuint32m2_t __riscv_vsll_vx_u32m2(const vuint32m2_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}

// ===========================================================================
// Strict-Arm BFDOT support — full intrinsic set used by the LLM-translated
// xnn_bfdot_f32 / xnn_bfcvtn_f32 / xnn_vpaddq_f32 helpers. These implement
// fp64-sticky-bit Round-to-Odd, FZ pre-flush, and default-NaN gating per
// translation_rules.md §9.4 (strict mode).
// ===========================================================================

// --- FP64 type aliases ----------------------------------------------------
using vfloat64m1_t = RVVVector;
using vfloat64m2_t = RVVVector;
using vfloat64m4_t = RVVVector;
using vuint16mf2_t = RVVVector;

// --- Reinterprets (bit cast — no-op on lanes) -----------------------------
inline vfloat32m2_t __riscv_vreinterpret_v_u32m2_f32m2(const vuint32m2_t& a) { return a; }
inline vuint32m2_t  __riscv_vreinterpret_v_f32m2_u32m2(const vfloat32m2_t& a) { return a; }
inline vuint32m1_t  __riscv_vreinterpret_v_f32m1_u32m1(const vfloat32m1_t& a) { return a; }
inline vfloat32m1_t __riscv_vreinterpret_v_u32m1_f32m1(const vuint32m1_t& a) { return a; }

// --- LMUL grouping casts (no-op for symbolic models — same RVVVector) ----
inline vfloat64m2_t __riscv_vlmul_trunc_v_f64m4_f64m2(const vfloat64m4_t& a) { return a; }
inline vuint16mf2_t __riscv_vlmul_trunc_v_u16m1_u16mf2(const vuint16m1_t& a) { return a; }
inline vuint32m2_t  __riscv_vlmul_ext_v_u32m1_u32m2(const vuint32m1_t& a)  { return a; }
inline vuint16m1_t  __riscv_vlmul_ext_v_u16mf2_u16m1(const vuint16mf2_t& a) { return a; }

// --- Element-wise FP arith --------------------------------------------------
inline vfloat32m2_t __riscv_vfmul_vv_f32m2(const vfloat32m2_t& a, const vfloat32m2_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_MULT, vl);
}
inline vfloat32m1_t __riscv_vfadd_vv_f32m1(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_ADD, vl);
}
inline vfloat32m1_t __riscv_vfsub_vv_f32m1(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_SUB, vl);
}
// vlse32 strided load (stride in bytes); stride=0 broadcasts lane 0.
// Resolves findBuffer PER LANE: with a shifted-back base pointer (de-gather
// left-pad trick) lane 0 can land before its buffer while higher lanes are
// in-bounds — a single base-pointer findBuffer would read every lane from the
// wrong buffer and corrupt the valid lanes (only bites at vl>=2).
inline vfloat32m1_t __riscv_vlse32_v_f32m1(const float* p, ptrdiff_t stride, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> lanes; lanes.reserve(vl);
    if (stride == 0) {
        auto& b = g_ctx->findBuffer(p);
        Term v0 = b.loadScalar(b.ptrToByteOffset(p), 32);
        for (size_t i = 0; i < vl; i++) lanes.push_back(v0);
    } else {
        for (size_t i = 0; i < vl; i++) {
            const float* lp = (const float*)((uintptr_t)p + i * (size_t)stride);
            auto& b = g_ctx->findBuffer(lp);
            lanes.push_back(b.loadScalar(b.ptrToByteOffset(lp), 32));
        }
    }
    return RVVVector(tm, 32, lanes);
}

// --- FP64 helpers (mirror fp32 helpers but with sort {11, 53}) ------------
inline Term rvv_load_as_fp64(TermManager& tm, Term bv64) {
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {11, 53});
    return tm.mkTerm(op, {bv64});
}
inline size_t& rvv_fp64_bv_counter() { static size_t c = 0; return c; }
inline Term rvv_store_fp64_as_bv(TermManager& tm, Term fp_val) {
    Sort bv64 = tm.mkBitVectorSort(64);
    Term bv = tm.mkConst(bv64, "_rvv_fp64_2bv_" + std::to_string(rvv_fp64_bv_counter()++));
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {11, 53});
    Term fp_from_bv = tm.mkTerm(op, {bv});
    g_ctx->solver->assertFormula(fold_eq(tm, fp_from_bv, fp_val));
    return bv;
}

// --- FP32 → FP64 widening converts -----------------------------------------
inline vfloat64m4_t __riscv_vfwcvt_f_f_v_f64m4(const vfloat32m2_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    Op cast = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_FP, {11, 53});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term f32 = rvv_load_as_fp32(tm, a.getElement(i));
        Term f64 = tm.mkTerm(cast, {rm, f32});  // exact: fp32 fits in fp64
        r.push_back(rvv_store_fp64_as_bv(tm, f64));
    }
    return RVVVector(tm, 64, r);
}
inline vfloat64m2_t __riscv_vfwcvt_f_f_v_f64m2(const vfloat32m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    Op cast = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_FP, {11, 53});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term f32 = rvv_load_as_fp32(tm, a.getElement(i));
        Term f64 = tm.mkTerm(cast, {rm, f32});
        r.push_back(rvv_store_fp64_as_bv(tm, f64));
    }
    return RVVVector(tm, 64, r);
}

// --- FP64 add with explicit rounding mode ----------------------------------
inline vfloat64m2_t __riscv_vfadd_vv_f64m2_rm(const vfloat64m2_t& a, const vfloat64m2_t& b,
                                                unsigned frm, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = rm_term_from_frm(tm, frm);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp64(tm, a.getElement(i));
        Term bf = rvv_load_as_fp64(tm, b.getElement(i));
        Term s  = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
        r.push_back(rvv_store_fp64_as_bv(tm, s));
    }
    return RVVVector(tm, 64, r);
}

// --- FP64 → FP32 narrowing convert with rm --------------------------------
inline vfloat32m1_t __riscv_vfncvt_f_f_w_f32m1_rm(const vfloat64m2_t& a,
                                                    unsigned frm, size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = rm_term_from_frm(tm, frm);
    Op cast = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_FP, {8, 24});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term f64 = rvv_load_as_fp64(tm, a.getElement(i));
        Term f32 = tm.mkTerm(cast, {rm, f64});
        r.push_back(rvv_store_fp32_as_bv(tm, f32));
    }
    return RVVVector(tm, 32, r);
}

// --- FP NEQ comparisons ----------------------------------------------------
inline MaskVector __riscv_vmfne_vv_f64m2_b32(const vfloat64m2_t& a, const vfloat64m2_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp64(tm, a.getElement(i));
        Term bf = rvv_load_as_fp64(tm, b.getElement(i));
        Term eq = tm.mkTerm(Kind::FLOATINGPOINT_EQ, {af, bf});
        Term ne = tm.mkTerm(Kind::NOT, {eq});
        bits.push_back(fold_ite(tm, ne, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}

// --- vid (lane index generator) -------------------------------------------
inline vuint16m1_t __riscv_vid_v_u16m1(size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(mk_bv_val(tm, 16, static_cast<int64_t>(i)));
    return RVVVector(tm, 16, r);
}
inline vuint32m1_t __riscv_vid_v_u32m1(size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) r.push_back(mk_bv_val(tm, 32, static_cast<int64_t>(i)));
    return RVVVector(tm, 32, r);
}

// --- Shifts (additional widths) -------------------------------------------
inline vuint16m1_t __riscv_vsll_vx_u16m1(const vuint16m1_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 16, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 16, r);
}
inline vuint32m1_t __riscv_vsll_vx_u32m1(const vuint32m1_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvshl(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}
inline vuint32m1_t __riscv_vsrl_vx_u32m1(const vuint32m1_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvlshr(tm, a.getElement(i), sh));
    return RVVVector(tm, 32, r);
}

// --- Narrowing right shifts (n.s.r.l: u32 → u16) --------------------------
inline vuint16m1_t __riscv_vnsrl_wx_u16m1(const vuint32m2_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    Op extract16 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {15u, 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = fold_bvlshr(tm, a.getElement(i), sh);
        r.push_back(tm.mkTerm(extract16, {shifted}));
    }
    return RVVVector(tm, 16, r);
}
inline vuint16mf2_t __riscv_vnsrl_wx_u16mf2(const vuint32m1_t& a, size_t shift, size_t vl) {
    auto& tm = g_ctx->tm;
    Term sh = mk_bv_val(tm, 32, static_cast<int64_t>(shift));
    Op extract16 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {15u, 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term shifted = fold_bvlshr(tm, a.getElement(i), sh);
        r.push_back(tm.mkTerm(extract16, {shifted}));
    }
    return RVVVector(tm, 16, r);
}

// --- vadd_vx (u16m1) -------------------------------------------------------
inline vuint16m1_t __riscv_vadd_vx_u16m1(const vuint16m1_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), bv));
    return RVVVector(tm, 16, r);
}

// --- vand_vx (u32m1) and masked-undisturbed variant -----------------------
inline vuint32m1_t __riscv_vand_vx_u32m1(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvand(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}
inline vuint32m1_t __riscv_vand_vx_u32m1_mu(const vbool32_t& mask,
                                              const vuint32m1_t& merge,
                                              const vuint32m1_t& a,
                                              uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv  = mk_bv_val(tm, 32, (int64_t)b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond  = fold_eq(tm, mask.getBit(i), one);
        Term anded = fold_bvand(tm, a.getElement(i), bv);
        r.push_back(fold_ite(tm, cond, anded, merge.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}

// --- vor_vv (u16m1) and masked-undisturbed vor_vx (u32m1) -----------------
inline vuint16m1_t __riscv_vor_vv_u16m1(const vuint16m1_t& a, const vuint16m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvor(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 16, r);
}
inline vuint32m1_t __riscv_vor_vx_u32m1_mu(const vbool32_t& mask,
                                             const vuint32m1_t& merge,
                                             const vuint32m1_t& a,
                                             uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv  = mk_bv_val(tm, 32, (int64_t)b);
    Term one = mk_bv_val(tm, 1, 1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cond = fold_eq(tm, mask.getBit(i), one);
        Term ored = fold_bvor(tm, a.getElement(i), bv);
        r.push_back(fold_ite(tm, cond, ored, merge.getElement(i)));
    }
    return RVVVector(tm, 32, r);
}

// --- vzext_vf2 (u16mf2 → u32m1) -------------------------------------------
inline vuint32m1_t __riscv_vzext_vf2_u32m1(const vuint16mf2_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Op zext = tm.mkOp(Kind::BITVECTOR_ZERO_EXTEND, {16});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(zext, {a.getElement(i)}));
    return RVVVector(tm, 32, r);
}

// --- Mask predicates at b32 -----------------------------------------------
inline MaskVector __riscv_vmseq_vx_u32m1_b32(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term eq = fold_eq(tm, a.getElement(i), bv);
        bits.push_back(fold_ite(tm, eq, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmsne_vx_u32m1_b32(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)b);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term eq = fold_eq(tm, a.getElement(i), bv);
        Term ne = tm.mkTerm(Kind::NOT, {eq});
        bits.push_back(fold_ite(tm, ne, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmand_mm_b32(const vbool32_t& a, const vbool32_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        bits.push_back(fold_bvand(tm, a.getBit(i), b.getBit(i)));
    return MaskVector(tm, bits);
}
inline MaskVector __riscv_vmor_mm_b32(const vbool32_t& a, const vbool32_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        bits.push_back(fold_bvor(tm, a.getBit(i), b.getBit(i)));
    return MaskVector(tm, bits);
}

// --- Broadcasts -----------------------------------------------------------
inline vuint32m1_t __riscv_vmv_v_x_u32m1(uint32_t v, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)v);
    std::vector<Term> r(vl, bv);
    return RVVVector(tm, 32, r);
}

// --- Merges (u16m1 / u32m1) ----------------------------------------------
inline vuint16m1_t __riscv_vmerge_vxm_u16m1(const vuint16m1_t& a, uint16_t b,
                                              const vbool16_t& mask, size_t vl) {
    return rvv_vmerge_vxm_impl(a, (int64_t)b, mask, vl, 16);
}
inline vuint32m1_t __riscv_vmerge_vxm_u32m1(const vuint32m1_t& a, uint32_t b,
                                              const vbool32_t& mask, size_t vl) {
    return rvv_vmerge_vxm_impl(a, (int64_t)b, mask, vl, 32);
}

// --- Gathers (delegate to rvv_vrgather_vv_impl above; src.elemBits() and
//     idx.elemBits() are read from the vectors at call time) --------------
inline vuint16m1_t  __riscv_vrgather_vv_u16m1(const vuint16m1_t& s, const vuint16m1_t& idx, size_t vl) {
    return rvv_vrgather_vv_impl(s, idx, vl, 16);
}
inline vfloat32m1_t __riscv_vrgather_vv_f32m1(const vfloat32m1_t& s, const vuint32m1_t& idx, size_t vl) {
    return rvv_vrgather_vv_impl(s, idx, vl, 32);
}
// vrgatherei16: indices are u16, source is f64m4 — pick per u16 index.
inline vfloat64m4_t __riscv_vrgatherei16_vv_f64m4(const vfloat64m4_t& s,
                                                    const vuint16m1_t& idx, size_t vl) {
    return rvv_vrgather_vv_impl(s, idx, vl, 64);
}

// (vslidedown_vx_f32m1 / vslideup_vx_f32m1 already defined upstream — see
//  rvv_vslidedown_impl / rvv_vslideup_impl.)

// --- Additional intrinsics for the second LLM bf16-gemm translation ------
// vmerge.vvm: mask==1 → src, else merge.
// Defensive against `src.getVL() < vl` (happens when src came from a partial
// vle with vl < VLMAX): treat out-of-range src lanes as 0 (tail-agnostic).
// Both ITE branches are evaluated symbolically, so we cannot rely on the
// mask making src[i] unreachable.
inline RVVVector rvv_vmerge_vvm_impl(const RVVVector& merge, const RVVVector& src,
                                       const MaskVector& mask, size_t vl, size_t bits) {
    auto& tm = g_ctx->tm;
    Term one = mk_bv_val(tm, 1, 1);
    Term zero_bits = mk_bv_val(tm, bits, (int64_t)0);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term sel = fold_eq(tm, mask.getBit(i), one);
        Term src_v = (i < src.getVL()) ? src.getElement(i) : zero_bits;
        r.push_back(fold_ite(tm, sel, src_v, merge.getElement(i)));
    }
    return RVVVector(tm, bits, r);
}
inline vuint16m1_t __riscv_vmerge_vvm_u16m1(const vuint16m1_t& merge, const vuint16m1_t& src,
                                              const vbool16_t& mask, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, src, mask, vl, 16);
}
inline vuint32m1_t __riscv_vmerge_vvm_u32m1(const vuint32m1_t& merge, const vuint32m1_t& src,
                                              const vbool32_t& mask, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, src, mask, vl, 32);
}

// Tail-undisturbed (_tu) result: lanes < vl come from `body`, lanes in
// [vl, dst.VL) keep `dst`.  Lanes < vl are computed even if dst is shorter.
inline RVVVector rvv_tu_impl(const RVVVector& dst, const RVVVector& body, size_t vl, size_t bits) {
    size_t n = dst.getVL() > vl ? dst.getVL() : vl;
    std::vector<Term> r; r.reserve(n);
    for (size_t i = 0; i < n; i++) r.push_back(i < vl ? body.getElement(i) : dst.getElement(i));
    return RVVVector(g_ctx->tm, bits, r);
}

// vfmul.vf (f32m8) — masked-undisturbed: where mask==1 multiply, else pass merge.
// Used by the Phase-2 f32-vlrelu kernel.
inline vfloat32m8_t __riscv_vfmul_vf_f32m8_mu(const vbool4_t& mask, const vfloat32m8_t& merge,
                                               const vfloat32m8_t& a, float b, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, __riscv_vfmul_vf_f32m8(a, b, vl), mask, vl, 32);
}
inline vfloat32m8_t __riscv_vfmul_vf_f32m8_mu(const vbool4_t& mask, const vfloat32m8_t& merge,
                                               const vfloat32m8_t& a, SymbolicScalar<float> b, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, __riscv_vfmul_vf_f32m8(a, b, vl), mask, vl, 32);
}

// vrgather.vv (f32m2): result[i] = src[idx[i]] (or 0 if idx[i] >= src.VL).
inline vfloat32m2_t __riscv_vrgather_vv_f32m2(const vfloat32m2_t& s,
                                                const vuint32m2_t& idx, size_t vl) {
    return rvv_vrgather_vv_impl(s, idx, vl, 32);
}

// vlmul_trunc f32m2 → f32m1 (no-op for symbolic models — same RVVVector).
inline vfloat32m1_t __riscv_vlmul_trunc_v_f32m2_f32m1(const vfloat32m2_t& a) { return a; }

// vadd.vx (u32m1) — element-wise add with scalar.
inline vuint32m1_t __riscv_vadd_vx_u32m1(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvadd(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}

// vor.vx (u32m1) — element-wise OR with scalar.
inline vuint32m1_t __riscv_vor_vx_u32m1(const vuint32m1_t& a, uint32_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 32, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvor(tm, a.getElement(i), bv));
    return RVVVector(tm, 32, r);
}

// --- u16m1 loads / stores ------------------------------------------------
inline vuint16m1_t __riscv_vle16_v_u16m1(const uint16_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 16);
}
// Tail-undisturbed: lanes [0, vl) come from memory, lanes [vl, merge.getVL())
// keep the merge value. Used for partial-tail loads in the GEMM main loop.
inline vuint16m1_t __riscv_vle16_v_u16m1_tu(const vuint16m1_t& merge,
                                              const uint16_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    vuint16m1_t loaded = b.loadRVV(b.ptrToByteOffset(p), vl, 16);
    if (merge.getVL() <= vl) return loaded;
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(merge.getVL());
    for (size_t i = 0; i < merge.getVL(); i++)
        r.push_back(i < vl ? loaded.getElement(i) : merge.getElement(i));
    return RVVVector(tm, 16, r);
}
inline void __riscv_vse16_v_u16m1(uint16_t* p, const vuint16m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    b.storeRVV(b.ptrToByteOffset(p), v);
}
// xnn_bfloat16 thin overload — kernels passing xnn_bfloat16* directly.
inline vuint16m1_t __riscv_vle16_v_u16m1(const xnn_bfloat16* p, size_t vl) {
    return __riscv_vle16_v_u16m1(reinterpret_cast<const uint16_t*>(p), vl);
}
inline vuint16m1_t __riscv_vle16_v_u16m1_tu(const vuint16m1_t& merge,
                                              const xnn_bfloat16* p, size_t vl) {
    return __riscv_vle16_v_u16m1_tu(merge, reinterpret_cast<const uint16_t*>(p), vl);
}
inline void __riscv_vse16_v_u16m1(xnn_bfloat16* p, const vuint16m1_t& v, size_t vl) {
    __riscv_vse16_v_u16m1(reinterpret_cast<uint16_t*>(p), v, vl);
}

// --- LMUL truncate (no-op type cast) -------------------------------------
inline vuint32m1_t __riscv_vlmul_trunc_v_u32m2_u32m1(const vuint32m2_t& a) { return a; }

// --- FP32 broadcast / min / max (m1) -------------------------------------
inline vfloat32m1_t __riscv_vfmv_v_f_f32m1(float src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, src));
    return RVVVector(tm, 32, std::vector<Term>(vl, bv));
}

// vsetvl_e32m1: VLMAX clamp matching the RVV spec (clamp to ≥1 to defend
// against vlen=0/1 CLI bugs).  Mirrors the bitwuzla side at line 128.
inline size_t __riscv_vsetvl_e32m1(size_t avl) { return _rvv_vsetvl(avl, 32, 1); }

// vle32: load vl fp32 lanes from the registered buffer.
inline vfloat32m1_t __riscv_vle32_v_f32m1(const float* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 32);
}

// vfmul_vv_f32m1: lane-wise fp32 multiply.  Used by f32-rsum's RMW.
inline vfloat32m1_t __riscv_vfmul_vv_f32m1(const vfloat32m1_t& a,
                                             const vfloat32m1_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_MULT, vl);
}

// vse32_v_f32m1: store vl fp32 lanes into the registered buffer at the bound
// pointer's offset.
inline void __riscv_vse32_v_f32m1(float* p, const vfloat32m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    // RVVVector storeRVV iterates v.getVL() lanes; we only want vl, so trim.
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 32, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}

// vle32 / vse32 for u32m1 — used by transposec RVV variants.
inline vuint32m1_t __riscv_vle32_v_u32m1(const uint32_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 32);
}
inline void __riscv_vse32_v_u32m1(uint32_t* p, const vuint32m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 32, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}

// vle/vse for u8m1 and u64m1 — used by x8/x64-transposec RVV variants.
// u64m1 alias added here since it isn't declared elsewhere on the cvc5 side.
using vuint64m1_t = RVVVector;
inline vuint8m1_t __riscv_vle8_v_u8m1(const uint8_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 8);
}
inline void __riscv_vse8_v_u8m1(uint8_t* p, const vuint8m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 8, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}
inline vuint64m1_t __riscv_vle64_v_u64m1(const uint64_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 64);
}
inline void __riscv_vse64_v_u64m1(uint64_t* p, const vuint64m1_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    std::vector<Term> lanes; lanes.reserve(vl);
    for (size_t i = 0; i < vl; i++) lanes.push_back(v.getElement(i));
    RVVVector trimmed(g_ctx->tm, 64, lanes);
    b.storeRVV(b.ptrToByteOffset(p), trimmed);
}

// vfadd_vv_f32m1_tu: tail-undisturbed add — lanes [0, vl) get a[i]+b[i],
// lanes [vl, dst.getVL()) keep dst's value.  Used by f32-rsum's main loop.
inline vfloat32m1_t __riscv_vfadd_vv_f32m1_tu(const vfloat32m1_t& dst,
                                                const vfloat32m1_t& a,
                                                const vfloat32m1_t& b,
                                                size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) {
            Term af = rvv_load_as_fp32(tm, a.getElement(i));
            Term bf = rvv_load_as_fp32(tm, b.getElement(i));
            Term sf = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
            r.push_back(rvv_store_fp32_as_bv(tm, sf));
        } else {
            r.push_back(dst.getElement(i));
        }
    }
    return RVVVector(tm, 32, r);
}

// vfadd_vv_f32m8_tu: same shape, m8 LMUL.  Used by the LLM-generated f32-rsum
// translation that batches 8x register groups.
inline vfloat32m8_t __riscv_vfadd_vv_f32m8_tu(const vfloat32m8_t& dst,
                                                const vfloat32m8_t& a,
                                                const vfloat32m8_t& b,
                                                size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) {
            Term af = rvv_load_as_fp32(tm, a.getElement(i));
            Term bf = rvv_load_as_fp32(tm, b.getElement(i));
            Term sf = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
            r.push_back(rvv_store_fp32_as_bv(tm, sf));
        } else {
            r.push_back(dst.getElement(i));
        }
    }
    return RVVVector(tm, 32, r);
}

// vfadd_vv_f32m4_tu / m2_tu: same shape as m1/m8 above, m4/m2 LMUL.  Used by
// raddstoreexpminusmax's `vsum` accumulate (rvv-rr2-p6, u4v=m4 / u2v=m2).
inline vfloat32m4_t __riscv_vfadd_vv_f32m4_tu(const vfloat32m4_t& dst,
                                                const vfloat32m4_t& a,
                                                const vfloat32m4_t& b,
                                                size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) {
            Term af = rvv_load_as_fp32(tm, a.getElement(i));
            Term bf = rvv_load_as_fp32(tm, b.getElement(i));
            Term sf = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
            r.push_back(rvv_store_fp32_as_bv(tm, sf));
        } else {
            r.push_back(dst.getElement(i));
        }
    }
    return RVVVector(tm, 32, r);
}

inline vfloat32m2_t __riscv_vfadd_vv_f32m2_tu(const vfloat32m2_t& dst,
                                                const vfloat32m2_t& a,
                                                const vfloat32m2_t& b,
                                                size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) {
            Term af = rvv_load_as_fp32(tm, a.getElement(i));
            Term bf = rvv_load_as_fp32(tm, b.getElement(i));
            Term sf = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, af, bf});
            r.push_back(rvv_store_fp32_as_bv(tm, sf));
        } else {
            r.push_back(dst.getElement(i));
        }
    }
    return RVVVector(tm, 32, r);
}

// vadd_vv_{i32,u32}m8_tu: tail-undisturbed integer add — lanes [0, vl) get
// a[i]+b[i], lanes [vl, dst.getVL()) keep dst's value.  The int twin of
// vfadd_vv_f32m8_tu above; used by qs8/qu8-rsum's accumulator loop.
inline vint32m8_t __riscv_vadd_vv_i32m8_tu(const vint32m8_t& dst,
                                           const vint32m8_t& a,
                                           const vint32m8_t& b,
                                           size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) r.push_back(tm.mkTerm(Kind::BITVECTOR_ADD, {a.getElement(i), b.getElement(i)}));
        else        r.push_back(dst.getElement(i));
    }
    return RVVVector(tm, 32, r);
}
inline vuint32m8_t __riscv_vadd_vv_u32m8_tu(const vuint32m8_t& dst,
                                            const vuint32m8_t& a,
                                            const vuint32m8_t& b,
                                            size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(dst.getVL());
    for (size_t i = 0; i < dst.getVL(); i++) {
        if (i < vl) r.push_back(tm.mkTerm(Kind::BITVECTOR_ADD, {a.getElement(i), b.getElement(i)}));
        else        r.push_back(dst.getElement(i));
    }
    return RVVVector(tm, 32, r);
}

// vfredusum_vs_f32m8_f32m1: unordered-sum reduction.  Folds vlmax fp32 lanes
// of `vec` into lane 0, starting from `init.lane(0)`.  Output is m1 (1 active
// lane = the sum).  Order-of-summation is unspecified; we pick left-to-right
// for symbolic reasoning, matching what most RVV cores do.
inline vfloat32m1_t __riscv_vfredusum_vs_f32m8_f32m1(const vfloat32m8_t& vec,
                                                       const vfloat32m1_t& init,
                                                       size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    Term acc_fp = rvv_load_as_fp32(tm, init.getElement(0));
    for (size_t i = 0; i < vl; i++) {
        Term lane_fp = rvv_load_as_fp32(tm, vec.getElement(i));
        acc_fp = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, acc_fp, lane_fp});
    }
    Term acc_bv = rvv_store_fp32_as_bv(tm, acc_fp);
    // Result is an m1 vector.  Lane 0 holds the sum; tail lanes match init.
    std::vector<Term> r; r.reserve(init.getVL());
    r.push_back(acc_bv);
    for (size_t i = 1; i < init.getVL(); i++) r.push_back(init.getElement(i));
    return RVVVector(tm, 32, r);
}

// vfmv_f_s: extract lane 0 as a scalar float.  Concrete return value is
// unused in symbolic mode; the SymbolicScalar<float> side channel records the
// term in g_scalar_terms keyed by the destination address (same pattern as
// the NEON vget_lane_f32 above).
inline float __riscv_vfmv_f_s_f32m1_f32(const vfloat32m1_t& a) { (void)a; return 0.0f; }
inline vfloat32m1_t __riscv_vfmin_vv_f32m1(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat32m1_t __riscv_vfmax_vv_f32m1(const vfloat32m1_t& a, const vfloat32m1_t& b, size_t vl) {
    return rvv_fp32_binop(a, b, Kind::FLOATINGPOINT_MAX, vl);
}

// --- vmerge.vvm (f32m1): delegate to rvv_vmerge_vvm_impl.
inline vfloat32m1_t __riscv_vmerge_vvm_f32m1(const vfloat32m1_t& merge, const vfloat32m1_t& src,
                                               const vbool32_t& mask, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, src, mask, vl, 32);
}

// --- u16mf2 family (used by the strict-Arm BFCVTN narrow path) ----------
// vncvt.x.x.w (u32m1 → u16mf2): low-16 narrow (extract bits [15:0]).
inline vuint16mf2_t __riscv_vncvt_x_x_w_u16mf2(const vuint32m1_t& a, size_t vl) {
    auto& tm = g_ctx->tm;
    Op extract16 = tm.mkOp(Kind::BITVECTOR_EXTRACT, {15u, 0u});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(tm.mkTerm(extract16, {a.getElement(i)}));
    return RVVVector(tm, 16, r);
}
// vor.vx (u16mf2) — element-wise OR with 16-bit scalar.
inline vuint16mf2_t __riscv_vor_vx_u16mf2(const vuint16mf2_t& a, uint16_t b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = mk_bv_val(tm, 16, (int64_t)b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvor(tm, a.getElement(i), bv));
    return RVVVector(tm, 16, r);
}
// vmerge.vvm (u16mf2): mask SEW=32 for mf2 LMUL (RVV ratio rule —
// SEW/LMUL = 16/(1/2) = 32, so mask uses vbool32).
inline vuint16mf2_t __riscv_vmerge_vvm_u16mf2(const vuint16mf2_t& merge, const vuint16mf2_t& src,
                                                const vbool32_t& mask, size_t vl) {
    return rvv_vmerge_vvm_impl(merge, src, mask, vl, 16);
}
// vmerge.vxm (u16mf2) — vector-scalar variant.
inline vuint16mf2_t __riscv_vmerge_vxm_u16mf2(const vuint16mf2_t& merge,
                                                uint16_t b,
                                                const vbool32_t& mask, size_t vl) {
    return rvv_vmerge_vxm_impl(merge, (int64_t)b, mask, vl, 16);
}
// vle16 / vse16 at u16mf2.
inline vuint16mf2_t __riscv_vle16_v_u16mf2(const uint16_t* p, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    return b.loadRVV(b.ptrToByteOffset(p), vl, 16);
}
inline void __riscv_vse16_v_u16mf2(uint16_t* p, const vuint16mf2_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    b.storeRVV(b.ptrToByteOffset(p), v);
}

// --- vmsltu.vx (u16m1, unsigned less-than scalar → b16) — delegates to impl.
inline MaskVector __riscv_vmsltu_vx_u16m1_b16(const vuint16m1_t& a, uint16_t b, size_t vl) {
    return rvv_vmsltu_vx_impl(a, b, vl, 16);
}

// --- vfwmacc.vv (f64m2): widening fused multiply-accumulate.
// vd[i] (fp64) += widen(vs1[i] fp32) * widen(vs2[i] fp32). The widening
// makes the multiply exact for any finite fp32 operands and lets the sum
// stay in fp64 range, avoiding fp32 mid-computation overflow.
inline vfloat64m2_t __riscv_vfwmacc_vv_f64m2(const vfloat64m2_t& vd,
                                              const vfloat32m1_t& vs1,
                                              const vfloat32m1_t& vs2,
                                              size_t vl) {
    auto& tm = g_ctx->tm;
    Term rm = g_ctx->fp.rounding_mode;
    Op cast = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_FP, {11, 53});
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af32 = rvv_load_as_fp32(tm, vs1.getElement(i));
        Term bf32 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term af64 = tm.mkTerm(cast, {rm, af32});  // exact widen (fp32 ⊂ fp64)
        Term bf64 = tm.mkTerm(cast, {rm, bf32});  // exact widen
        Term mul  = tm.mkTerm(Kind::FLOATINGPOINT_MULT, {rm, af64, bf64});
        Term acc  = rvv_load_as_fp64(tm, vd.getElement(i));
        Term sum  = tm.mkTerm(Kind::FLOATINGPOINT_ADD, {rm, acc, mul});
        r.push_back(rvv_store_fp64_as_bv(tm, sum));
    }
    return RVVVector(tm, 64, r);
}

// --- vslidedown.vx (f64m2) — slide a 64-bit lane vector down by `off`.
inline vfloat64m2_t __riscv_vslidedown_vx_f64m2(const vfloat64m2_t& a,
                                                  size_t off, size_t vl) {
    return rvv_vslidedown_impl(a, off, vl, 64);
}

// --- vmandn.mm (b32) — mask bitwise AND-NOT (a AND NOT b) ----------------
inline MaskVector __riscv_vmandn_mm_b32(const vbool32_t& a, const vbool32_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term nb = fold_bvnot(tm, b.getBit(i));
        bits.push_back(fold_bvand(tm, a.getBit(i), nb));
    }
    return MaskVector(tm, bits);
}

// --- vor.vv (u32m1) — element-wise vector OR -----------------------------
inline vuint32m1_t __riscv_vor_vv_u32m1(const vuint32m1_t& a, const vuint32m1_t& b, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++)
        r.push_back(fold_bvor(tm, a.getElement(i), b.getElement(i)));
    return RVVVector(tm, 32, r);
}

// --- f32m1 vector-scalar FP min/max (concrete-float overloads) ---------
inline vfloat32m1_t __riscv_vfmin_vf_f32m1(const vfloat32m1_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b),
                              Kind::FLOATINGPOINT_MIN, vl);
}
inline vfloat32m1_t __riscv_vfmax_vf_f32m1(const vfloat32m1_t& a, float b, size_t vl) {
    return rvv_fp32_binop_vf(a, mk_fp32_from_float(g_ctx->tm, b),
                              Kind::FLOATINGPOINT_MAX, vl);
}

// =============================================================================
// f32m2 family — extra m2 intrinsics for f32-conv-hwc2chw (rvv-2x1).
// =============================================================================
inline vfloat32m2_t __riscv_vfmv_v_f_f32m2(float src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, src));
    return RVVVector(tm, 32, std::vector<Term>(vl, bv));
}
inline vfloat32m2_t __riscv_vfmacc_vf_f32m2(const vfloat32m2_t& vd, float rs1,
                                              const vfloat32m2_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term rs1_fp = mk_fp32_from_float(tm, rs1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, rs1_fp, v2, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m2_t __riscv_vfmin_vf_f32m2(const vfloat32m2_t& a, float b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bf = mk_fp32_from_float(tm, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        r.push_back(rvv_store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MIN, {af, bf})));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m2_t __riscv_vfmax_vf_f32m2(const vfloat32m2_t& a, float b, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bf = mk_fp32_from_float(tm, b);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term af = rvv_load_as_fp32(tm, a.getElement(i));
        r.push_back(rvv_store_fp32_as_bv(tm, tm.mkTerm(Kind::FLOATINGPOINT_MAX, {af, bf})));
    }
    return RVVVector(tm, 32, r);
}
inline void __riscv_vse32_v_f32m2(float* p, const vfloat32m2_t& v, size_t vl) {
    auto& b = g_ctx->findBuffer(p);
    size_t off = b.ptrToByteOffset(p);
    for (size_t i = 0; i < vl; i++) b.storeScalar(off + i * 4, v.getElement(i), 32);
}
// vlse32 strided load (stride in bytes); per-lane findBuffer (see f32m1 above).
inline vfloat32m2_t __riscv_vlse32_v_f32m2(const float* p, ptrdiff_t stride, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        const float* lp = (const float*)((uintptr_t)p + i * (size_t)stride);
        auto& b = g_ctx->findBuffer(lp);
        r.push_back(b.loadScalar(b.ptrToByteOffset(lp), 32));
    }
    return RVVVector(tm, 32, r);
}
// vmseq_vx_u32m2_b16: r[i] = (a[i] == s) ? 1 : 0
inline vbool16_t __riscv_vmseq_vx_u32m2_b16(const vuint32m2_t& a, uint32_t s, size_t vl) {
    auto& tm = g_ctx->tm; Term sv = mk_bv_val(tm, 32, (int64_t)(uint64_t)s);
    std::vector<Term> bits; bits.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term cmp = tm.mkTerm(Kind::EQUAL, {a.getElement(i), sv});
        bits.push_back(fold_ite(tm, cmp, mk_bv_val(tm, 1, 1), mk_bv_val(tm, 1, 0)));
    }
    return MaskVector(tm, bits);
}
// vsetvlmax for f32m2 — same lmul=2 logic as vsetvl with avl=SIZE_MAX.
inline size_t __riscv_vsetvlmax_e32m2() { return _rvv_vsetvl((size_t)-1, 32, 2); }
// vle32_v_f32m2 — 16-byte (vlmax) load from memory.
inline vfloat32m2_t __riscv_vle32_v_f32m2(const float* p, size_t vl) {
    auto& tm = g_ctx->tm;
    auto& b  = g_ctx->findBuffer(p);
    std::vector<Term> r; r.reserve(vl);
    size_t off = b.ptrToByteOffset(p);
    for (size_t i = 0; i < vl; i++) r.push_back(b.loadScalar(off + i * 4, 32));
    return RVVVector(tm, 32, r);
}
// vfslide1down: r[i] = a[i+1] for i < vl-1; r[vl-1] = scalar
inline vfloat32m2_t __riscv_vfslide1down_vf_f32m2(const vfloat32m2_t& a, float scalar, size_t vl) {
    auto& tm = g_ctx->tm;
    Term s_bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, scalar));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    if (vl > 0) r.push_back(s_bv);
    return RVVVector(tm, 32, r);
}
// vfslide1up: r[0] = scalar; r[i] = a[i-1] for i>0
inline vfloat32m2_t __riscv_vfslide1up_vf_f32m2(const vfloat32m2_t& a, float scalar, size_t vl) {
    auto& tm = g_ctx->tm;
    Term s_bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, scalar));
    std::vector<Term> r; r.reserve(vl);
    if (vl > 0) r.push_back(s_bv);
    for (size_t i = 1; i < vl; i++) r.push_back(a.getElement(i - 1));
    return RVVVector(tm, 32, r);
}
// vslidedown_vx: r[i] = a[i + s] when in range, undef beyond
inline vfloat32m2_t __riscv_vslidedown_vx_f32m2(const vfloat32m2_t& a, size_t s, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        if (i + s < vl) r.push_back(a.getElement(i + s));
        else r.push_back(mk_bv_val(tm, 32, 0));
    }
    return RVVVector(tm, 32, r);
}
// vfmv_f_s_f32m2_f32: extract first lane as float (returns Term — not exact match but works for symbolic flow)
inline float __riscv_vfmv_f_s_f32m2_f32(const vfloat32m2_t& a) {
    // Pure-symbolic context can't return concrete float; return 0.0 — kernel uses
    // it for boundary slide setup which has no observable effect on verification
    // since both NEON and RVV produce the same slide pattern.
    (void) a;
    return 0.0f;
}

// =============================================================================
// f32m4 family — extra m4 intrinsics for f32-dwconv2d-chw (rvv-3x3p1-4x4).
// =============================================================================
inline vfloat32m4_t __riscv_vfmv_v_f_f32m4(float src, size_t vl) {
    auto& tm = g_ctx->tm;
    Term bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, src));
    return RVVVector(tm, 32, std::vector<Term>(vl, bv));
}
inline vfloat32m4_t __riscv_vfmacc_vf_f32m4(const vfloat32m4_t& vd, float rs1,
                                              const vfloat32m4_t& vs2, size_t vl) {
    auto& tm = g_ctx->tm; Term rm = g_ctx->fp.rounding_mode;
    Term rs1_fp = mk_fp32_from_float(tm, rs1);
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        Term vd_fp = rvv_load_as_fp32(tm, vd.getElement(i));
        Term v2 = rvv_load_as_fp32(tm, vs2.getElement(i));
        Term res = tm.mkTerm(Kind::FLOATINGPOINT_FMA, {rm, rs1_fp, v2, vd_fp});
        r.push_back(rvv_store_fp32_as_bv(tm, res));
    }
    return RVVVector(tm, 32, r);
}
inline vfloat32m4_t __riscv_vfslide1down_vf_f32m4(const vfloat32m4_t& a, float scalar, size_t vl) {
    auto& tm = g_ctx->tm;
    Term s_bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, scalar));
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i + 1 < vl; i++) r.push_back(a.getElement(i + 1));
    if (vl > 0) r.push_back(s_bv);
    return RVVVector(tm, 32, r);
}
inline vfloat32m4_t __riscv_vfslide1up_vf_f32m4(const vfloat32m4_t& a, float scalar, size_t vl) {
    auto& tm = g_ctx->tm;
    Term s_bv = rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm, scalar));
    std::vector<Term> r; r.reserve(vl);
    if (vl > 0) r.push_back(s_bv);
    for (size_t i = 1; i < vl; i++) r.push_back(a.getElement(i - 1));
    return RVVVector(tm, 32, r);
}
inline vfloat32m4_t __riscv_vslidedown_vx_f32m4(const vfloat32m4_t& a, size_t s, size_t vl) {
    auto& tm = g_ctx->tm;
    std::vector<Term> r; r.reserve(vl);
    for (size_t i = 0; i < vl; i++) {
        if (i + s < vl) r.push_back(a.getElement(i + s));
        else r.push_back(mk_bv_val(tm, 32, 0));
    }
    return RVVVector(tm, 32, r);
}
inline float __riscv_vfmv_f_s_f32m4_f32(const vfloat32m4_t& a) {
    (void) a;
    return 0.0f;
}

} // namespace salt_cvc5
