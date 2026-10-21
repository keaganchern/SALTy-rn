/* Shared by the original AArch64 source and freshly transpiled RVV target.
 * adapter.h supplies types, parameter initialization, and the kernel call.
 * stdin: repeated LE uint32 n, 10 LE int32 parameters, two padded input arrays.
 * stdout: concatenated logical output bytes, with no struct padding or pointers.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "kernel.c"
#include "adapter.h"

#define PAD_ELEMENTS 32
#define GUARD_BYTES 64

static void fail(size_t case_index, const char* message) {
  fprintf(stderr, "case %zu: %s\n", case_index, message);
  exit(2);
}

static void read_exact(void* p, size_t n, size_t case_index) {
  if (fread(p, 1, n, stdin) != n) fail(case_index, "truncated input");
}

int main(int argc, char** argv) {
#ifdef __riscv
  size_t vlen_bytes;
  __asm__ volatile ("csrr %0, vlenb" : "=r"(vlen_bytes));
  if (argc != 2 || strtoul(argv[1], NULL, 10) != vlen_bytes * 8)
    fail(0, "runtime VLEN disagrees with requested VLEN");
#else
  (void)argc; (void)argv;
#endif
  for (size_t case_index = 0; ; ++case_index) {
    uint32_t n;
    size_t got = fread(&n, 1, sizeof(n), stdin);
    if (got == 0 && feof(stdin)) break;
    if (got != sizeof(n) || n == 0 || n > 1048576)
      fail(case_index, "invalid input length");
    int32_t config[10];
    read_exact(config, sizeof(config), case_index);
    size_t input_bytes = ((size_t)n + PAD_ELEMENTS) * sizeof(INPUT_T);
    size_t output_bytes = OUTPUT_COUNT(n) * sizeof(OUTPUT_T);
    INPUT_T* a = malloc(input_bytes);
    INPUT_T* b = malloc(input_bytes);
    unsigned char* before = malloc(2 * input_bytes);
    unsigned char* storage = malloc(output_bytes + 2 * GUARD_BYTES);
    if (!a || !b || !before || !storage) fail(case_index, "allocation failed");
    read_exact(a, input_bytes, case_index);
    read_exact(b, input_bytes, case_index);
    memcpy(before, a, input_bytes);
    memcpy(before + input_bytes, b, input_bytes);
    memset(storage, 0xA5, output_bytes + 2 * GUARD_BYTES);
    OUTPUT_T* out = (OUTPUT_T*)(storage + GUARD_BYTES);
    PARAMS_T params = {0};
    INIT_PARAMS(params, config);
    INVOKE(n, a, b, out, &params);
    if (memcmp(before, a, input_bytes) || memcmp(before + input_bytes, b, input_bytes))
      fail(case_index, "input buffer modified");
    for (size_t i = 0; i < GUARD_BYTES; ++i) {
      if (storage[i] != 0xA5 || storage[GUARD_BYTES + output_bytes + i] != 0xA5)
        fail(case_index, "output guard modified");
    }
    if (fwrite(out, 1, output_bytes, stdout) != output_bytes || fflush(stdout))
      fail(case_index, "output write failed");
    free(a); free(b); free(before); free(storage);
  }
  if (fflush(stdout) || ferror(stdin)) return 2;
  return 0;
}
