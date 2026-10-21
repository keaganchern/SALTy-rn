/* Buffer protocol v1: magic, 32 u32 config words, buffer count, then
 * (u32 byte count, u32 writable, initial bytes) per buffer, all little endian.
 * Output contains every writable buffer, in order, including stride gaps.
 * Pointer tables are reconstructed locally from serialized byte offsets.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "kernel.c"

typedef struct { uint32_t size, writable; unsigned char *base, *data, *before; } Buffer;
static size_t current_case;
static void fail(const char* message) {
  fprintf(stderr, "case %zu: %s\n", current_case, message); exit(2);
}
static void read_exact(void* p, size_t n) {
  if (fread(p, 1, n, stdin) != n) fail("truncated input");
}
static float float_word(uint32_t word) { float f; memcpy(&f, &word, 4); return f; }
/* UINT32_MAX denotes the zero/sentinel buffer. Other offsets address data. */
static const void** pointers(Buffer* data, Buffer* offsets, Buffer* zero) {
  size_t count = offsets->size / 4;
  const void** p = malloc(count * sizeof(*p));
  if (!p) fail("allocation failed");
  for (size_t i = 0; i < count; ++i) {
    uint32_t offset; memcpy(&offset, offsets->data + 4 * i, 4);
    if (offset != UINT32_MAX && offset >= data->size) fail("invalid pointer offset");
    p[i] = offset == UINT32_MAX ? zero->data : data->data + offset;
  }
  return p;
}
#define B(i) ((void*) b[i].data)
#define F(i) float_word(c[i])
#define S(i) ((int32_t)c[i])
#include "adapter.h"

int main(int argc, char** argv) {
#ifdef __riscv
  size_t vlen_bytes;
  __asm__ volatile ("csrr %0, vlenb" : "=r"(vlen_bytes));
  if (argc != 2 || strtoul(argv[1], NULL, 10) != vlen_bytes * 8)
    fail("runtime VLEN disagrees with requested VLEN");
#else
  (void)argc; (void)argv;
#endif
  for (current_case = 0; ; ++current_case) {
    uint32_t magic, c[32], count;
    size_t got = fread(&magic, 1, 4, stdin);
    if (!got && feof(stdin)) break;
    if (got != 4 || magic != 0x53425431) fail("invalid buffer protocol");
    read_exact(c, sizeof(c)); read_exact(&count, 4);
    if (!count || count > 8) fail("invalid buffer count");
    Buffer b[8] = {0};
    for (size_t j = 0; j < count; ++j) {
      read_exact(&b[j].size, 4); read_exact(&b[j].writable, 4);
      if (!b[j].size || b[j].size > 16777216 || b[j].writable > 1) fail("invalid buffer descriptor");
      b[j].base = malloc(b[j].size + 128);
      b[j].before = malloc(b[j].size);
      if (!b[j].base || !b[j].before) fail("allocation failed");
      memset(b[j].base, 0xA5, b[j].size + 128);
      b[j].data = b[j].base + 64;
      read_exact(b[j].data, b[j].size);
      memcpy(b[j].before, b[j].data, b[j].size);
    }
    invoke(c, b);
    for (size_t j = 0; j < count; ++j) {
      if (!b[j].writable && memcmp(b[j].data, b[j].before, b[j].size)) fail("input buffer modified");
      for (size_t i = 0; i < 64; ++i)
        if (b[j].base[i] != 0xA5 || b[j].data[b[j].size + i] != 0xA5) fail("buffer guard modified");
      if (b[j].writable && fwrite(b[j].data, 1, b[j].size, stdout) != b[j].size) fail("output write failed");
      free(b[j].before); free(b[j].base);
    }
    if (fflush(stdout)) fail("output flush failed");
  }
  return ferror(stdin) ? 2 : 0;
}
