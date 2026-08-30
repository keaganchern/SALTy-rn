#!/bin/sh
set -eu

probe_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
probe_source="$probe_script_dir/rvv-vssra-vx-i32m8-shift32-probe.c"
probe_start="$probe_script_dir/rvv-vssra-vx-i32m8-shift32-start.S"
probe_build_dir=$(mktemp -d "${TMPDIR:-/tmp}/rvv-vssra-shift32.XXXXXX")
trap 'rm -rf -- "$probe_build_dir"' EXIT HUP INT TERM

find_probe_tool() {
  configured=$1
  shift
  if [ -n "$configured" ]; then
    if command -v "$configured" >/dev/null 2>&1; then
      command -v "$configured"
      return 0
    fi
    echo "configured tool is not executable: $configured" >&2
    return 1
  fi
  for candidate in "$@"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  echo "missing required tool; tried: $*" >&2
  return 1
}

probe_clang=$(find_probe_tool "${RVV_PROBE_CLANG:-}" \
  /opt/homebrew/opt/llvm/bin/clang clang-20 clang)
probe_ld=$(find_probe_tool "${RVV_PROBE_LD:-}" riscv64-elf-ld)
probe_objdump=$(find_probe_tool "${RVV_PROBE_OBJDUMP:-}" riscv64-elf-objdump)
probe_spike=$(find_probe_tool "${RVV_PROBE_SPIKE:-}" spike)

"$probe_clang" --target=riscv64-unknown-elf \
  -march=rv64gcv_zvl128b -mabi=lp64d -O2 -ffreestanding \
  -c -o "$probe_build_dir/probe.o" "$probe_source"
"$probe_clang" --target=riscv64-unknown-elf \
  -march=rv64gcv_zvl128b -mabi=lp64d \
  -c -o "$probe_build_dir/start.o" "$probe_start"
"$probe_ld" -Ttext=0x80001000 -e _start --no-relax \
  -o "$probe_build_dir/probe.elf" \
  "$probe_build_dir/start.o" "$probe_build_dir/probe.o"

"$probe_objdump" -d "$probe_build_dir/probe.elf" > "$probe_build_dir/disassembly.txt"
"$probe_spike" --isa=rv64gcv_zvl128b --pc=0x80001000 \
  --instructions=30 -l --log-commits "$probe_build_dir/probe.elf" \
  > "$probe_build_dir/spike.txt" 2>&1

if ! grep -Eq 'li[[:space:]]+a1,32' "$probe_build_dir/disassembly.txt"; then
  echo "FAIL: compiled caller does not pass shift=32 in a1" >&2
  exit 1
fi
if ! grep -Eq 'vssra\.vx[[:space:]]+v8,v8,a1' "$probe_build_dir/disassembly.txt"; then
  echo "FAIL: C intrinsic did not lower to vssra.vx using the dynamic shift" >&2
  exit 1
fi
if ! awk '
  /vssra\.vx v8, v8, a1/ {
    getline
    if ($0 ~ /e32 m8 l1 v8 .*0000000000000001/) found = 1
  }
  END { exit(found ? 0 : 1) }
' "$probe_build_dir/spike.txt"; then
  echo "FAIL: Spike did not commit lane 0 of v8 as 1 after vssra.vx" >&2
  exit 1
fi
if ! grep -Eq 'x10 +0x0000000000000001 mem ' "$probe_build_dir/spike.txt"; then
  echo "FAIL: stored and returned scalar result is not 1" >&2
  exit 1
fi

grep -E 'li[[:space:]]+a1,32|vssra\.vx[[:space:]]+v8,v8,a1' \
  "$probe_build_dir/disassembly.txt"
grep -E 'vssra\.vx v8, v8, a1|e32 m8 l1 v8 .*0000000000000001|x10 +0x0000000000000001 mem ' \
  "$probe_build_dir/spike.txt" | tail -3
echo "PASS: RVV C intrinsic input=1 shift=32 RNU returned 1"
