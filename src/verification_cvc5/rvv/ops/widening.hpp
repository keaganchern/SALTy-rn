#pragma once
// RVV widening integer ops (result = 2*SEW) — generated (ns salt_cvc5).
// vwadd/sub/mul/macc (signed/unsigned/mixed), vwcvt, vzext/vsext.
#include "../intrinsics.hpp"
namespace salt_cvc5 {
inline Term _gw_ext(TermManager& tm, Term t, size_t frombits, size_t tobits, bool sgn){
  if(tobits<=frombits) return t; size_t k=tobits-frombits;
  return sgn? fold_bvsext(tm,k,t) : fold_bvzext(tm,k,t);
}
inline RVVVector _gw_bin_vv(const RVVVector&a,const RVVVector&b,size_t rb,bool sa,bool sb,bool sub,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ea=_gw_ext(tm,a.getElement(i),s,rb,sa),eb=_gw_ext(tm,b.getElement(i),s,rb,sb);
    r.push_back(tm.mkTerm(sub?Kind::BITVECTOR_SUB:Kind::BITVECTOR_ADD,{ea,eb}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_bin_wv(const RVVVector&a,const RVVVector&b,size_t rb,bool sb,bool sub,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term eb=_gw_ext(tm,b.getElement(i),s,rb,sb);
    r.push_back(tm.mkTerm(sub?Kind::BITVECTOR_SUB:Kind::BITVECTOR_ADD,{a.getElement(i),eb}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_bin_vx(const RVVVector&a,int64_t sv,size_t rb,bool sa,bool sub,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; Term sb=mk_bv_val(tm,rb,sv); std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ea=_gw_ext(tm,a.getElement(i),s,rb,sa);
    r.push_back(tm.mkTerm(sub?Kind::BITVECTOR_SUB:Kind::BITVECTOR_ADD,{ea,sb}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_bin_wx(const RVVVector&a,int64_t sv,size_t rb,bool sub,size_t vl){
  auto&tm=g_ctx->tm; Term sb=mk_bv_val(tm,rb,sv); std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(tm.mkTerm(sub?Kind::BITVECTOR_SUB:Kind::BITVECTOR_ADD,{a.getElement(i),sb}));
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_mul_vv(const RVVVector&a,const RVVVector&b,size_t rb,bool sa,bool sb,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ea=_gw_ext(tm,a.getElement(i),s,rb,sa),eb=_gw_ext(tm,b.getElement(i),s,rb,sb);
    r.push_back(tm.mkTerm(Kind::BITVECTOR_MULT,{ea,eb}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_mul_vx(const RVVVector&a,int64_t sv,size_t rb,bool sa,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; Term sb=mk_bv_val(tm,rb,sv); std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ea=_gw_ext(tm,a.getElement(i),s,rb,sa);
    r.push_back(tm.mkTerm(Kind::BITVECTOR_MULT,{ea,sb}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_macc_vv(const RVVVector&vd,const RVVVector&x,const RVVVector&y,size_t rb,bool sx,bool sy,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ex=_gw_ext(tm,x.getElement(i),s,rb,sx),ey=_gw_ext(tm,y.getElement(i),s,rb,sy);
    Term p=tm.mkTerm(Kind::BITVECTOR_MULT,{ex,ey}); r.push_back(tm.mkTerm(Kind::BITVECTOR_ADD,{vd.getElement(i),p}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_macc_vx(const RVVVector&vd,int64_t sv,const RVVVector&y,size_t rb,bool sy,size_t vl){
  auto&tm=g_ctx->tm; size_t s=rb/2; Term sb=mk_bv_val(tm,rb,sv); std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){Term ey=_gw_ext(tm,y.getElement(i),s,rb,sy);
    Term p=tm.mkTerm(Kind::BITVECTOR_MULT,{sb,ey}); r.push_back(tm.mkTerm(Kind::BITVECTOR_ADD,{vd.getElement(i),p}));}
  return RVVVector(tm,rb,r);
}
inline RVVVector _gw_unary(const RVVVector&a,size_t rb,size_t srcb,bool sgn,size_t vl){
  auto&tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(_gw_ext(tm,a.getElement(i),srcb,rb,sgn));
  return RVVVector(tm,rb,r);
}
inline RVVVector __riscv_vsext_vf2_i16m1(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vsext_vf2_i16m8(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vsext_vf2_i16mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vsext_vf2_i16mf4(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vsext_vf2_i32m1(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vsext_vf2_i32m2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vsext_vf2_i32m4(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vsext_vf2_i32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vsext_vf2_i64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vsext_vf2_i64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vsext_vf2_i64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vsext_vf2_i64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vsext_vf4_i32m2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,true,vl); }
inline RVVVector __riscv_vsext_vf4_i32m8(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,true,vl); }
inline RVVVector __riscv_vsext_vf4_i32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,true,vl); }
inline RVVVector __riscv_vsext_vf4_i64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,true,vl); }
inline RVVVector __riscv_vsext_vf4_i64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,true,vl); }
inline RVVVector __riscv_vsext_vf4_i64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,true,vl); }
inline RVVVector __riscv_vsext_vf4_i64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,true,vl); }
inline RVVVector __riscv_vsext_vf8_i64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,true,vl); }
inline RVVVector __riscv_vsext_vf8_i64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,true,vl); }
inline RVVVector __riscv_vsext_vf8_i64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,true,vl); }
inline RVVVector __riscv_vsext_vf8_i64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,true,vl); }
inline RVVVector __riscv_vwadd_vv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i16m1(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i16m8(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i16mf2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i16mf4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i32m1(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i32mf2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i64m1(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i64m2(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i64m4(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_vx_i64m8(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i16m4_tu(const RVVVector& dst, const RVVVector& a, const RVVVector& b, size_t vl){ return rvv_tu_impl(dst,_gw_bin_wv(a,b,16,true,false,vl),vl,16); }
inline RVVVector __riscv_vwadd_wv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_wv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16m1(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16m2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16m4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16m8(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16mf2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i16mf4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwadd_wx_i32m1(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwadd_wx_i32m2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwadd_wx_i32m4(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwadd_wx_i32m8(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwadd_wx_i32mf2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwadd_wx_i64m1(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwadd_wx_i64m2(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwadd_wx_i64m4(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwadd_wx_i64m8(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vv_u64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16m2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16m4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_vx_u64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_wv_u64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16m2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16m4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwaddu_wx_u64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i16m1(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i16m8(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i16mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i16mf4(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i32m1(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i32m2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i32m8(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vwcvt_x_x_v_i64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,true,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u16m8(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u16mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u16mf4(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u32m1(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u32m2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u32m8(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vwcvtu_x_x_v_u64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vwmacc_vv_i16m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i16m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i16m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i16m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i16mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i16mf4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i32m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i32mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i64m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i64m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i64m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,true,vl); }
inline RVVVector __riscv_vwmacc_vv_i64m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16m1(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16m2(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16m4(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16m8(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16mf2(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i16mf4(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i32m2(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
// Scalar activation loads must retain their symbolic value through widening.
// Replicating the 16-bit scalar uses the same signed 16x16 -> 32 MAC semantics.
inline RVVVector __riscv_vwmacc_vx_i32m2(const RVVVector& vd, SymbolicScalar<int16_t> x,
                                       const RVVVector& y, size_t vl) {
  RVVVector broadcast(g_ctx->tm, 16, std::vector<Term>(vl, x.term()));
  return _gw_macc_vv(vd, broadcast, y, 32, true, true, vl);
}
inline RVVVector __riscv_vwmacc_vx_i32mf2(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i64m1(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i64m2(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i64m4(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmacc_vx_i64m8(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i16mf4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i32m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i32m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i32m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i32m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i32mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i64m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i64m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i64m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vv_i64m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,true,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16m1(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16m2(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16m4(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16m8(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16mf2(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i16mf4(const RVVVector& vd, int8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i32m1(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i32m2(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i32m4(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i32m8(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i32mf2(const RVVVector& vd, int16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i64m1(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i64m2(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i64m4(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccsu_vx_i64m8(const RVVVector& vd, int32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u16mf4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,16,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u32m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u32m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u32m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u32m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u32mf2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,32,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u64m1(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u64m2(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u64m4(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vv_u64m8(const RVVVector& vd, const RVVVector& x, const RVVVector& y, size_t vl){ return _gw_macc_vv(vd,x,y,64,false,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16m1(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16m2(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16m4(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16m8(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16mf2(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u16mf4(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u32m1(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u32m2(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u32m4(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u32m8(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u32mf2(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u64m1(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u64m2(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u64m4(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccu_vx_u64m8(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,false,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16m1(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16m2(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16m4(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16m8(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16mf2(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i16mf4(const RVVVector& vd, uint8_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,16,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i32m1(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i32m2(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i32m4(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i32m8(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i32mf2(const RVVVector& vd, uint16_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,32,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i64m1(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i64m2(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i64m4(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmaccus_vx_i64m8(const RVVVector& vd, uint32_t x, const RVVVector& y, size_t vl){ return _gw_macc_vx(vd,(int64_t)x,y,64,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwmul_vv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwmul_vx_i16m1(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmul_vx_i16m2(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
// symbolic-scalar overload: qd8 reads `a0[i]` via salt_scalar (int8 has no NaN sentinel).
// Product built at 32 bits with vmlal-matching structure (sext-merge makes the MULT node
// hash-cons with NEON's), truncated to the true 16-bit result; the sext(extract)==M32
// equality is a tautology here (8-bit-sext operands → |prod| < 2^15) asserted as a bridge
// so SAT never has to reason about the multiplier's output range.
inline RVVVector __riscv_vwmul_vx_i16m2(const RVVVector& a, SymbolicScalar<int8_t> b, size_t vl){
  auto&tm=g_ctx->tm;
  Op sx24=tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND,{24}), sx16=tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND,{16});
  Op lo16=tm.mkOp(Kind::BITVECTOR_EXTRACT,{15,0});
  Term sb=tm.mkTerm(sx24,{b.term()});
  std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++){
    Term sa=tm.mkTerm(sx24,{a.getElement(i)});
    Term m32=tm.mkTerm(Kind::BITVECTOR_MULT,{sa,sb});
    Term p16=tm.mkTerm(lo16,{m32});
    g_ctx->solver->assertFormula(tm.mkTerm(Kind::EQUAL,{m32,tm.mkTerm(sx16,{p16})}));
    r.push_back(p16);}
  return RVVVector(tm,16,r);
}
inline RVVVector __riscv_vwmul_vx_i16m4(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmul_vx_i16m8(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmul_vx_i16mf2(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmul_vx_i16mf4(const RVVVector& a, int8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmul_vx_i32m1(const RVVVector& a, int16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmul_vx_i32m2(const RVVVector& a, int16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmul_vx_i32mf2(const RVVVector& a, int16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmul_vx_i64m1(const RVVVector& a, int32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmul_vx_i64m2(const RVVVector& a, int32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmul_vx_i64m4(const RVVVector& a, int32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmul_vx_i64m8(const RVVVector& a, int32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,true,false,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16m2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16m4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmulsu_vx_i64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwmulu_vv_u16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,16,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,32,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwmulu_vv_u64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_mul_vv(a,b,64,false,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16m2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16m4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,16,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,32,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwmulu_vx_u64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_mul_vx(a,(int64_t)b,64,false,vl); }
inline RVVVector __riscv_vwsub_vv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,true,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i16m1(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i16m8(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i16mf2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i16mf4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i32m1(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i32m2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i32m4(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i32m8(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i32mf2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i64m1(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i64m2(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i64m4(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_vx_i64m8(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_wv_i64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,true,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16m1(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16m2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16m4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16m8(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16mf2(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i16mf4(const RVVVector& a, int8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsub_wx_i32m1(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsub_wx_i32m2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsub_wx_i32m4(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsub_wx_i32m8(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsub_wx_i32mf2(const RVVVector& a, int16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsub_wx_i64m1(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsub_wx_i64m2(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsub_wx_i64m4(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsub_wx_i64m8(const RVVVector& a, int32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,16,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,32,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vv_u64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_vv(a,b,64,false,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_vx_u64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_vx(a,(int64_t)b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u16mf4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,16,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u32m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u32m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u32m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u32m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u32mf2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,32,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u64m1(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u64m2(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u64m4(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_wv_u64m8(const RVVVector& a, const RVVVector& b, size_t vl){ return _gw_bin_wv(a,b,64,false,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16m1(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16m2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16m4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16m8(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16mf2(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u16mf4(const RVVVector& a, uint8_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,16,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u32m1(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u32m2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u32m4(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u32m8(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u32mf2(const RVVVector& a, uint16_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,32,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u64m1(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u64m2(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u64m4(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vwsubu_wx_u64m8(const RVVVector& a, uint32_t b, size_t vl){ return _gw_bin_wx(a,(int64_t)b,64,true,vl); }
inline RVVVector __riscv_vzext_vf2_u16m1(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vzext_vf2_u16m4(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vzext_vf2_u16m8(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vzext_vf2_u16mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vzext_vf2_u16mf4(const RVVVector& a, size_t vl){ return _gw_unary(a,16,8,false,vl); }
inline RVVVector __riscv_vzext_vf2_u32m4(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vzext_vf2_u32m8(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vzext_vf2_u32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,16,false,vl); }
inline RVVVector __riscv_vzext_vf2_u64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vzext_vf2_u64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vzext_vf2_u64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vzext_vf2_u64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,32,false,vl); }
inline RVVVector __riscv_vzext_vf4_u32m2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,false,vl); }
inline RVVVector __riscv_vzext_vf4_u32m4(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,false,vl); }
inline RVVVector __riscv_vzext_vf4_u32m8(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,false,vl); }
inline RVVVector __riscv_vzext_vf4_u32mf2(const RVVVector& a, size_t vl){ return _gw_unary(a,32,8,false,vl); }
inline RVVVector __riscv_vzext_vf4_u64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,false,vl); }
inline RVVVector __riscv_vzext_vf4_u64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,false,vl); }
inline RVVVector __riscv_vzext_vf4_u64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,false,vl); }
inline RVVVector __riscv_vzext_vf4_u64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,16,false,vl); }
inline RVVVector __riscv_vzext_vf8_u64m1(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,false,vl); }
inline RVVVector __riscv_vzext_vf8_u64m2(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,false,vl); }
inline RVVVector __riscv_vzext_vf8_u64m4(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,false,vl); }
inline RVVVector __riscv_vzext_vf8_u64m8(const RVVVector& a, size_t vl){ return _gw_unary(a,64,8,false,vl); }
} // namespace salt_cvc5
