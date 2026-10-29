#pragma once
// RVV single-width FP arithmetic — add/sub/mul/div/rsub/rdiv/min/max/neg/abs/sgnj(n/x) (cvc5).
// vv and vf forms over f16/f32/f64; lanes hold raw IEEE bits in a BV.
#include "../intrinsics.hpp"
namespace salt_cvc5 {

enum GfaOp { G_ADD,G_SUB,G_MUL,G_DIV,G_RSUB,G_RDIV,G_MIN,G_MAX,G_NEG,G_ABS,G_SGNJ,G_SGNJN,G_SGNJX };

// raw BV <-> FP for a given precision (16/32/64)
inline Term _gfa_load_fp(TermManager& tm, size_t p, Term bv){
  if(p==16) return rvv_load_as_fp16(tm,bv);
  if(p==32) return rvv_load_as_fp32(tm,bv);
  return rvv_load_as_fp64(tm,bv);
}
inline Term _gfa_store_fp(TermManager& tm, size_t p, Term fp){
  if(p==16) return rvv_store_fp16_as_bv(tm,fp);
  if(p==32) return rvv_store_fp32_as_bv(tm,fp);
  return rvv_store_fp64_as_bv(tm,fp);
}
// scalar f16/f32/f64 -> raw IEEE BV (p bits)
inline Term _gfa_scalar_bv(TermManager& tm, size_t p, salt_float16 v){ return rvv_store_fp16_as_bv(tm, mk_fp16_from_f16(tm,v)); }
inline Term _gfa_scalar_bv(TermManager& tm, size_t p, float v){ return rvv_store_fp32_as_bv(tm, mk_fp32_from_float(tm,v)); }
inline Term _gfa_scalar_bv(TermManager& tm, size_t p, double v){
  uint64_t bits; std::memcpy(&bits,&v,8);
  return tm.mkBitVector(64,(uint64_t)bits);
}

// FP add/sub/mul/div/min/max/neg/abs on raw BV lanes
inline Term _gfa_fp_lane(TermManager& tm, size_t p, Term abv, Term bbv, GfaOp op){
  Term rm=g_ctx->fp.rounding_mode;
  Term af=_gfa_load_fp(tm,p,abv);
  Term res;
  switch(op){
    case G_ADD: res=tm.mkTerm(Kind::FLOATINGPOINT_ADD,{rm,af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_SUB: res=tm.mkTerm(Kind::FLOATINGPOINT_SUB,{rm,af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_MUL: res=tm.mkTerm(Kind::FLOATINGPOINT_MULT,{rm,af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_DIV: res=tm.mkTerm(Kind::FLOATINGPOINT_DIV,{rm,af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_RSUB:res=tm.mkTerm(Kind::FLOATINGPOINT_SUB,{rm,_gfa_load_fp(tm,p,bbv),af}); break;
    case G_RDIV:res=tm.mkTerm(Kind::FLOATINGPOINT_DIV,{rm,_gfa_load_fp(tm,p,bbv),af}); break;
    case G_MIN: res=tm.mkTerm(Kind::FLOATINGPOINT_MIN,{af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_MAX: res=tm.mkTerm(Kind::FLOATINGPOINT_MAX,{af,_gfa_load_fp(tm,p,bbv)}); break;
    case G_NEG: res=tm.mkTerm(Kind::FLOATINGPOINT_NEG,{af}); break;
    case G_ABS: res=tm.mkTerm(Kind::FLOATINGPOINT_ABS,{af}); break;
    default: res=af; break;
  }
  return _gfa_store_fp(tm,p,res);
}
// sign-injection: exact BV splice. result = {sign, magnitude_bits_of_a}
inline Term _gfa_sgnj_lane(TermManager& tm, size_t p, Term abv, Term bbv, GfaOp op){
  size_t msb=p-1;
  Term asign=fold_bvextract(tm,msb,msb,abv);
  Term bsign=fold_bvextract(tm,msb,msb,bbv);
  Term mag=fold_bvextract(tm,msb-1,0,abv);
  Term sign;
  if(op==G_SGNJ)       sign=bsign;
  else if(op==G_SGNJN) sign=fold_bvnot(tm,bsign);
  else                 sign=fold_bvxor(tm,asign,bsign); // G_SGNJX
  return fold_bvconcat(tm,sign,mag);
}
inline Term _gfa_lane(TermManager& tm, size_t p, Term abv, Term bbv, GfaOp op){
  if(op==G_SGNJ||op==G_SGNJN||op==G_SGNJX) return _gfa_sgnj_lane(tm,p,abv,bbv,op);
  return _gfa_fp_lane(tm,p,abv,bbv,op);
}
inline RVVVector _gfa_vv(const RVVVector& a, const RVVVector& b, size_t p, GfaOp op, size_t vl){
  auto& tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(_gfa_lane(tm,p,a.getElement(i),b.getElement(i),op));
  return RVVVector(tm,p,r);
}
inline RVVVector _gfa_vf(const RVVVector& a, Term sbv, size_t p, GfaOp op, size_t vl){
  auto& tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(_gfa_lane(tm,p,a.getElement(i),sbv,op));
  return RVVVector(tm,p,r);
}
inline RVVVector _gfa_v(const RVVVector& a, size_t p, GfaOp op, size_t vl){
  auto& tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(_gfa_fp_lane(tm,p,a.getElement(i),a.getElement(i),op));
  return RVVVector(tm,p,r);
}

inline RVVVector __riscv_vfabs_v_f16m1(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f16m2(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f16mf2(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f16mf4(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f32m1(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f32m2(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f32m4(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f32m8(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f32mf2(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f64m1(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f64m2(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f64m4(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_ABS,vl); }
inline RVVVector __riscv_vfabs_v_f64m8(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_ABS,vl); }
inline RVVVector __riscv_vfadd_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_ADD,vl); }
inline RVVVector __riscv_vfadd_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_ADD,vl); }
inline RVVVector __riscv_vfdiv_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_DIV,vl); }
inline RVVVector __riscv_vfdiv_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_DIV,vl); }
inline RVVVector __riscv_vfmax_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MAX,vl); }
inline RVVVector __riscv_vfmax_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MAX,vl); }
inline RVVVector __riscv_vfmin_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MIN,vl); }
inline RVVVector __riscv_vfmin_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MIN,vl); }
inline RVVVector __riscv_vfmul_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MUL,vl); }
inline RVVVector __riscv_vfmul_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_MUL,vl); }
inline RVVVector __riscv_vfneg_v_f16m2(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f16m4(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f16m8(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f16mf2(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f16mf4(const RVVVector& a, size_t vl){ return _gfa_v(a,16,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f32m8(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f32mf2(const RVVVector& a, size_t vl){ return _gfa_v(a,32,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f64m1(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f64m2(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f64m4(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_NEG,vl); }
inline RVVVector __riscv_vfneg_v_f64m8(const RVVVector& a, size_t vl){ return _gfa_v(a,64,G_NEG,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RDIV,vl); }
inline RVVVector __riscv_vfrdiv_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RDIV,vl); }
inline RVVVector __riscv_vfrsub_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RSUB,vl); }
inline RVVVector __riscv_vfrsub_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_RSUB,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f32m8_mu(const MaskVector& mask, const RVVVector& merge, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_vmerge_vvm_impl(merge,_gfa_vv(a,b,32,G_SGNJ,vl),mask,vl,32); }
inline RVVVector __riscv_vfsgnj_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnj_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJ,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjn_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJN,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f32m8(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsgnjx_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SGNJX,vl); }
inline RVVVector __riscv_vfsub_vf_f16m1(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f16m2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f16m4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f16m8(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f16mf2(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f16mf4(const RVVVector& a, salt_float16 b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,16,b),16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f32m1(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f32m2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f32m4(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f32mf2(const RVVVector& a, float b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,32,b),32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f64m1(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f64m2(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f64m4(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vf_f64m8(const RVVVector& a, double b, size_t vl){ return _gfa_vf(a,_gfa_scalar_bv(g_ctx->tm,64,b),64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,16,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,32,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SUB,vl); }
inline RVVVector __riscv_vfsub_vv_f64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gfa_vv(a,b,64,G_SUB,vl); }

} // namespace salt_cvc5
