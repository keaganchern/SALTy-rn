#ifndef SALT_LEAN_INTEGER_TYPES_FACADE_H
#define SALT_LEAN_INTEGER_TYPES_FACADE_H

/* Parse-only scalar, vector, macro, and policy declarations. */

typedef __SIZE_TYPE__ size_t;
typedef __INT8_TYPE__ int8_t;
typedef __INT16_TYPE__ int16_t;
typedef __INT32_TYPE__ int32_t;
typedef __UINT8_TYPE__ uint8_t;
typedef __UINT16_TYPE__ uint16_t;
typedef __UINT32_TYPE__ uint32_t;

#define NULL ((void*) 0)
#define assert(condition) ((void) 0)
#define XNN_OOB_READS
#define XNN_LIKELY(condition) (condition)
#define XNN_UNLIKELY(condition) (condition)

#define __RISCV_VXRM_RNU 0
#define __RISCV_VXRM_RDN 2

typedef struct { int8_t lanes[8]; } int8x8_t;
typedef struct { int8_t lanes[16]; } int8x16_t;
typedef struct { int16_t lanes[4]; } int16x4_t;
typedef struct { int16_t lanes[8]; } int16x8_t;
typedef struct { int32_t lanes[4]; } int32x4_t;
typedef struct { uint8_t lanes[8]; } uint8x8_t;
typedef struct { uint16_t lanes[4]; } uint16x4_t;
typedef struct { uint16_t lanes[8]; } uint16x8_t;
typedef struct { uint32_t lanes[2]; } uint32x2_t;

typedef struct { int8_t opaque; } vint8m2_t;
typedef struct { int8_t opaque; } vint8m8_t;
typedef struct { int16_t opaque; } vint16m4_t;
typedef struct { int32_t opaque; } vint32m8_t;
typedef struct { uint8_t opaque; } vuint8m2_t;
typedef struct { uint16_t opaque; } vuint16m4_t;
typedef struct { uint8_t opaque; } vbool4_t;

#endif
