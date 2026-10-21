#!/usr/bin/env python3
"""Execute C lowering regressions on the host; optionally type-check real RVV.

The host uses small test-only vector structs and lane operations. These tests
check C control flow, sizeof, and assignment sequencing, not RVV execution or
the correctness of the intrinsic catalogue. Target structs are deliberately
larger than their NEON counterparts to expose accidental target sizeof usage.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from corpus import EXE, builtin_header, run


CASES = {
    "conditions": """
int main(void) {
  int x = 0;
  if (x) ++x;
  if (x != 0) return 1;
  x = 3;
  while (x) --x;
  if (x != 0) return 2;
  int y = 0;
  int* p = &y;
  if (1) *p = 7;
  if (y != 7) return 3;
  if XNN_LIKELY(1) ++y;
  if XNN_UNLIKELY(0) --y;
  do --y; while (y > 7);
  if (1) if (0) ++y; else --y;
  return y != 6;
}
""",
    "sizeof_type": """
int main(void) {
  if (!(sizeof(int8x16_t) < -1)) return 1;
  if (sizeof(int8x16_t) != 16) return 2;
  if (sizeof(uint32x2x2_t) != 16) return 3;
  return sizeof(sizeof(int8x16_t)) != sizeof(size_t);
}
""",
    "sizeof_expression": """
uint32x2_t identity(uint32x2_t v) { return v; }
int main(void) {
  int i = 0;
  uint32x2_t v;
  uint32x2_t* p = &v;
  uint32x2x2_t t;
  if (sizeof v != 8 || sizeof t != 16) return 1;
  if (sizeof t.val[0] != 8 || sizeof *p++ != 8) return 2;
  if (p != &v) return 3;
  if (sizeof vdup_n_u32(i++) != 8 || i != 0) return 4;
  if (sizeof (i++, v) != 8 || i != 0) return 5;
  if (sizeof (t.val[0] = v) != 8) return 6;
  if (sizeof (i ? v : v) != 8 || sizeof identity(v) != 8) return 7;
  if (!(sizeof v < -1)) return 8;
  if (sizeof p != sizeof(void*)) return 9;
  { size_t v = sizeof v; if (v != sizeof(size_t)) return 10; }
  return 0;
}
""",
    "tuple_assignment": """
uint32x2_t produce(int* count) { ++*count; return vdup_n_u32(*count); }
int main(void) {
  int calls = 0;
  uint32x2x2_t v;
  v.val[1] = vdup_n_u32(9);
  uint32x2_t x = (v.val[0] = produce(&calls));
  uint32_t out[2];
  vst1_u32(out, x);
  if (calls != 1 || out[0] != 1 || out[1] != 1) return 1;
  vst1_u32(out, v.val[0]);
  if (out[0] != 1 || out[1] != 1) return 2;
  vst1_u32(out, v.val[1]);
  return out[0] != 9 || out[1] != 9;
}
""",
    "tuple_nested": """
int main(void) {
  uint32x2x2_t v;
  v.val[0] = vdup_n_u32(1);
  v.val[1] = vdup_n_u32(2);
  uint32x2_t x = (v.val[0] = (v.val[1] = vdup_n_u32(7)));
  uint32_t out[2];
  vst1_u32(out, x);
  if (out[0] != 7 || out[1] != 7) return 1;
  vst1_u32(out, v.val[0]);
  if (out[0] != 7 || out[1] != 7) return 2;
  vst1_u32(out, v.val[1]);
  return out[0] != 7 || out[1] != 7;
}
""",
}

COMMON = """
#pragma once
#include <stddef.h>
#include <stdint.h>
#define XNN_LIKELY(x) (x)
#define XNN_UNLIKELY(x) (x)
"""
NEON = COMMON + """
typedef struct { int8_t lane[16]; } int8x16_t;
typedef struct { uint32_t lane[2]; } uint32x2_t;
typedef struct { uint32x2_t val[2]; } uint32x2x2_t;
static inline uint32x2_t vdup_n_u32(uint32_t a) {
  uint32x2_t r = {{a, a}}; return r;
}
static inline void vst1_u32(uint32_t* p, uint32x2_t v) {
  p[0] = v.lane[0]; p[1] = v.lane[1];
}
"""
RVV = COMMON + """
typedef struct { int8_t lane[32]; } vint8m1_t;
typedef struct { uint32_t lane[8]; } vuint32m1_t;
typedef struct { vuint32m1_t val[2]; } vuint32m1x2_t;
static inline vuint32m1_t __riscv_vmv_v_x_u32m1(uint32_t a, size_t vl) {
  vuint32m1_t r = {{0}};
  for (size_t i = 0; i < vl; ++i) r.lane[i] = a;
  return r;
}
static inline void __riscv_vse32_v_u32m1(uint32_t* p, vuint32m1_t v, size_t vl) {
  for (size_t i = 0; i < vl; ++i) p[i] = v.lane[i];
}
static inline vuint32m1x2_t __riscv_vcreate_v_u32m1x2(vuint32m1_t a, vuint32m1_t b) {
  vuint32m1x2_t r = {{a, b}}; return r;
}
static inline vuint32m1_t __riscv_vget_v_u32m1x2_u32m1(vuint32m1x2_t t, int i) {
  return t.val[i];
}
static inline vuint32m1x2_t __riscv_vset_v_u32m1_u32m1x2(vuint32m1x2_t t, int i, vuint32m1_t v) {
  t.val[i] = v; return t;
}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cc", default="cc", help="host C compiler")
    ap.add_argument("--clang", help="optional real RVV Clang syntax/type checks")
    ap.add_argument("--builtin-header", action="store_true")
    ap.add_argument("--include", action="append", default=[])
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="salty-regressions-") as temp:
        tmp = Path(temp)
        host = tmp / "host"
        host.mkdir()
        (host / "arm_neon.h").write_text(NEON)
        (host / "riscv_vector.h").write_text(RVV)
        targets = []
        for name, body in CASES.items():
            source = tmp / f"{name}.c"
            source.write_text('#include <arm_neon.h>\n' + body)
            target = tmp / f"{name}-rvv.c"
            run([EXE, "transpile", source, "-o", target])
            run([EXE, "check", target])
            targets.append(target)
            for optimization in ["-O0", "-O2"]:
                for path in [source, target]:
                    binary = tmp / "test"
                    run([args.cc, "-std=c11", optimization, "-I", host, path, "-o", binary])
                    result = subprocess.run([binary], timeout=5)
                    assert result.returncode == 0, (name, path.name, optimization, result.returncode)
        print(f"PASS: {len(CASES)} host lowering regressions, source and target at O0/O2 (test-only vector structs)")
        if args.clang:
            real = tmp / "real"
            real.mkdir()
            if args.builtin_header:
                builtin_header(real, "\n".join(p.read_text() for p in targets))
                header = real / "riscv_vector.h"
                header.write_text("#pragma once\n" + header.read_text())
            for vlen in [128, 256, 512]:
                for target in targets:
                    command = [args.clang, "--target=riscv64", f"-march=rv64gcv_zvl{vlen}b",
                               "-ffreestanding", "-fsyntax-only", "-Werror=implicit-function-declaration",
                               "-DXNN_LIKELY(x)=(x)", "-DXNN_UNLIKELY(x)=(x)"]
                    if args.builtin_header:
                        command += ["-I", real]
                    for inc in args.include:
                        command += ["-isystem", inc]
                    run(command + [target])
            print(f"PASS: {len(targets) * 3} real RVV regression syntax/type checks")


if __name__ == "__main__":
    main()
