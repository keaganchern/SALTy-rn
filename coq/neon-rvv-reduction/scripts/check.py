#!/usr/bin/env python3
"""Recursively recheck all project objects, then report exported assumptions."""
import json
import subprocess
import hashlib
import datetime
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    started = time.monotonic()
    evidence = ROOT / '_build/check'
    evidence.mkdir(parents=True, exist_ok=True)
    # Remove an earlier success report before starting a new check.
    (evidence / 'result.json').unlink(missing_ok=True)
    manifest = json.loads((ROOT / 'traces/manifest.json').read_text())
    flags = ['-Q', str(ROOT / 'deps/islaris/_build/default/theories'), 'isla',
             '-Q', str(ROOT / 'theories'), 'Reduction']
    # Include every source, even generated data and helpers outside the root closures.
    modules = ['Reduction.' + '.'.join(p.relative_to(ROOT / 'theories').with_suffix('').parts)
               for p in sorted((ROOT / 'theories').rglob('*.v'))]
    print(f'Recursively checking {len(modules)} project modules with coqchk...', flush=True)
    with (evidence / 'coqchk.log').open('w') as log:
        subprocess.run(['coqchk', '-bytecode-compiler', 'yes', *flags, *modules], cwd=ROOT, check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    print('Recursive object checking passed; inspecting exported assumptions...', flush=True)
    roots = [m for entries in manifest['proof_roots'].values() for m in entries]
    commands = ''.join(f'Require Import {m}.\n' for m in roots)
    commands += ''.join(f'Print Assumptions {name}.\n' for name in manifest['exported_theorems'])
    # Coqchk above checks all proof terms independently of the proof tactics.
    result = subprocess.run(['coqtop', '-quiet', '-q', *flags], cwd=ROOT,
                            input=commands + 'Quit.\n', text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout)
    (evidence / 'assumptions.log').write_text(result.stdout)
    if result.returncode or 'Error:' in result.stdout:
        raise SystemExit('Exported-root import failed')
    if ('Axioms:' in result.stdout or 'Variables:' in result.stdout
            or 'could not be accessed' in result.stdout
            or 'Cannot access' in result.stdout
            or result.stdout.count('Closed under the global context') != len(manifest['exported_theorems'])):
        raise SystemExit('An exported theorem has assumptions or an incomplete assumption report')
    print(f'Independent recursive checking passed for {len(modules)} project modules.')
    report = {
        'status': 'passed',
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'elapsed_seconds': round(time.monotonic() - started, 2),
        'coq_version': subprocess.check_output(['coqc', '--version'], text=True).strip(),
        'project_modules': len(modules),
        'assumption_reports_closed': len(manifest['exported_theorems']),
        'recursive_external_dependency_check': True,
        'coqchk_bytecode_compiler': True,
        'manifest_sha256': hashlib.sha256((ROOT / 'traces/manifest.json').read_bytes()).hexdigest(),
        'objects': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ROOT / 'theories').rglob('*.vo'))},
    }
    (evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
