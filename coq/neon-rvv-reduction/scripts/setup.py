#!/usr/bin/env python3
"""Create the pinned proof environment and build the external Islaris libraries."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing-switch', action='store_true',
                        help='Use the current opam switch instead of creating ./_opam')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'traces/manifest.json').read_text())
    if not args.existing_switch and not (ROOT / '_opam').exists():
        run('opam', 'switch', 'create', '.', 'ocaml-base-compiler.' + manifest['ocaml'], '-y')
    run('opam', 'repository', 'add', 'coq-released',
        'https://coq.inria.fr/opam/released', '--this-switch', '-y')
    run('opam', 'repository', 'add', 'iris-dev',
        'git+https://gitlab.mpi-sws.org/iris/opam.git', '--this-switch', '-y')
    run('opam', 'install', '.', '--deps-only', '-y')
    info = manifest['toolchain']['islaris']
    checkout = ROOT / 'deps/islaris'
    checkout.parent.mkdir(exist_ok=True)
    if not checkout.exists():
        run('git', 'clone', '--no-checkout', info['repository'], checkout)
        run('git', '-C', checkout, 'checkout', '--detach', info['commit'])
    actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != info['commit']:
        raise SystemExit(f'Islaris checkout differs from the pinned commit: {actual}')
    run('opam', 'exec', '--', 'dune', 'build', '--root', checkout,
        'theories/aarch64/aarch64.vo', 'theories/riscv64/riscv64.vo', 'frontend/main.exe', '-j4')
    print('Proof dependencies are ready. Run: opam exec -- make -j2')


if __name__ == '__main__':
    main()
