#!/usr/bin/env python3
"""Build the pinned Isla extractor and fetch hash-checked Sail model snapshots."""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((ROOT / 'traces/manifest.json').read_text())
    info = manifest['toolchain']['isla']
    checkout = ROOT / 'deps/isla'
    checkout.parent.mkdir(exist_ok=True)
    if not checkout.exists():
        subprocess.run(['git', 'clone', '--no-checkout', info['repository'], str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'checkout', '--detach', info['commit']], check=True)
    actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != info['commit']:
        raise SystemExit(f'Isla checkout differs from the pinned commit: {actual}')
    subprocess.run(['cargo', 'build', '--locked', '--release', '--bin', 'isla-footprint'],
                   cwd=checkout, check=True)
    models = ROOT / 'deps/models'
    models.mkdir(exist_ok=True)
    for model in manifest['models'].values():
        target = models / model['snapshot_file']
        if not target.exists():
            # Keep an incomplete download separate from the accepted snapshot.
            temporary = target.with_suffix('.download')
            urllib.request.urlretrieve(model['url'], temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != model['sha256']:
                raise SystemExit(f'Sail model hash mismatch: {temporary}')
            temporary.rename(target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != model['sha256']:
            raise SystemExit(f'Sail model hash mismatch: {target}')
    print('Extraction dependencies are ready. Run: opam exec -- python3 scripts/extract.py')


if __name__ == '__main__':
    main()
