"""
Verification orchestrator — compiles and runs harnesses with progressive batch sizing.

Runs batch=1,2,3,... in a single process. Stops when any single batch
exceeds the per-batch timeout, or on counterexample/crash.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # src/workflow/verification/ -> SALT/

# Backend → (cmake source dir, build subdir under build/) mapping.  The
# generated harness is identical between backends; only the include path /
# library link differs.
VERIFICATION_DIRS = {
    "bitwuzla": PROJECT_ROOT / "src" / "verification_bw",
    "cvc5":     PROJECT_ROOT / "src" / "verification_cvc5",
}
VERIFICATION_BUILD_SUBDIRS = {
    "bitwuzla": "verification_bw",
    "cvc5":     "verification_cvc5",
}

# Auto-routing portfolio: the v2 (cvc5) harness routes each query at runtime —
# pure-BV → bitwuzla (it wins the hard symbolic-int BV cases), FP → cvc5 — via
# the SALT_BACKEND=auto / SALT_BITWUZLA env hooks in core/context.hpp.
BITWUZLA_BIN = PROJECT_ROOT / "third_party" / "bitwuzla" / "install" / "bin" / "bitwuzla"
if not BITWUZLA_BIN.is_file():
    BITWUZLA_BIN = Path(shutil.which("bitwuzla") or BITWUZLA_BIN)
BITWUZLA_LIB = PROJECT_ROOT / "third_party" / "bitwuzla" / "install" / "lib64"

# Serializes libclang harness generation when many kernels verify in one process
# (the --jobs ThreadPool). Process-local, so the ProcessPool sweep is unaffected.
import threading as _threading
_GEN_LOCK = _threading.Lock()

# Legacy alias kept for any downstream import.
VERIFICATION_DIR = VERIFICATION_DIRS["bitwuzla"]


@dataclass
class BatchResult:
    batch: int
    status: str        # "VERIFIED", "COUNTEREXAMPLE", "TIMEOUT", "CRASH"
    elapsed: float = 0.0
    details: str = ""
    config: str = ""


@dataclass
class VerificationResult:
    kernel_name: str
    verdict: str           # "ALL_PASSED", "COUNTEREXAMPLE", "COMPILE_ERROR",
                           # "MISSING_INTRINSIC", "UNSUPPORTED", "CRASH",
                           # "HARNESS_GEN_ERROR", "EMPTY_RANGE", "PARTIAL"
    verified_batches: list[BatchResult] = field(default_factory=list)
    max_verified_batch: int = 0
    compile_error: str = ""
    missing_intrinsics: list[str] = field(default_factory=list)
    counterexample: dict = field(default_factory=dict)
    configs_tested: int = 0
    config_results: dict = field(default_factory=dict)  # config_name → max_verified_batch
    failed_config: str = ""
    timeouts: list[dict] = field(default_factory=list)   # where each config's coverage stopped
    elapsed: float = 0.0                                  # total solver-process wall time (s)

    def to_json(self) -> str:
        d = {
            "kernel": self.kernel_name,
            "verdict": self.verdict,
            "max_verified_batch": self.max_verified_batch,
            "num_verified": len([b for b in self.verified_batches if b.status == "VERIFIED"]),
        }
        if self.configs_tested > 1:
            d["configs_tested"] = self.configs_tested
            d["config_results"] = self.config_results
        if self.failed_config:
            d["failed_config"] = self.failed_config
        if self.missing_intrinsics:
            d["missing_intrinsics"] = self.missing_intrinsics
        if self.counterexample:
            d["counterexample"] = self.counterexample
        if self.compile_error:
            d["compile_error"] = self.compile_error[:500]
        d.update(self.coverage())
        return json.dumps(d, indent=2)

    def coverage(self) -> dict:
        """What was actually proved: shapes (multi-dim fixtures), timeouts, solve times."""
        ok = [b for b in self.verified_batches if b.status == "VERIFIED"]
        cov = {}
        shapes = sorted({json.loads(b.details)["dims"] for b in ok if b.details and '"dims"' in b.details},
                        key=lambda s: [int(x) for x in s.split(",") if x.lstrip("-").isdigit()])
        if shapes:
            dims = [[int(x) for x in s.split(",")] for s in shapes]
            cov["verified_shapes"] = len(shapes)
            cov["shape_dim_max"] = [max(col) for col in zip(*dims)]
            cov["largest_shape"] = max(shapes, key=lambda s: (eval_product(s), s))
            if len(shapes) <= 64:
                cov["shapes"] = shapes
        if self.timeouts:
            cov["timeouts"] = self.timeouts[:16]
        times = [b.elapsed for b in ok if b.elapsed > 0]
        if times:
            cov["query_s_max"] = round(max(times), 2)
        if self.elapsed:
            cov["elapsed_s"] = round(self.elapsed, 1)
        return cov


def eval_product(shape: str) -> int:
    prod = 1
    for x in shape.split(","):
        prod *= max(int(x), 1)
    return prod


def compile_harness(harness_source: str, kernel_name: str,
                     output_dir: Path = None,
                     backend: str = "bitwuzla") -> tuple[Optional[Path], str]:
    """Compile a C++ harness via CMake. Returns (binary_path, error_string).

    backend: "bitwuzla" (default) or "cvc5".  Picks the cmake source directory
    and the build dir layout.

    Layout (bitwuzla):
      build/verification/harnesses/<kernel>.cpp   — source
      build/verification/cmake_build/             — shared CMake build dir
      build/verification/cmake_build/<kernel>     — compiled binary
    Layout (cvc5):
      build/verification_cvc5_pipeline/...        — same shape, different root
    """
    if backend not in VERIFICATION_DIRS:
        raise ValueError(f"Unknown backend '{backend}'. "
                         f"Supported: {list(VERIFICATION_DIRS)}")
    cmake_source_dir = VERIFICATION_DIRS[backend]

    if output_dir is None:
        output_dir = PROJECT_ROOT / "build" / VERIFICATION_BUILD_SUBDIRS[backend]

    harness_dir = output_dir / "harnesses"
    harness_dir.mkdir(parents=True, exist_ok=True)
    cmake_build_dir = output_dir / "cmake_build"
    cmake_build_dir.mkdir(parents=True, exist_ok=True)

    # Write harness source (one file per kernel, overwritten on re-verify)
    harness_name = f"verify_{kernel_name}"
    src_path = harness_dir / f"{harness_name}.cpp"
    src_path.write_text(harness_source)

    # Configure CMake (reconfigure each time to pick up the right source)
    configure_cmd = [
        "cmake", str(cmake_source_dir),
        f"-DHARNESS_SRC={src_path}",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    cmake_cache = cmake_build_dir / "CMakeCache.txt"
    if not cmake_cache.exists():
        log.info("Configuring CMake...")
    result = subprocess.run(configure_cmd, capture_output=True, text=True,
                            cwd=str(cmake_build_dir), timeout=60)
    if result.returncode != 0:
        error = result.stderr + "\n" + result.stdout
        log.error("CMake configure failed:\n%s", error[:2000])
        return None, error

    # Build
    build_cmd = ["cmake", "--build", ".", "--target", harness_name, "-j"]
    log.info("Compiling %s...", harness_name)
    t0 = time.perf_counter()
    result = subprocess.run(build_cmd, capture_output=True, text=True,
                            cwd=str(cmake_build_dir), timeout=120)
                            
    if result.returncode != 0 and "No rule to make target" in (result.stdout + result.stderr):
        log.info("Stale CMake target; reconfiguring from a clean cache...")
        (cmake_build_dir / "CMakeCache.txt").unlink(missing_ok=True)
        shutil.rmtree(cmake_build_dir / "CMakeFiles", ignore_errors=True)
        rc = subprocess.run(configure_cmd, capture_output=True, text=True,
                            cwd=str(cmake_build_dir), timeout=60)
        if rc.returncode != 0:
            error = rc.stderr + "\n" + rc.stdout
            log.error("CMake reconfigure failed:\n%s", error[:2000])
            return None, error
        result = subprocess.run(build_cmd, capture_output=True, text=True,
                                cwd=str(cmake_build_dir), timeout=120)

    compile_time = time.perf_counter() - t0

    if result.returncode != 0:
        error = result.stderr + "\n" + result.stdout
        log.error("Compilation failed (%.1fs):\n%s", compile_time, error[:2000])
        return None, error

    bin_path = cmake_build_dir / harness_name
    if not bin_path.exists():
        return None, f"Binary not found at {bin_path}"

    log.info("Compiled successfully: %s (%.1fs)", bin_path.name, compile_time)
    return bin_path, ""


def extract_missing_intrinsics(compile_error: str) -> list[str]:
    """Parse compiler errors to find undefined/undeclared SIMD intrinsics."""
    missing = set()
    patterns = [
        r"undeclared identifier '(\w+)'",
        r"no matching function for call to '(\w+)'",
        r"undefined reference to.*?'(?:salt::)?(\w+)'",
        r"implicit declaration of function '(\w+)'",
    ]
    for pat in patterns:
        for m in re.finditer(pat, compile_error):
            name = m.group(1)
            if name.startswith(('v', '__riscv_')):
                missing.add(name)
    return sorted(missing)


def run_verification(bin_path: Path, kernel_name: str,
                      time_budget: int = 600,
                      max_batch: int = 0,
                      vlen: int = 256,
                      min_batch: int = 1,
                      route: bool = False) -> VerificationResult:
    """Run the harness in a single process under ONE total wall-clock budget.

    The harness sweeps increasing batch sizes (min_batch, min_batch+1, …) and each
    solver query gets whatever is left of `time_budget` seconds; it stops when the
    budget is spent (→ TIMEOUT/PARTIAL), on a counterexample, or at max_batch.

    max_batch == 0 means UNBOUNDED — keep increasing the batch until the budget runs
    out (the batch is not capped, only the total time is). max_batch > 0 caps it.
    time_budget == 0 disables the budget (then max_batch must be > 0, else the harness
    defaults to a 600 s budget so it can't run forever).
    """
    result = VerificationResult(kernel_name=kernel_name, verdict="ALL_PASSED")
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = "/usr/local/lib"
    env["LD_LIBRARY_PATH"] = "/usr/local/lib"
    if route:
        bwz = os.environ.get("SALT_BITWUZLA", str(BITWUZLA_BIN))
        env["SALT_BACKEND"] = "auto"
        env["SALT_BITWUZLA"] = bwz
        env["LD_LIBRARY_PATH"] = f"{BITWUZLA_LIB}:{env['LD_LIBRARY_PATH']}"
        log.info("  Routing: auto (pure-BV→bitwuzla, FP→cvc5); bitwuzla=%s", bwz)

    # The harness self-limits to `time_budget` wall-clock. Kill the process only as a
    # backstop a bit past that (last-query overshoot + final summary print).
    overall_timeout = None if time_budget <= 0 else (time_budget + 60)

    log.info("  Running: %s start=%d end=%s vlen=%d budget=%ds", bin_path.name,
             min_batch, max_batch or "unbounded", vlen, time_budget)

    t0 = time.perf_counter()
    last_logged_batch = 0
    current_config = ""
    stderr_buf = []
    solve_started = {}   # (config, label) → time of its SOLVING event

    # Stream stdout line-by-line for real-time progress
    try:
        proc = subprocess.Popen(
            [str(bin_path), str(min_batch), str(max_batch), str(vlen), str(time_budget)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env,
            bufsize=1,  # line-buffered on the Python side of the pipe
        )

        import threading

        def _read_stderr():
            for line in proc.stderr:
                stderr_buf.append(line)

        stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        stderr_thread.start()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # Check overall timeout (None = no outer kill)
            if overall_timeout is not None and time.perf_counter() - t0 > overall_timeout:
                log.warning("Overall timeout after %.1fs — killing process",
                            time.perf_counter() - t0)
                proc.kill()
                result.verdict = "PARTIAL"
                break

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            status = data.get("status", "")
            batch = data.get("batch", 0)
            config = data.get("config", "default")
            # Progress label: elementwise harnesses report "batch"; multi-dim
            # ("shape") harnesses report "dims" (e.g. "10,16"). Show whichever is
            # present so progress prints for every shape, not just "batch=0".
            label = f"dims=[{data['dims']}]" if "dims" in data else f"batch={batch}"

            # Log config transitions
            if config != current_config:
                if current_config:
                    log.info("  config=%s: verified up to batch=%d",
                             current_config, result.config_results.get(current_config, 0))
                current_config = config
                log.info("  Starting config=%s...", config)
                last_logged_batch = 0

            if status == "SOLVING":
                solve_started[(config, label)] = time.perf_counter()
                # Visibility ping from verify() before check_sat() runs.
                # Prevents silence when a single batch takes a long time.
                elapsed_so_far = time.perf_counter() - t0
                log.info("  %-16s solving... (%.1fs)", label, elapsed_so_far)

            elif status == "VERIFIED":
                result.max_verified_batch = max(result.max_verified_batch, batch)
                started = solve_started.pop((config, label), None)
                result.verified_batches.append(BatchResult(
                    batch=batch, status="VERIFIED",
                    elapsed=(time.perf_counter() - started) if started else 0.0,
                    details=json.dumps(data) if "dims" in data else "", config=config))
                result.config_results[config] = max(
                    result.config_results.get(config, 0), batch)
                # Log every batch
                elapsed_so_far = time.perf_counter() - t0
                log.info("  %-16s VERIFIED  (%.1fs)", label, elapsed_so_far)
                last_logged_batch = batch

            elif status == "COUNTEREXAMPLE":
                result.verdict = "COUNTEREXAMPLE"
                result.counterexample = data
                result.failed_config = config
                result.verified_batches.append(
                    BatchResult(batch=batch, status="COUNTEREXAMPLE", details=json.dumps(data)))
                log.error("  %-16s COUNTEREXAMPLE config=%s", label, config)
                log.error("    input[%s]=%s  neon_out=%s  rvv_out=%s",
                           data.get("fail_index", "?"),
                           data.get("input_at_fail", "?"),
                           data.get("neon_out", "?"),
                           data.get("rvv_out", "?"))

            elif status == "TIMEOUT":
                result.verdict = "PARTIAL"
                result.timeouts.append({"config": config, "at": label})
                log.info("  config=%s — %ds budget spent at %s; verified up to batch=%d",
                         config, time_budget, label,
                         result.config_results.get(config, 0))

            elif status == "ALL_VERIFIED" and result.verdict == "ALL_PASSED":
                # Harness always prints ALL_VERIFIED at its `done:` label, even
                # after a TIMEOUT goto. Only trust it if no TIMEOUT/COUNTEREXAMPLE
                # has already downgraded the verdict.
                result.max_verified_batch = data.get("end", 0)
                result.configs_tested = data.get("configs", 1)

        proc.wait(timeout=10)
        stderr_thread.join(timeout=5)

    except Exception as e:
        elapsed = time.perf_counter() - t0
        log.warning("Process error after %.1fs: %s", elapsed, e)
        try:
            proc.kill()
        except Exception:
            pass
        if result.verdict == "ALL_PASSED":
            result.verdict = "PARTIAL"

    returncode = proc.returncode if proc.returncode is not None else -1
    stderr_text = "".join(stderr_buf)

    # Check for crash
    if result.verdict not in ("PARTIAL", "COUNTEREXAMPLE"):
        if returncode not in (0, 1, 2):
            result.verdict = "CRASH"
            result.compile_error = stderr_text[:1000]
            log.error("Harness crashed (exit=%d): %s", returncode, stderr_text[:500])
        elif returncode == 1 and result.verdict != "COUNTEREXAMPLE":
            result.verdict = "CRASH"
            result.compile_error = stderr_text[:1000]

    total_elapsed = time.perf_counter() - t0
    result.elapsed = total_elapsed
    num_verified = len([b for b in result.verified_batches if b.status == "VERIFIED"])
    num_configs = len(result.config_results)

    # Harness alignment can produce an empty loop body (e.g. byte-count kernel
    # with end < elem_bytes). It still emits ALL_VERIFIED at `done:`, which
    # otherwise looks like a successful run.
    if result.verdict == "ALL_PASSED" and num_verified == 0:
        result.verdict = "EMPTY_RANGE"
        result.max_verified_batch = 0

    if result.verdict == "ALL_PASSED":
        log.info("═══════════════════════════════════════════════════════════")
        log.info("VERIFIED: %s — %d batches, %d configs, max_batch=%d (%.1fs)",
                 kernel_name, num_verified, num_configs, result.max_verified_batch,
                 total_elapsed)
    elif result.verdict == "COUNTEREXAMPLE":
        log.error("FAILED: %s — counterexample at batch=%d config=%s",
                  kernel_name, result.counterexample.get("batch", 0), result.failed_config)
    elif result.verdict == "PARTIAL":
        log.info("PARTIAL: %s — %d batches verified, max=%d (%.1fs)",
                 kernel_name, num_verified, result.max_verified_batch, total_elapsed)
    elif result.verdict == "EMPTY_RANGE":
        log.warning("EMPTY: %s — no batches in requested range (alignment skipped all of [min,max]?)",
                    kernel_name)
    else:
        log.error("RESULT: %s — %s", kernel_name, result.verdict)

    return result


def verify_kernel(neon_path: str, rvv_path: str,
                   kernel_name: str = "",
                   params_init: str = "",
                   param_configs: list[tuple[str, str]] = None,
                   symbolic_params: bool = False,
                   vlen: int = 256,
                   time_budget: int = 600,
                   max_batch: int = 0,
                   min_batch: int = 1,
                   backend: str = "auto",
                   input_range: tuple = None,
                   build_dir: Path = None,
                   llm_client=None,
                   reference_isa: str = "neon") -> VerificationResult:
    """Full pipeline: generate (v2 engine) → compile → run.

    The generator (src/workflow/verification/engine) is the sole engine: a libclang
    frontend + uniform/fixture-family template. (It replaced an older Shape-tree /
    size_inferrer / profile pipeline, now removed.)
    cvc5-only (the harness includes the cvc5 salt.hpp shims).

    symbolic_params: prove for ALL valid params (else concrete edge configs).
    input_range: (lo, hi) constrains F32 inputs to a finite band — needed for the
      FP-multiply families (gemm/igemm/dwconv/vmulcaddc/ibilinear); the verdict is
      tagged config:finite to record the weakened claim. None = full domain.
    """

    # Always derive kernel_name from filename if not provided
    if not kernel_name:
        kernel_name = Path(neon_path).stem

    # backend="auto" (default) → build the cvc5 harness, but route per-query at
    # runtime (pure-BV→bitwuzla, FP→cvc5) via the SALT_BACKEND env hook.  If the
    # bitwuzla binary isn't present, degrade gracefully to cvc5-only.
    route = backend == "auto"
    compile_backend = "cvc5" if route else backend
    if route:
        bwz = os.environ.get("SALT_BITWUZLA", str(BITWUZLA_BIN))
        if not Path(bwz).exists():
            log.warning("  backend=auto but bitwuzla not found at %s — using cvc5-only", bwz)
            route = False

    log.info("═══════════════════════════════════════════════════════════")
    log.info("Verification: %s", kernel_name)
    log.info("  %s reference: %s", reference_isa.upper(), neon_path)
    log.info("  RVV source:  %s", rvv_path)
    log.info("  Backend: %s", backend)
    log.info("  VLEN=%d  max_batch=%s  time_budget=%ds",
             vlen, max_batch or "unbounded", time_budget)

    params_mode = "symbolic" if symbolic_params else "concrete"
    log.info("  Mode: params=%s%s", params_mode,
             f", input-range={input_range}" if input_range else " (full domain)")

    # 1. Generate harness (v2 engine — the only engine)
    log.info("Step 1/3: Generating verification harness (v2)...")
    try:
        from .engine.emit import generate_harness
        with _GEN_LOCK:   # libclang cindex isn't reliably thread-safe across concurrent parses
            harness = generate_harness(
                neon_path, rvv_path, kernel_name,
                params_mode=params_mode,
                input_range=input_range,
                reference_isa=reference_isa,
            )
    except NotImplementedError as e:
        log.warning("Kernel not yet supported by v2 engine: %s", e)
        return VerificationResult(
            kernel_name=kernel_name, verdict="UNSUPPORTED", compile_error=str(e))
    except Exception as e:
        log.error("Harness generation failed: %s", e)
        return VerificationResult(
            kernel_name=kernel_name, verdict="HARNESS_GEN_ERROR", compile_error=str(e))
    log.info("  Harness generated (%d lines)", harness.count('\n') + 1)

    # 2. Compile
    log.info("Step 2/3: Compiling verification harness...")
    bin_path, compile_error = compile_harness(harness, kernel_name, backend=compile_backend,
                                              output_dir=build_dir)
    if bin_path is None:
        missing = extract_missing_intrinsics(compile_error)
        if missing:
            log.error("  Missing intrinsics: %s", missing)
        return VerificationResult(
            kernel_name=kernel_name,
            verdict="MISSING_INTRINSIC" if missing else "COMPILE_ERROR",
            compile_error=compile_error[:3000],
            missing_intrinsics=missing,
        )
    log.info("  Compilation successful")

    # 3. Run
    log.info("Step 3/3: Bounded verification (batch from %d, %s, %ds budget)...",
             min_batch, f"to {max_batch}" if max_batch else "unbounded", time_budget)
    return run_verification(bin_path, kernel_name,
                             time_budget=time_budget,
                             max_batch=max_batch,
                             min_batch=min_batch,
                             vlen=vlen,
                             route=route)


def verify_rvv_pair(reference_path: str, candidate_path: str, *, batch: int,
                    vlen: int, **kwargs) -> VerificationResult:
    """Prove RVV output bits equal at one explicit workload element count/VLEN.

    Both files must expose test_rvv. Unsupported output/shape models fail closed.
    A timeout or partial result is never sufficient for optimized acceptance.
    """
    if batch <= 0 or vlen <= 0 or vlen % 8:
        raise ValueError("RVV verification requires batch > 0 and positive byte-aligned VLEN")
    return verify_kernel(reference_path, candidate_path, reference_isa="rvv",
                         min_batch=batch, max_batch=batch, vlen=vlen, **kwargs)


# ---------------------------------------------------------------------------
# Parallel sweep — embarrassingly parallel across kernels (§9c.F)
# ---------------------------------------------------------------------------
def _verify_one_spec(spec: dict):
    """Pool worker: verify one kernel in its OWN build dir so concurrent compiles
    don't clobber a shared CMake cache.  `spec` is verify_kernel kwargs."""
    name = spec["kernel_name"]
    bd = PROJECT_ROOT / "build" / "slots" / name
    return name, verify_kernel(build_dir=bd, **spec)


def verify_kernels_parallel(specs: list, max_workers: int = None) -> dict:
    """Verify many kernels concurrently (one process each, isolated build dirs).

    `specs`: list of verify_kernel kwargs dicts (each must include kernel_name,
    neon_path, rvv_path).  Returns {kernel_name: VerificationResult}.  Each kernel's
    solver query uses ~1 core, so the natural cap is the core count.
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    if max_workers is None:
        max_workers = max(1, min(8, (os.cpu_count() or 4) - 1))
    log.info("Parallel verification: %d kernels across %d workers", len(specs), max_workers)
    results = {}
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_verify_one_spec, s): s.get("kernel_name", "?") for s in specs}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                n, res = fut.result()
                results[n] = res
                nver = len([b for b in res.verified_batches if b.status == "VERIFIED"])
                log.info("  [done] %-18s %-14s verified=%d", n, res.verdict, nver)
            except Exception as e:
                log.error("  [fail] %s: %s", name, e)
                results[name] = VerificationResult(kernel_name=name, verdict=f"EXC:{type(e).__name__}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

    p = argparse.ArgumentParser(description="SALTy-RN Bounded Verification")
    reference = p.add_mutually_exclusive_group(required=True)
    reference.add_argument("--neon", help="Path to NEON kernel source")
    reference.add_argument("--reference-rvv", help="Verified RVV baseline (requires --batch)")
    p.add_argument("--rvv", required=True, help="Path to RVV kernel source")
    p.add_argument("--params-init", default="", help="C++ params initialization code")
    p.add_argument("--params-file", default="", help="File containing params init code")
    p.add_argument("--vlen", type=int, default=256, help="Target VLEN in bits")
    p.add_argument("--timeout", type=int, default=600,
                   help="TOTAL wall-clock time budget in seconds for the whole batch sweep "
                        "(default: 600 = 10 min). The sweep keeps increasing the batch until this "
                        "is spent; each query gets whatever time is left. 0 = no budget (then set --max-batch).")
    p.add_argument("--max-batch", type=int, default=0,
                   help="Cap the batch sweep at this size. 0 (default) = UNBOUNDED — keep increasing "
                        "the batch until the --timeout budget runs out.")
    p.add_argument("--batch", type=int, default=0,
                   help="Run ONLY this batch size (shortcut for --min-batch=N --max-batch=N). 0 = sweep.")
    p.add_argument("--symbolic-params", action="store_true",
                   help="Use symbolic params (proves for ALL valid params)")
    p.add_argument("--backend", choices=sorted(VERIFICATION_DIRS.keys()) + ["auto"],
                   default="auto",
                   help="SMT backend. auto (default) = portfolio: build cvc5 harness, "
                        "route each query pure-BV→bitwuzla / FP→cvc5 with on-timeout "
                        "fallback (degrades to cvc5 if bitwuzla absent). "
                        "cvc5 = cvc5-only | bitwuzla = legacy tree.")
    p.add_argument("--input-range", default="",
                   help="Constrain F32 inputs to a finite band 'LO,HI' (e.g. -1,1) — "
                        "needed for FP-multiply families; tags the verdict config:finite. "
                        "Use '=' to avoid argparse eating a leading '-': --input-range=-1,1")
    args = p.parse_args()

    if args.reference_rvv and args.batch <= 0:
        p.error("--reference-rvv requires a positive --batch workload element count")
    if args.reference_rvv and (args.vlen <= 0 or args.vlen % 8 or args.timeout < 0):
        p.error("RVV verification requires positive byte-aligned VLEN and nonnegative timeout")

    params_init = args.params_init
    if args.params_file:
        params_init = Path(args.params_file).read_text()

    input_range = None
    if args.input_range:
        lo, hi = args.input_range.split(",")
        input_range = (float(lo), float(hi))

    min_batch = args.batch if args.batch > 0 else 1
    max_batch = args.batch if args.batch > 0 else args.max_batch
    result = verify_kernel(
        args.reference_rvv or args.neon, args.rvv,
        reference_isa="rvv" if args.reference_rvv else "neon",
        params_init=params_init,
        symbolic_params=args.symbolic_params,
        vlen=args.vlen,
        time_budget=args.timeout,
        max_batch=max_batch,
        min_batch=min_batch,
        backend=args.backend,
        input_range=input_range,
    )

    print(result.to_json())
    if args.reference_rvv and (result.verdict != "ALL_PASSED" or
                               result.max_verified_batch != args.batch):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
