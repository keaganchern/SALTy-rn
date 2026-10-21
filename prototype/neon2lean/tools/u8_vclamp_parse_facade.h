typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;

typedef struct { uint8_t lanes[8]; } uint8x8_t;
typedef struct { uint8_t lanes[16]; } uint8x16_t;
typedef struct { uint16_t lanes[4]; } uint16x4_t;
typedef struct { uint32_t lanes[2]; } uint32x2_t;

struct xnn_u8_minmax_params {
  struct {
    uint32_t min;
    uint32_t max;
  } scalar;
};

#define XNN_OOB_READS
#define XNN_UNLIKELY(x) (x)
#define NULL ((void*) 0)
#define assert(x) ((void) 0)

uint8x16_t vdupq_n_u8(uint8_t x);
uint8x16_t vld1q_u8(const uint8_t* p);
uint8x8_t vld1_u8(const uint8_t* p);
uint8x16_t vmaxq_u8(uint8x16_t a, uint8x16_t b);
uint8x16_t vminq_u8(uint8x16_t a, uint8x16_t b);
uint8x8_t vmax_u8(uint8x8_t a, uint8x8_t b);
uint8x8_t vmin_u8(uint8x8_t a, uint8x8_t b);
uint8x8_t vget_low_u8(uint8x16_t x);
uint32x2_t vreinterpret_u32_u8(uint8x8_t x);
uint16x4_t vreinterpret_u16_u8(uint8x8_t x);
uint8x8_t vext_u8(uint8x8_t a, uint8x8_t b, int n);
void vst1q_u8(uint8_t* p, uint8x16_t x);
void vst1_u8(uint8_t* p, uint8x8_t x);
void vst1_lane_u32(void* p, uint32x2_t x, int lane);
void vst1_lane_u16(void* p, uint16x4_t x, int lane);
void vst1_lane_u8(uint8_t* p, uint8x8_t x, int lane);
