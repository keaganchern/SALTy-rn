#pragma once
// RVV policy variants of base intrinsics defined in the other family files (cvc5),
// following the RVV intrinsics v1.0 policy rules:
//   _tu    lanes < vl from the op; lanes in [vl, vd.VL) keep vd
//   _mu    masked-off lanes < vl keep maskedoff (tail agnostic)
//   _tumu  both
//   _m     masked-off lanes are agnostic: fresh unconstrained values, so a kernel
//          whose output depends on them does not verify
//   _rm    the op under an explicit rounding mode instead of frm
// Masked loads and stores never touch inactive elements, as in hardware (an
// inactive lane past the end of a buffer must not be read or written).
#include "../intrinsics.hpp"
#include "core.hpp"
#include "fixedpoint.hpp"
#include "fp_arith.hpp"
#include "fp_cvt.hpp"
#include "fp_fma.hpp"
#include "fp_special.hpp"
#include "init.hpp"
#include "int_arith.hpp"
#include "mem_unit.hpp"
#include "widening.hpp"
namespace salt_cvc5 {

inline Term _pol_agnostic(size_t bits) {
  static thread_local unsigned n = 0;
  auto& tm = g_ctx->tm;
  return tm.mkConst(tm.mkBitVectorSort(bits), "agnostic" + std::to_string(n++));
}
inline Term _pol_active(const MaskVector& mask, size_t i) {
  auto& tm = g_ctx->tm;
  return fold_eq(tm, mask.getBit(i), mk_bv_val(tm, 1, 1));
}
inline bool _pol_inactive(const MaskVector& mask, size_t i) {
  Term a = _pol_active(mask, i);
  return a.isBooleanValue() && !a.getBooleanValue();
}
inline RVVVector _pol_tumu(const RVVVector& vd, const RVVVector& body, const MaskVector& mask,
                           size_t vl, size_t bits) {
  return rvv_tu_impl(vd, rvv_vmerge_vvm_impl(vd, body, mask, vl, bits), vl, bits);
}
inline RVVVector _pol_m(const RVVVector& body, const MaskVector& mask, size_t vl, size_t bits) {
  auto& tm = g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for (size_t i = 0; i < vl; i++)
    r.push_back(fold_ite(tm, _pol_active(mask, i), body.getElement(i), _pol_agnostic(bits)));
  return RVVVector(tm, bits, r);
}
// Masked load: active lanes read memory; inactive lanes keep `merge` and are not read.
inline RVVVector _pol_masked_load(const void* base, size_t bits, const MaskVector& mask,
                                  const RVVVector& merge, size_t vl) {
  auto& tm = g_ctx->tm; auto& b = g_ctx->findBuffer(base); size_t o = b.ptrToByteOffset(base);
  std::vector<Term> r; r.reserve(vl);
  for (size_t i = 0; i < vl; i++) {
    Term keep = i < merge.getVL() ? merge.getElement(i) : _pol_agnostic(bits);
    if (_pol_inactive(mask, i)) { r.push_back(keep); continue; }
    Term v = bits == 8 ? b.getByte(o + i) : b.loadScalar(o + i * (bits / 8), bits);
    r.push_back(fold_ite(tm, _pol_active(mask, i), v, keep));
  }
  return RVVVector(tm, bits, r);
}
// Masked store: inactive elements leave memory untouched.
inline void _pol_masked_store(void* base, const RVVVector& v, size_t bits, const MaskVector& mask,
                              size_t vl) {
  auto& tm = g_ctx->tm; auto& b = g_ctx->findBuffer(base); size_t o = b.ptrToByteOffset(base);
  for (size_t i = 0; i < vl; i++) {
    if (_pol_inactive(mask, i)) continue;
    size_t off = o + i * (bits / 8);
    Term act = _pol_active(mask, i), val = v.getElement(i);
    if (!(act.isBooleanValue() && act.getBooleanValue()))   // symbolic mask: inactive keeps old bytes
      val = fold_ite(tm, act, val, b.loadScalar(off, bits));
    b.storeScalar(off, val, bits);
  }
}
// The conversions read g_ctx->fp.rounding_mode; set it from frm for one call.
struct _PolFrm {
  Term saved;
  explicit _PolFrm(unsigned frm) : saved(g_ctx->fp.rounding_mode) {
    static const RoundingMode modes[] = {
      RoundingMode::ROUND_NEAREST_TIES_TO_EVEN, RoundingMode::ROUND_TOWARD_ZERO,
      RoundingMode::ROUND_TOWARD_NEGATIVE, RoundingMode::ROUND_TOWARD_POSITIVE,
      RoundingMode::ROUND_NEAREST_TIES_TO_AWAY};
    if (frm > 4) throw std::runtime_error("unsupported frm " + std::to_string(frm));
    g_ctx->fp.rounding_mode = g_ctx->tm.mkRoundingMode(modes[frm]);
  }
  ~_PolFrm() { g_ctx->fp.rounding_mode = saved; }
};

// --- _tu ---------------------------------------------------------------------
inline RVVVector __riscv_vwaddu_wv_u16m4_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vwaddu_wv_u16m4(a,b,vl),vl,16); }
inline RVVVector __riscv_vwaddu_wv_u16m8_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vwaddu_wv_u16m8(a,b,vl),vl,16); }
inline RVVVector __riscv_vwaddu_wv_u32m8_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vwaddu_wv_u32m8(a,b,vl),vl,32); }
inline RVVVector __riscv_vwadd_wv_i16m8_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vwadd_wv_i16m8(a,b,vl),vl,16); }
inline RVVVector __riscv_vwadd_wv_i32m8_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vwadd_wv_i32m8(a,b,vl),vl,32); }
inline RVVVector __riscv_vwmaccu_vx_u32m8_tu(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return rvv_tu_impl(vd,__riscv_vwmaccu_vx_u32m8(vd,x,y,vl),vl,32); }
inline RVVVector __riscv_vwmacc_vx_i32m8_tu(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return rvv_tu_impl(vd,__riscv_vwmacc_vx_i32m8(vd,x,y,vl),vl,32); }
inline RVVVector __riscv_vadd_vv_u16m4_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vadd_vv_u16m4(a,b,vl),vl,16); }
inline RVVVector __riscv_vadd_vv_i16m8_tu(const RVVVector& vd, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(vd,__riscv_vadd_vv_i16m8(a,b,vl),vl,16); }
inline RVVVector __riscv_vsll_vx_i32m8_tu(const RVVVector& vd, const RVVVector& a, size_t shift, size_t vl){ return rvv_tu_impl(vd,__riscv_vsll_vx_i32m8(a,shift,vl),vl,32); }
inline RVVVector __riscv_vzext_vf2_u16m8_tu(const RVVVector& vd, const RVVVector& a, size_t vl){ return rvv_tu_impl(vd,__riscv_vzext_vf2_u16m8(a,vl),vl,16); }
inline RVVVector __riscv_vzext_vf4_u32m8_tu(const RVVVector& vd, const RVVVector& a, size_t vl){ return rvv_tu_impl(vd,__riscv_vzext_vf4_u32m8(a,vl),vl,32); }
inline RVVVector __riscv_vnclip_wx_i16m4_tu(const RVVVector& vd, const RVVVector& a, size_t shift, unsigned vxrm, size_t vl){ return rvv_tu_impl(vd,__riscv_vnclip_wx_i16m4(a,shift,vxrm,vl),vl,16); }
inline RVVVector __riscv_vnclipu_wx_u8m2_tu(const RVVVector& vd, const RVVVector& a, size_t shift, unsigned vxrm, size_t vl){ return rvv_tu_impl(vd,__riscv_vnclipu_wx_u8m2(a,shift,vxrm,vl),vl,8); }
inline RVVVector __riscv_vmv_v_v_i32m8_tu(const RVVVector& vd, const RVVVector& a, size_t vl){ return rvv_tu_impl(vd,__riscv_vmv_v_v_i32m8(a,vl),vl,32); }
inline RVVVector __riscv_vmv_v_x_u32m1_tu(const RVVVector& vd, uint32_t x, size_t vl){ return rvv_tu_impl(vd,__riscv_vmv_v_x_u32m1(x,vl),vl,32); }
inline RVVVector __riscv_vmv_v_x_u32m4_tu(const RVVVector& vd, uint32_t x, size_t vl){ return rvv_tu_impl(vd,__riscv_vmv_v_x_u32m4(x,vl),vl,32); }
inline RVVVector __riscv_vle8_v_u8m2_tu(const RVVVector& vd, const uint8_t* p, size_t vl){ return rvv_tu_impl(vd,__riscv_vle8_v_u8m2(p,vl),vl,8); }
inline RVVVector __riscv_vle8_v_i8m2_tu(const RVVVector& vd, const int8_t* p, size_t vl){ return rvv_tu_impl(vd,__riscv_vle8_v_i8m2(p,vl),vl,8); }
inline RVVVector __riscv_vle32_v_u32m1_tu(const RVVVector& vd, const uint32_t* p, size_t vl){ return rvv_tu_impl(vd,__riscv_vle32_v_u32m1(p,vl),vl,32); }
inline RVVVector __riscv_vle32_v_u32m4_tu(const RVVVector& vd, const uint32_t* p, size_t vl){ return rvv_tu_impl(vd,__riscv_vle32_v_u32m4(p,vl),vl,32); }
// vmv.s.x writes element 0 (if vl > 0); with _tu every other element keeps vd.
inline RVVVector __riscv_vmv_s_x_u32m1_tu(const RVVVector& vd, uint32_t x, size_t vl) {
  std::vector<Term> r(vd.elements());
  if (r.empty()) r.push_back(_pol_agnostic(32));
  if (vl > 0) r[0] = mk_bv_val(g_ctx->tm, 32, (int64_t)x);
  return RVVVector(g_ctx->tm, 32, r);
}

// --- _mu ---------------------------------------------------------------------
inline RVVVector __riscv_vor_vx_u32m4_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, uint32_t b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vor_vx_u32m4(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vor_vx_u32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, uint32_t b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vor_vx_u32m8(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vor_vv_u32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vor_vv_u32m8(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vxor_vv_i32m4_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vxor_vv_i32m4(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vxor_vv_i32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vxor_vv_i32m8(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vsmul_vx_i16m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, int16_t b, unsigned vxrm, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vsmul_vx_i16m8(a,b,vxrm,vl),m,vl,16); }
inline RVVVector __riscv_vfmul_vf_f32m4_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, float b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vfmul_vf_f32m4(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vfmul_vv_f32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vfmul_vv_f32m8(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vfsgnj_vv_f32m4_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vfsgnj_vv_f32m4(a,b,vl),m,vl,32); }
inline RVVVector __riscv_vfsqrt_v_f32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vfsqrt_v_f32m8(a,vl),m,vl,32); }
inline RVVVector __riscv_vfcvt_f_x_v_f32m8_mu(const MaskVector& m, const RVVVector& mo, const RVVVector& a, size_t vl){ return rvv_vmerge_vvm_impl(mo,__riscv_vfcvt_f_x_v_f32m8(a,vl),m,vl,32); }
inline RVVVector __riscv_vfmacc_vf_f32m1_mu(const MaskVector& m, const RVVVector& vd, float x, const RVVVector& y, size_t vl){ return rvv_vmerge_vvm_impl(vd,__riscv_vfmacc_vf_f32m1(vd,x,y,vl),m,vl,32); }
inline RVVVector __riscv_vfmacc_vf_f32m2_mu(const MaskVector& m, const RVVVector& vd, float x, const RVVVector& y, size_t vl){ return rvv_vmerge_vvm_impl(vd,__riscv_vfmacc_vf_f32m2(vd,x,y,vl),m,vl,32); }
inline RVVVector __riscv_vle32_v_u32m4_mu(const MaskVector& m, const RVVVector& mo, const uint32_t* p, size_t vl){ return _pol_masked_load(p,32,m,mo,vl); }

// --- _tumu -------------------------------------------------------------------
inline RVVVector __riscv_vfmacc_vf_f32m1_tumu(const MaskVector& m, const RVVVector& vd, float x, const RVVVector& y, size_t vl){ return _pol_tumu(vd,__riscv_vfmacc_vf_f32m1(vd,x,y,vl),m,vl,32); }
inline RVVVector __riscv_vle8_v_u8m4_tumu(const MaskVector& m, const RVVVector& mo, const uint8_t* p, size_t vl){ return rvv_tu_impl(mo,_pol_masked_load(p,8,m,mo,vl),vl,8); }

// --- _m ----------------------------------------------------------------------
inline RVVVector __riscv_vfcvt_x_f_v_i32m8_m(const MaskVector& m, const RVVVector& a, size_t vl){ return _pol_m(__riscv_vfcvt_x_f_v_i32m8(a,vl),m,vl,32); }
inline RVVVector __riscv_vfcvt_f_x_v_f32m8_m(const MaskVector& m, const RVVVector& a, size_t vl){ return _pol_m(__riscv_vfcvt_f_x_v_f32m8(a,vl),m,vl,32); }
inline RVVVector __riscv_vfmacc_vf_f32m1_m(const MaskVector& m, const RVVVector& vd, float x, const RVVVector& y, size_t vl){ return _pol_m(__riscv_vfmacc_vf_f32m1(vd,x,y,vl),m,vl,32); }
inline void __riscv_vse32_v_f32m8_m(const MaskVector& m, float* p, const RVVVector& v, size_t vl){ _pol_masked_store(p,v,32,m,vl); }
inline void __riscv_vse8_v_i8m8_m(const MaskVector& m, int8_t* p, const RVVVector& v, size_t vl){ _pol_masked_store(p,v,8,m,vl); }

// --- _rm ---------------------------------------------------------------------
inline RVVVector __riscv_vfcvt_x_f_v_i32m8_rm(const RVVVector& a, unsigned frm, size_t vl){ _PolFrm g(frm); return __riscv_vfcvt_x_f_v_i32m8(a,vl); }
inline RVVVector __riscv_vfcvt_f_x_v_f32m8_rm(const RVVVector& a, unsigned frm, size_t vl){ _PolFrm g(frm); return __riscv_vfcvt_f_x_v_f32m8(a,vl); }
inline RVVVector __riscv_vfncvt_x_f_w_i16m4_rm(const RVVVector& a, unsigned frm, size_t vl){ _PolFrm g(frm); return __riscv_vfncvt_x_f_w_i16m4(a,vl); }

} // namespace salt_cvc5
