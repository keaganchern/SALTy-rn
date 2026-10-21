#!/usr/bin/env python3
"""Regenerate selected instruction traces with the recorded models and constraints.

Outputs go to _build/extracted; committed sources and traces are never overwritten.
Run under the pinned opam environment after building the Islaris frontend and Isla.
"""
import argparse
import hashlib
import json
import os
import subprocess
import re
import shlex
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def runtime_config(source, destination, architecture):
    """Replace only historical absolute tool paths, preserving semantic settings."""
    text = source.read_text()
    changes = []
    if architecture == 'aarch64':
        commands = {'assembler': os.environ.get('LLVM_MC', 'llvm-mc-14'),
                    'objdump': os.environ.get('LLVM_OBJDUMP', 'llvm-objdump-14'),
                    'linker': os.environ.get('LLVM_LD', 'ld.lld-14'),
                    'nm': os.environ.get('LLVM_NM', 'llvm-nm-14')}
    else:
        bindir = os.environ.get('RVV_TOOLCHAIN_BIN')
        commands = {key: str(Path(bindir) / name) if bindir else name
                    for key, name in [('assembler', 'riscv-none-elf-as'),
                                      ('objdump', 'riscv-none-elf-objdump'),
                                      ('linker', 'riscv-none-elf-ld'),
                                      ('nm', 'riscv-none-elf-nm')]}
    def replace(match):
        key, command = match[1], json.loads(match[2])
        parts = shlex.split(command)
        if not parts or not Path(parts[0]).is_absolute():
            return match[0]
        if shutil.which(commands[key]) is None:
            raise SystemExit(f'Missing {key}: {commands[key]}; select the tool via LLVM_* or RVV_TOOLCHAIN_BIN')
        updated = shlex.join([commands[key], *parts[1:]])
        changes.append({'field': key, 'recorded': command, 'runtime': updated})
        return key + ' = ' + json.dumps(updated)
    text = re.sub(r'^(assembler|objdump|linker|nm)\s*=\s*("[^"\n]*")$', replace,
                  text, flags=re.MULTILINE)
    destination.write_text(text)
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['NEON', 'RVV', 'Bridge', 'all'], default='all')
    parser.add_argument('--address', help='Select one hexadecimal instruction address')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'traces/manifest.json').read_text())
    frontend = Path(os.environ.get('ISLARIS_FRONTEND',
                    str(ROOT / 'deps/islaris/_build/default/frontend/main.exe'))).resolve()
    config_root = frontend.parent.parent.parent / 'install/default/etc/islaris'
    config_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = str(ROOT / 'scripts') + os.pathsep + env.get('PATH', '')
    selected = [row for row in manifest['instructions']
                if (args.group == 'all' or row['group'] == args.group)
                and (not args.address or int(row['address'], 16) == int(args.address, 16))]
    if not selected:
        raise SystemExit('No instruction matches the selection')
    for row in selected:
        output = ROOT / '_build/extracted' / Path(row['coq']).parent.relative_to('theories/Generated')
        output.mkdir(parents=True, exist_ok=True)
        stem = Path(row['coq']).stem
        (output / (stem + '-comparison.json')).unlink(missing_ok=True)
        dump = output / Path(row['dump']).name
        original_config = (ROOT / row['config']).resolve()
        if hashlib.sha256(original_config.read_bytes()).hexdigest() != row['config_sha256']:
            raise SystemExit(f'Recorded configuration hash mismatch: {original_config}')
        config = output / original_config.name
        overrides = runtime_config(original_config, config, row['architecture'])
        relative_config = os.path.relpath(config, config_root)
        original = (ROOT / row['dump']).read_text().splitlines()
        dump.write_text(f'//@isla-config: {relative_config}\n' + '\n'.join(original[1:]) + '\n')
        namespace = 'Reduction.' + '.'.join(Path(row['coq']).parent.relative_to('theories').parts)
        subprocess.run([str(frontend), '-d', '-a', row['architecture'], '-s',
                        '--coqdir=' + namespace, '-o', str(output), str(dump)],
                       cwd=ROOT, env=env, check=True)
        trace = output / (stem + '.isla')
        coq = output / (stem + '.v')
        trace_hash = hashlib.sha256(trace.read_bytes()).hexdigest()
        coq_hash = hashlib.sha256(coq.read_bytes()).hexdigest()
        report = {'address': row['address'], 'trace_sha256': trace_hash,
                  'coq_sha256': coq_hash,
                  'runtime_config_sha256': hashlib.sha256(config.read_bytes()).hexdigest(),
                  'toolchain_overrides': overrides,
                  'matches_recorded_trace': trace_hash == row['trace_sha256'],
                  'matches_recorded_coq': coq_hash == row['coq_sha256']}
        (output / (stem + '-comparison.json')).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
        if not report['matches_recorded_trace'] or not report['matches_recorded_coq']:
            raise SystemExit('Regenerated trace/source differs; inspect the output before accepting it')


if __name__ == '__main__':
    main()
