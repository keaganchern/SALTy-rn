#pragma once
// RVV initialize/move family — generated (ns salt_cvc5).
// vmv_v_v (copy), vmv_v_x (broadcast), vmv_s_x (lane0=scalar,tail 0),
// vmv_x_s (lane0 -> scalar, returns 0 per tree convention), vundefined (zeros).
#include "../intrinsics.hpp"
namespace salt_cvc5 {
inline RVVVector _gini_copy(const RVVVector& s,size_t sew,size_t vl){
  auto& tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  for(size_t i=0;i<vl;i++) r.push_back(s.getElement(i));
  return RVVVector(tm,sew,r);
}
inline RVVVector _gini_bcast(int64_t v,size_t sew,size_t vl){
  auto& tm=g_ctx->tm; Term b=mk_bv_val(tm,sew,v);
  return RVVVector(tm,sew,std::vector<Term>(vl,b));
}
inline RVVVector _gini_s_x(int64_t v,size_t sew,size_t vl){
  auto& tm=g_ctx->tm; std::vector<Term> r; r.reserve(vl);
  r.push_back(mk_bv_val(tm,sew,v));
  for(size_t i=1;i<vl;i++) r.push_back(mk_bv_val(tm,sew,0));
  return RVVVector(tm,sew,r);
}
inline RVVVector _gini_undef(size_t sew){
  auto& tm=g_ctx->tm; size_t n=g_ctx->vlen/sew*8; if(n<1) n=1;
  return RVVVector(tm,sew,std::vector<Term>(n,mk_bv_val(tm,sew,0)));
}
inline RVVVector __riscv_vmv_s_x_i16m1(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i16m2(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i16m4(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i16m8(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i16mf2(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i16mf4(int16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_i32m1(int32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_i32m2(int32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_i32m4(int32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_i32m8(int32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_i32mf2(int32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_i64m1(int64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_i64m2(int64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_i64m4(int64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_i64m8(int64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_i8m1(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8m2(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8m4(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8m8(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8mf2(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8mf4(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_i8mf8(int8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u16m1(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u16m2(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u16m4(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u16m8(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u16mf2(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u16mf4(uint16_t src, size_t vl){ return _gini_s_x((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_s_x_u32m1(uint32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_u32m2(uint32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_u32m4(uint32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_u32m8(uint32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_u32mf2(uint32_t src, size_t vl){ return _gini_s_x((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_s_x_u64m1(uint64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_u64m2(uint64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_u64m4(uint64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_u64m8(uint64_t src, size_t vl){ return _gini_s_x((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_s_x_u8m1(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8m2(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8m4(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8m8(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8mf2(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8mf4(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_s_x_u8mf8(uint8_t src, size_t vl){ return _gini_s_x((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_v_f16m1(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_f16m2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_f16mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_f16mf4(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_f32m1(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_f32m2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_f32m8(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_f32mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_f64m1(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_f64m2(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_f64m4(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_f64m8(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_i16m1(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i16m2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i16m4(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i16m8(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i16mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i16mf4(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_i32m1(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_i32m2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_i32m4(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_i32m8(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_i32mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_i64m1(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_i64m2(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_i64m4(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_i64m8(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_i8m1(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8m2(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8m4(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8m8(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8mf4(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_i8mf8(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u16m1(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u16m2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u16m4(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u16m8(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u16mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u16mf4(const RVVVector& src, size_t vl){ return _gini_copy(src,16,vl); }
inline RVVVector __riscv_vmv_v_v_u32m1(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_u32m2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_u32m4(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_u32m8(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_u32mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,32,vl); }
inline RVVVector __riscv_vmv_v_v_u64m1(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_u64m2(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_u64m4(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_u64m8(const RVVVector& src, size_t vl){ return _gini_copy(src,64,vl); }
inline RVVVector __riscv_vmv_v_v_u8m1(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8m2(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8m4(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8m8(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8mf2(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8mf4(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_v_u8mf8(const RVVVector& src, size_t vl){ return _gini_copy(src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i16m1(int16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_i16m2(int16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_i16m8(int16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_i16mf2(int16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_i16mf4(int16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_i32m1(int32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_i32m2(int32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_i32m4(int32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_i32mf2(int32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_i64m1(int64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_i64m2(int64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_i64m4(int64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_i64m8(int64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_i8m1(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8m2(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8m4(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8m8(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8mf2(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8mf4(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_i8mf8(int8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u16m2(uint16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_u16mf2(uint16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_u16mf4(uint16_t src, size_t vl){ return _gini_bcast((int64_t)src,16,vl); }
inline RVVVector __riscv_vmv_v_x_u32m2(uint32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_u32m4(uint32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_u32mf2(uint32_t src, size_t vl){ return _gini_bcast((int64_t)src,32,vl); }
inline RVVVector __riscv_vmv_v_x_u64m1(uint64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_u64m2(uint64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_u64m4(uint64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_u64m8(uint64_t src, size_t vl){ return _gini_bcast((int64_t)src,64,vl); }
inline RVVVector __riscv_vmv_v_x_u8m1(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8m2(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8m4(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8m8(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8mf2(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8mf4(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline RVVVector __riscv_vmv_v_x_u8mf8(uint8_t src, size_t vl){ return _gini_bcast((int64_t)src,8,vl); }
inline int16_t __riscv_vmv_x_s_i16m2_i16(const RVVVector& src){ (void)src; return 0; }
inline int16_t __riscv_vmv_x_s_i16m4_i16(const RVVVector& src){ (void)src; return 0; }
inline int16_t __riscv_vmv_x_s_i16m8_i16(const RVVVector& src){ (void)src; return 0; }
inline int16_t __riscv_vmv_x_s_i16mf2_i16(const RVVVector& src){ (void)src; return 0; }
inline int16_t __riscv_vmv_x_s_i16mf4_i16(const RVVVector& src){ (void)src; return 0; }
inline int32_t __riscv_vmv_x_s_i32m1_i32(const RVVVector& src){ g_ctx->set_scalar_result(src.getElement(0)); return 0; }  // rsum: capture reduction sum
inline int32_t __riscv_vmv_x_s_i32m2_i32(const RVVVector& src){ (void)src; return 0; }
inline int32_t __riscv_vmv_x_s_i32m4_i32(const RVVVector& src){ (void)src; return 0; }
inline int32_t __riscv_vmv_x_s_i32m8_i32(const RVVVector& src){ (void)src; return 0; }
inline int32_t __riscv_vmv_x_s_i32mf2_i32(const RVVVector& src){ (void)src; return 0; }
inline int64_t __riscv_vmv_x_s_i64m1_i64(const RVVVector& src){ (void)src; return 0; }
inline int64_t __riscv_vmv_x_s_i64m2_i64(const RVVVector& src){ (void)src; return 0; }
inline int64_t __riscv_vmv_x_s_i64m4_i64(const RVVVector& src){ (void)src; return 0; }
inline int64_t __riscv_vmv_x_s_i64m8_i64(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8m1_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8m2_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8m4_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8m8_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8mf2_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8mf4_i8(const RVVVector& src){ (void)src; return 0; }
inline int8_t __riscv_vmv_x_s_i8mf8_i8(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16m1_u16(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16m2_u16(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16m4_u16(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16m8_u16(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16mf2_u16(const RVVVector& src){ (void)src; return 0; }
inline uint16_t __riscv_vmv_x_s_u16mf4_u16(const RVVVector& src){ (void)src; return 0; }
inline uint32_t __riscv_vmv_x_s_u32m1_u32(const RVVVector& src){ g_ctx->set_scalar_result(src.getElement(0)); return 0; }  // rsum: capture reduction sum
inline uint32_t __riscv_vmv_x_s_u32m2_u32(const RVVVector& src){ (void)src; return 0; }
inline uint32_t __riscv_vmv_x_s_u32m4_u32(const RVVVector& src){ (void)src; return 0; }
inline uint32_t __riscv_vmv_x_s_u32m8_u32(const RVVVector& src){ (void)src; return 0; }
inline uint32_t __riscv_vmv_x_s_u32mf2_u32(const RVVVector& src){ (void)src; return 0; }
inline uint64_t __riscv_vmv_x_s_u64m1_u64(const RVVVector& src){ (void)src; return 0; }
inline uint64_t __riscv_vmv_x_s_u64m2_u64(const RVVVector& src){ (void)src; return 0; }
inline uint64_t __riscv_vmv_x_s_u64m4_u64(const RVVVector& src){ (void)src; return 0; }
inline uint64_t __riscv_vmv_x_s_u64m8_u64(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8m1_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8m2_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8m4_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8m8_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8mf2_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8mf4_u8(const RVVVector& src){ (void)src; return 0; }
inline uint8_t __riscv_vmv_x_s_u8mf8_u8(const RVVVector& src){ (void)src; return 0; }
inline RVVVector __riscv_vundefined_f16m1(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m1x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16m8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf2x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f16mf4x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_f32m1(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m1x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m1x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m1x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m1x5(){ return _gini_undef(32); }
// Tuple types aliased to VectorTuple (intrinsics.hpp) return a tuple of zero vectors.
inline VectorTuple<RVVVector,6> __riscv_vundefined_f32m1x6(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,6>{{u,u,u,u,u,u}}; }
inline RVVVector __riscv_vundefined_f32m1x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m1x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m2x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m2x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m2x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m4x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32m8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x5(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x6(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f32mf2x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_f64m1(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x5(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x6(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x7(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m1x8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m2x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m2x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m2x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m4x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_f64m8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i16m1(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m1x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16m8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf2x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i16mf4x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_i32m1(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x5(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x6(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m1x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m2x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m2x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m2x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m4x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32m8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x2(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x5(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x6(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i32mf2x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_i64m1(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x5(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x6(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x7(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m1x8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m2x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m2x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m2x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m4x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i64m8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_i8m1(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m1x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m2x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m2x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m2x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m4x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8m8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf2x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf4x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_i8mf8x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u16m1(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m1x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16m8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf2x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x2(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x3(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x4(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x5(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x6(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x7(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u16mf4x8(){ return _gini_undef(16); }
inline RVVVector __riscv_vundefined_u32m1(){ return _gini_undef(32); }
inline VectorTuple<RVVVector,2> __riscv_vundefined_u32m1x2(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,2>{{u,u}}; }
inline RVVVector __riscv_vundefined_u32m1x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m1x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m1x5(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m1x6(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m1x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m1x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32m2(){ return _gini_undef(32); }
inline VectorTuple<RVVVector,2> __riscv_vundefined_u32m2x2(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,2>{{u,u}}; }
inline VectorTuple<RVVVector,3> __riscv_vundefined_u32m2x3(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,3>{{u,u,u}}; }
inline VectorTuple<RVVVector,4> __riscv_vundefined_u32m2x4(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,4>{{u,u,u,u}}; }
inline RVVVector __riscv_vundefined_u32m4(){ return _gini_undef(32); }
inline VectorTuple<RVVVector,2> __riscv_vundefined_u32m4x2(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,2>{{u,u}}; }
inline RVVVector __riscv_vundefined_u32m8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2(){ return _gini_undef(32); }
inline VectorTuple<RVVVector,2> __riscv_vundefined_u32mf2x2(){ RVVVector u=_gini_undef(32); return VectorTuple<RVVVector,2>{{u,u}}; }
inline RVVVector __riscv_vundefined_u32mf2x3(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2x4(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2x5(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2x6(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2x7(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u32mf2x8(){ return _gini_undef(32); }
inline RVVVector __riscv_vundefined_u64m1(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x5(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x6(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x7(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m1x8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m2x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m2x3(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m2x4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m4(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m4x2(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u64m8(){ return _gini_undef(64); }
inline RVVVector __riscv_vundefined_u8m1(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m1x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m2x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m2x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m2x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m4x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8m8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf2x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf4x8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x2(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x3(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x4(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x5(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x6(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x7(){ return _gini_undef(8); }
inline RVVVector __riscv_vundefined_u8mf8x8(){ return _gini_undef(8); }
} // namespace salt_cvc5
