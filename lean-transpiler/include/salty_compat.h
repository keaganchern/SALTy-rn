#ifndef SALTY_TRANSPILER_COMPAT_H
#define SALTY_TRANSPILER_COMPAT_H

/* Minimal context for the standalone snippets in kernels/source/.
 * The parameter records themselves are emitted by --kernel. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

#define XNN_OOB_READS
#define XNN_LIKELY(x) (__builtin_expect(!!(x), 1))
#define XNN_UNLIKELY(x) (__builtin_expect(!!(x), 0))
#define XNN_UNPREDICTABLE(x) (x)
#define XNN_ALIGN(n) __attribute__((aligned(n)))

static inline size_t min(size_t a, size_t b) { return a < b ? a : b; }
static inline size_t doz(size_t a, size_t b) { return a > b ? a - b : 0; }
static inline size_t round_down_po2(size_t n, size_t q) { return n & ~(q - 1); }
static inline size_t round_up_po2(size_t n, size_t q) { return (n + q - 1) & ~(q - 1); }
static inline void xnn_prefetch_to_l1(const void *p) { __builtin_prefetch(p); }

/* This shared record is not repeated in the kernels' parameter comments. */
struct xnn_qd8_quantization_params {
  int32_t zero_point;
  float inv_scale;
};

#endif
