#ifndef SALT_TEST_WIDE_COPY_FACADE_H
#define SALT_TEST_WIDE_COPY_FACADE_H

typedef __SIZE_TYPE__ size_t;
typedef __INT16_TYPE__ int16_t;
typedef __INT32_TYPE__ int32_t;
typedef __UINT16_TYPE__ uint16_t;
typedef __UINT32_TYPE__ uint32_t;

#define NULL ((void*) 0)
#define assert(condition) ((void) 0)

typedef struct { uint16_t lanes[4]; } salt_u16x4_t;
typedef struct { uint16_t lanes[2]; } salt_u16x2_t;
typedef struct { uint16_t opaque; } salt_vu16m1_t;

typedef struct { uint32_t lanes[4]; } salt_u32x4_t;
typedef struct { uint32_t lanes[2]; } salt_u32x2_t;
typedef struct { uint32_t opaque; } salt_vu32m1_t;

typedef struct { float lanes[4]; } salt_f32x4_t;
typedef struct { float lanes[2]; } salt_f32x2_t;
typedef struct { float opaque; } salt_vf32m1_t;

typedef struct { int32_t lanes[4]; } salt_i32x4_t;
typedef struct { int16_t lanes[4]; } salt_i16x4_t;
typedef struct { int32_t opaque; } salt_vi32m1_t;
typedef struct { int16_t opaque; } salt_vi16m1_t;

salt_u16x4_t salt_neon_load4_u16(const uint16_t*);
salt_u16x2_t salt_neon_low2_u16(salt_u16x4_t);
salt_u16x2_t salt_neon_high2_u16(salt_u16x4_t);
void salt_neon_store4_u16(uint16_t*, salt_u16x4_t);
void salt_neon_store2_u16(uint16_t*, salt_u16x2_t);
void salt_neon_store1_u16(uint16_t*, salt_u16x2_t, int);
size_t salt_rvv_setvl_u16(size_t);
salt_vu16m1_t salt_rvv_load_u16(const uint16_t*, size_t);
void salt_rvv_store_u16(uint16_t*, salt_vu16m1_t, size_t);

salt_u32x4_t salt_neon_load4_u32(const uint32_t*);
salt_u32x2_t salt_neon_low2_u32(salt_u32x4_t);
salt_u32x2_t salt_neon_high2_u32(salt_u32x4_t);
void salt_neon_store4_u32(uint32_t*, salt_u32x4_t);
void salt_neon_store2_u32(uint32_t*, salt_u32x2_t);
void salt_neon_store1_u32(uint32_t*, salt_u32x2_t, int);
size_t salt_rvv_setvl_u32(size_t);
salt_vu32m1_t salt_rvv_load_u32(const uint32_t*, size_t);
void salt_rvv_store_u32(uint32_t*, salt_vu32m1_t, size_t);

salt_f32x4_t salt_neon_load4_f32(const float*);
salt_f32x2_t salt_neon_low2_f32(salt_f32x4_t);
salt_f32x2_t salt_neon_high2_f32(salt_f32x4_t);
void salt_neon_store4_f32(float*, salt_f32x4_t);
void salt_neon_store2_f32(float*, salt_f32x2_t);
void salt_neon_store1_f32(float*, salt_f32x2_t, int);
size_t salt_rvv_setvl_f32(size_t);
salt_vf32m1_t salt_rvv_load_f32(const float*, size_t);
void salt_rvv_store_f32(float*, salt_vf32m1_t, size_t);

salt_i32x4_t salt_neon_load4_i32(const int32_t*);
salt_i16x4_t salt_neon_narrow_i16(salt_i32x4_t);
void salt_neon_store4_i16(int16_t*, salt_i16x4_t);
size_t salt_rvv_setvl_i32_i16(size_t);
salt_vi32m1_t salt_rvv_load_i32(const int32_t*, size_t);
salt_vi16m1_t salt_rvv_narrow_i16(salt_vi32m1_t, size_t, unsigned int, size_t);
void salt_rvv_store_i16(int16_t*, salt_vi16m1_t, size_t);

#endif
