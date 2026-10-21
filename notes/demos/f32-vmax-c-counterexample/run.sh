#!/bin/sh
set -eu

demo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d "${TMPDIR:-/tmp}/f32-vmax-c-counterexample.XXXXXX")
trap 'rm -rf -- "$build_dir"' EXIT HUP INT TERM

find_tool() {
  for candidate in "$@"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  echo "missing required tool; tried: $*" >&2
  return 1
}

host_clang=$(find_tool clang)
rvv_clang=$(find_tool /opt/homebrew/opt/llvm/bin/clang clang-20)
rvv_ld=$(find_tool riscv64-elf-ld)
rvv_objdump=$(find_tool riscv64-elf-objdump)
spike=$(find_tool spike)

"$host_clang" -std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-parameter \
  "$demo_dir/neon-original.c" -o "$build_dir/neon-original"
neon_output=$("$build_dir/neon-original")

"$rvv_clang" --target=riscv64-unknown-elf \
  -march=rv64gcv_zvl128b -mabi=lp64d -mcmodel=medany \
  -std=c11 -O2 -ffreestanding \
  -c "$demo_dir/rvv-original.c" -o "$build_dir/rvv-original.o"
"$rvv_clang" --target=riscv64-unknown-elf \
  -march=rv64gcv_zvl128b -mabi=lp64d -mcmodel=medany \
  -c "$demo_dir/rvv-start.S" -o "$build_dir/rvv-start.o"
"$rvv_ld" -Ttext=0x80001000 -e _start --no-relax \
  "$build_dir/rvv-start.o" "$build_dir/rvv-original.o" \
  -o "$build_dir/rvv-original.elf"

"$rvv_objdump" -d "$build_dir/rvv-original.elf" > "$build_dir/rvv-disassembly.txt"
"$spike" --isa=rv64gcv_zvl128b --pc=0x80001000 \
  --instructions=80 -l --log-commits "$build_dir/rvv-original.elf" \
  > "$build_dir/rvv-spike.txt" 2>&1

if ! grep -Eq 'vfmax\.vv' "$build_dir/rvv-disassembly.txt"; then
  echo "FAIL: the target C intrinsic did not lower to vfmax.vv" >&2
  exit 1
fi
if ! grep -Eq 'addi[[:space:]]+a0,a0,1' "$build_dir/rvv-disassembly.txt"; then
  echo "FAIL: missing RVV result observation instruction" >&2
  exit 1
fi
if ! awk '
  /x10 / { last = $0 }
  END { exit(last ~ /x10 +0x0000000000000001/ ? 0 : 1) }
' "$build_dir/rvv-spike.txt"; then
  echo "FAIL: RVV original C output was not 0x00000000" >&2
  grep -E 'addi a0|x10 ' "$build_dir/rvv-spike.txt" | tail -10 >&2
  exit 1
fi

echo "$neon_output"
echo "RVV original C output:  0x00000000"
echo "PASS: original C kernels disagree for (+0.0, qNaN)"
