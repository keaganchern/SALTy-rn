#!/usr/bin/env python3
"""Check committed source, instruction, configuration and raw-trace bindings."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'traces/manifest.json').read_text())
    for item in manifest['sources']:
        path = ROOT / item['path']
        if digest(path.read_bytes()) != item['sha256']:
            raise SystemExit(f'Source hash mismatch: {item["path"]}')
    for item in manifest['instructions']:
        for path_key, hash_key in [('config', 'config_sha256'), ('coq', 'coq_sha256'),
                                   ('trace', 'compressed_sha256')]:
            if digest((ROOT / item[path_key]).read_bytes()) != item[hash_key]:
                raise SystemExit(f'Artifact hash mismatch: {item[path_key]}')
        if digest(gzip.decompress((ROOT / item['trace']).read_bytes())) != item['trace_sha256']:
            raise SystemExit(f'Raw trace hash mismatch: {item["trace"]}')
        lines = (ROOT / item['dump']).read_text().splitlines()
        constraints = [s.split(': ', 1)[1] for s in lines if s.startswith('//@constraint:')]
        if constraints != item['constraints']:
            raise SystemExit(f'Constraint mismatch: {item["dump"]}')
        if lines[0] != '//@isla-config: ' + item['config']:
            raise SystemExit(f'Configuration mismatch: {item["dump"]}')
        address, instruction = lines[-1].split(':', 1)
        opcode = instruction.split()[0]
        if int(address, 16) != int(item['address'], 16) or int(opcode, 16) != int(item['opcode'], 16):
            raise SystemExit(f'Instruction mismatch: {item["dump"]}')
    for isa, count in [('neon', 20), ('rvv', 19)]:
        inventory = json.loads((ROOT / f'programs/{isa}-inventory.json').read_text())
        if digest((ROOT / inventory['assembly_path']).read_bytes()) != inventory['assembly_sha256']:
            raise SystemExit(f'Assembly hash mismatch: {inventory["assembly_path"]}')
        items = [s for s in manifest['instructions'] if s['group'] == isa.upper()]
        actual = {(s['address'], s['opcode'], s['bytes']) for s in items}
        expected = {(s['address'], s['opcode'], s['bytes']) for s in inventory['instructions']}
        if len(items) != count or len(expected) != count or actual != expected:
            raise SystemExit(f'Incomplete instruction inventory: {isa}')
    print(f'Input bindings verified: {len(manifest["sources"])} Coq sources, '
          f'{len(manifest["instructions"])} instruction traces.')


if __name__ == '__main__':
    main()
