"""Grow seven multidimensional fixtures and measure a separate budget per kernel.

Run from the repository root:
  .venv/bin/python -m src.workflow.verification.engine.growth_sweep --vlen 512 --seconds 600
Each kernel gets one solver process at a time; kernels run concurrently. Compilation
finishes before the shared start barrier. Every accepted shape requires an explicit
VERIFIED event and a successful process exit. No result cache is used.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from .emit import _match_fixture, generate_multidim
from .frontend import parse_signature
from ..orchestrator import PROJECT_ROOT, BITWUZLA_BIN, compile_harness


@dataclass(frozen=True)
class Plan:
    name: str
    axes: tuple[tuple[str, int], ...]  # shape value = positive index * step
    fixed: tuple[tuple[str, tuple[int, ...]], ...] = ()


PLANS = (
    Plan('f32-dwconv2d-chw', (('input_height', 1), ('input_width', 4))),
    Plan('f32-dwconv-minmax', (('channels', 1), ('output_width', 1))),
    Plan('f32-conv-hwc2chw', (('input_height', 1), ('input_width', 1), ('output_channels', 1))),
    Plan('x32-packw-gemm-goi', (('g', 1), ('nc', 1), ('kc', 1)), (('extra_bytes', (0, 8)),)),
    Plan('qd8-f32-qc4w-gemm-minmax', (('nc', 1), ('kc', 2)), (('mr', (1,)),)),
    Plan('f32-igemm-minmax', (('nc', 1), ('kc', 4)), (('mr', (1,)),)),
    Plan('f32-gemm-minmax', (('nc', 1), ('kc', 4)), (('mr', (1, 2, 3, 4)),)),
)


def frontier(plan: Plan, level: int):
    """Yield max(index)=level once, with all fixed-parameter combinations.

    The first axis at the new maximum determines which face owns each shape.
    Thus successive levels exhaust the entire positive index cube without gaps.
    """
    if level < 1:
        raise ValueError('level must be positive')
    for face in range(len(plan.axes)):
        ranges = [([level] if i == face else range(1, level if i < face else level + 1))
                  for i in range(len(plan.axes))]
        for indices in itertools.product(*ranges):
            growing = {name: index * step for (name, step), index in zip(plan.axes, indices)}
            for fixed_values in itertools.product(*(values for _, values in plan.fixed)):
                yield growing | {name: value for (name, _), value in zip(plan.fixed, fixed_values)}


def fixture_for(plan: Plan):
    neon = PROJECT_ROOT / 'kernels/source' / f'{plan.name}.c'
    rvv = PROJECT_ROOT / 'kernels/target' / f'{plan.name}.c'
    ns, rs = parse_signature(str(neon), 'test_neon'), parse_signature(str(rvv), 'test_rvv')
    spec = _match_fixture(ns, neon.read_text())
    if spec is None:
        raise ValueError(f'No multidimensional fixture for {plan.name}')
    # Every shape scalar becomes an explicit runtime argument to verify().
    spec.dims = {name: [step] for name, step in plan.axes}
    spec.dims.update({name: list(values) for name, values in plan.fixed})
    spec.grow_dim = spec.grow_cross = None
    spec.probes = []
    corrections = []
    if plan.name == 'f32-igemm-minmax':
        spec.strides['cn_stride'] = '8 * sizeof(float)'
        spec.indirect['a']['row'] = 'a_offset / sizeof(float) + kc / sizeof(float)'
        corrections.append('IGEMM output tile stride=32 bytes; indirect input rows sized in float elements.')
    if plan.name == 'f32-dwconv-minmax':
        spec.dual_weights['weights'] = dict(planes='4', ncols='channels', neon_tile='4',
                                            rvv_tile='(vlen / 32) * 4', rvv_packed=True)
        spec.indirect['input']['row'] = '((channels + 3) / 4) * 4'
        spec.strides['input_stride'] = '3 * sizeof(void*)'
        spec.params = ('xnn_f32_minmax_params', {'scalar.min': '-1e30f', 'scalar.max': '1e30f'})
        corrections.append('DWConv shared logical weights packed separately (NEON tile4, RVV variable tile).')
        corrections.append('DWConv independent input triplets, padded tail rows, and clamp [-1e30,+1e30] replacing [0,0].')
    return neon, rvv, ns, rs, spec, corrections


def shape_driver(dimensions):
    argc = len(dimensions) + 3
    args = ', '.join(f'std::stoull(argv[{i + 3}])' for i in range(len(dimensions)))
    return f'''
int main(int argc, char** argv) {{
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != {argc}) return 64;
    try {{
        size_t vlen = std::stoull(argv[1]);
        double seconds = std::stod(argv[2]);
        if (!(seconds > 0)) return 64;
        return verify({args}, vlen, seconds);
    }} catch (const std::exception& e) {{
        fprintf(stderr, "SHAPE_ERROR: %s\\n", e.what());
        return 3;
    }}
}}
'''


def prepare(plan, build_root):
    neon, rvv, ns, rs, spec, corrections = fixture_for(plan)
    # Tolerance is embedded during generation, so runtime sanitization is too late.
    old_tolerance = os.environ.pop('SALT_ULP_TOL', None)
    try:
        source = generate_multidim(str(neon), str(rvv), plan.name, ns, rs, spec)
    finally:
        if old_tolerance is not None:
            os.environ['SALT_ULP_TOL'] = old_tolerance
    if plan.name == 'qd8-f32-qc4w-gemm-minmax':
        # emit.py supplies these adapters to every generated multidim harness.
        corrections.append('C-to-C++ void-pointer load adapters; underlying symbolic loads unchanged.')
    prefix, sep, _ = source.rpartition('\nint main(')
    if not sep:
        raise ValueError('Generated harness is missing its main function')
    source = prefix + shape_driver(tuple(spec.dims))
    binary, error = compile_harness(source, plan.name, output_dir=build_root / plan.name, backend='cvc5')
    if not binary:
        raise RuntimeError(error)
    return dict(binary=str(binary), dimensions=list(spec.dims), corrections=corrections,
                fixture=vars(spec), source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                neon_sha256=hashlib.sha256(neon.read_bytes()).hexdigest(),
                rvv_sha256=hashlib.sha256(rvv.read_bytes()).hexdigest())


def classify(returncode, events):
    statuses = [event.get('status') for event in events]
    if 'COUNTEREXAMPLE' in statuses:
        return 'COUNTEREXAMPLE'
    if returncode == 0 and statuses == ['SOLVING', 'VERIFIED']:
        return 'VERIFIED'
    if returncode == 2 and 'TIMEOUT' in statuses:
        return 'TIMEOUT'
    return 'ERROR'


def execute_shape(command, seconds, env):
    start = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=max(0.001, seconds - (time.monotonic() - start)))
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
    events = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
        except json.JSONDecodeError:
            pass
    elapsed = time.monotonic() - start
    status = classify(proc.returncode, events)
    if status != 'COUNTEREXAMPLE' and (timed_out or elapsed > seconds):
        status = 'TIMEOUT'
    return dict(status=status, seconds=elapsed, returncode=proc.returncode,
                events=events, stderr=stderr, hard_deadline=timed_out)


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def run_kernel(plan, prepared, outdir, seconds, vlen, barrier, max_level=0):
    target = outdir / plan.name
    target.mkdir()
    env = os.environ.copy()
    for key in ('SALT_UF_ABSTRACT', 'SALT_ULP_TOL', 'SALT_CVC5_OPTIONS', 'SALT_DUMP_SMT2', 'SALT_STATS',
                'SALT_BACKEND', 'SALT_BITWUZLA'):
        env.pop(key, None)
    # Use the same automatic portfolio as the ordinary verifier, where available.
    if BITWUZLA_BIN.is_file():
        env.update(SALT_BACKEND='auto', SALT_BITWUZLA=str(BITWUZLA_BIN))
    result = dict(kernel=plan.name, vlen=vlen, budget_seconds=seconds, status='RUNNING',
                  verified_shapes=0, completed_level=0, attempted_shapes=0,
                  axes=dict(plan.axes), fixed=dict(plan.fixed), dimensions=prepared['dimensions'],
                  corrections=prepared['corrections'], last_verified_shape=None)
    write_json(target/'result.json', result)
    barrier.wait()
    start = time.monotonic()
    result['started_utc'] = datetime.now(timezone.utc).isoformat()
    deadline = start + seconds
    with (target/'shapes.jsonl').open('w') as log:
        for level in itertools.count(1):
            for shape in frontier(plan, level):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    result.update(status='BUDGET_EXHAUSTED', stopped_shape=shape, stopped_level=level)
                    break
                result.update(current_shape=shape, current_level=level)
                write_json(target/'result.json', result)
                command = [prepared['binary'], str(vlen), str(remaining)] + [str(shape[d]) for d in prepared['dimensions']]
                record = execute_shape(command, remaining, env)
                record.update(shape=shape, level=level, elapsed_seconds=time.monotonic()-start)
                result['attempted_shapes'] += 1
                log.write(json.dumps(record) + '\n')
                log.flush()
                if record['status'] != 'VERIFIED':
                    result.update(status=record['status'], stopped_shape=shape, stopped_level=level,
                                  failure=record)
                    break
                result['verified_shapes'] += 1
                result['last_verified_shape'] = shape
                result['elapsed_seconds'] = time.monotonic()-start
                write_json(target/'result.json', result)
            else:
                result['completed_level'] = level
                write_json(target/'result.json', result)
                print(f"{plan.name}: completed level {level}, {result['verified_shapes']} shapes", flush=True)
                if max_level and level >= max_level:
                    result['status'] = 'MAX_LEVEL_REACHED'
                    break
                continue
            break
    result['elapsed_seconds'] = time.monotonic()-start
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result.pop('current_shape', None)
    result.pop('current_level', None)
    write_json(target/'result.json', result)
    print(f"{plan.name}: {result['status']}, completed level {result['completed_level']}, {result['verified_shapes']} shapes", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vlen', type=int, default=512)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--kernel', action='append', choices=[p.name for p in PLANS])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-level', type=int, default=0, help='Only for finite smoke checks; zero keeps growing')
    args = parser.parse_args()
    if args.vlen < 128 or args.vlen & (args.vlen-1) or args.seconds <= 0 or args.max_level < 0:
        parser.error('VLEN must be a power of two >=128, seconds positive, max-level nonnegative')
    plans = [p for p in PLANS if not args.kernel or p.name in args.kernel]
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = (args.output or PROJECT_ROOT/'results'/f'growth_vlen{args.vlen}_{stamp}').resolve()
    out.mkdir(parents=True, exist_ok=False)
    build_root = PROJECT_ROOT/'build/verification_cvc5'/out.name
    metadata = dict(vlen=args.vlen, budget_per_kernel_seconds=args.seconds, workers=len(plans),
                    max_level=args.max_level, cpu_count=os.cpu_count(), compile_excluded=True,
                    input_range=None, uf_abstraction=False, output_tolerance_override=None,
                    stop_policy='Stop each kernel at its first non-VERIFIED shape; completed levels have no gaps.',
                    solver='cvc5 1.3.1, automatic Bitwuzla routing for pure bit-vector queries',
                    scope='Existing fixture assumptions and output comparison. QC4W retains its packing and scale/bias constraints.',
                    files={})
    for folder in ('src/verification_cvc5', 'src/workflow/verification/engine'):
        for p in sorted((PROJECT_ROOT/folder).rglob('*')):
            if p.suffix in ('.hpp', '.py', '.h', '.txt'):
                metadata['files'][str(p.relative_to(PROJECT_ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    prepared = {}
    for plan in plans:
        print(f'Preparing {plan.name}...', flush=True)
        prepared[plan.name] = prepare(plan, build_root)
    metadata['prepared'] = prepared
    write_json(out/'manifest.json', metadata)
    print(f'All {len(plans)} harnesses compiled. Starting {args.seconds:g}s per kernel at VLEN={args.vlen}. Results: {out}', flush=True)
    barrier = threading.Barrier(len(plans))
    with ThreadPoolExecutor(max_workers=len(plans)) as pool:
        jobs = [pool.submit(run_kernel, plan, prepared[plan.name], out, args.seconds, args.vlen, barrier, args.max_level)
                for plan in plans]
        results = [job.result() for job in jobs]
    write_json(out/'summary.json', results)
    print(f'Summary: {out / "summary.json"}', flush=True)


if __name__ == '__main__':
    main()
