#!/usr/bin/env python3
"""Reassemble the kernels and compare every instruction with the checked inventory."""
import argparse
import json
import os
import re
import subprocess
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def check_elf(elf, instructions):
    """Bind the disassembled inventory to bytes in executable ELF load segments."""
    data = elf.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise SystemExit('Expected a little-endian ELF64 file')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    segments = [struct.unpack_from('<IIQQQQQQ', data, header[5] + index * header[9])
                for index in range(header[10])]
    for address, hexbytes in instructions:
        code = bytes.fromhex(hexbytes)
        matches = [segment for segment in segments if segment[0] == 1 and segment[1] & 1
                   and segment[3] <= address and address + len(code) <= segment[3] + segment[5]]
        if len(matches) != 1:
            raise SystemExit(f'Instruction at {address:#x} lacks a unique executable load segment')
        segment = matches[0]
        offset = segment[2] + address - segment[3]
        if data[offset:offset + len(code)] != code:
            raise SystemExit(f'ELF bytes differ at {address:#x}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isa', choices=['neon', 'rvv', 'all'], default='all')
    args = parser.parse_args()
    output = ROOT / '_build/programs'
    output.mkdir(parents=True, exist_ok=True)
    for isa in (['neon', 'rvv'] if args.isa == 'all' else [args.isa]):
        obj, elf = output / (isa + '.o'), output / (isa + '.elf')
        assembly = ROOT / 'programs' / (isa + '-simple.S')
        if isa == 'neon':
            run(os.environ.get('LLVM_MC', 'llvm-mc-14'), '-triple=aarch64', '-filetype=obj', assembly, '-o', obj)
            run(os.environ.get('LLVM_LD', 'ld.lld-14'), '-Ttext=0x80001000', '--entry=sum_u8', obj, '-o', elf)
            tool = os.environ.get('LLVM_OBJDUMP', 'llvm-objdump-14')
        else:
            bindir = Path(os.environ.get('RVV_TOOLCHAIN_BIN', '.'))
            def toolpath(name):
                return str(bindir / name) if 'RVV_TOOLCHAIN_BIN' in os.environ else name
            run(toolpath('riscv-none-elf-as'), '-march=rv64gcv', assembly, '-o', obj)
            run(toolpath('riscv-none-elf-ld'), '-m', 'elf64lriscv', '-Ttext=0x800001bc', '--entry=sum_u8', obj, '-o', elf)
            tool = toolpath('riscv-none-elf-objdump')
        text = subprocess.check_output([tool, '-d', str(elf)], text=True)
        (output / (isa + '-disassembly.txt')).write_text(text)
        instructions = []
        for line in text.splitlines():
            if isa == 'neon':
                match = re.match(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+){4})\s*(.*)$', line)
                if not match:
                    continue
                data = bytes.fromhex(match[2])
            else:
                match = re.match(r'^\s*([0-9a-f]+):\s+([0-9a-f]+)\s+(.+)$', line)
                if not match:
                    continue
                data = bytes.fromhex(match[2])[::-1]
            instructions.append((int(match[1], 16), data.hex()))
        inventory = json.loads((ROOT / 'programs' / (isa + '-inventory.json')).read_text())
        expected = [(int(row['address'], 16), row['bytes']) for row in inventory['instructions']]
        if instructions != expected:
            raise SystemExit(f'{isa}: regenerated addresses or instruction bytes differ from the inventory')
        check_elf(elf, expected)
        print(f'{isa}: {len(instructions)} instruction addresses and bytes match.')


if __name__ == '__main__':
    main()
