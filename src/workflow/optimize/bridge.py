"""Bridge SALTy's verified RVV kernels into autocomp for optimization.

Flow per kernel:
    1. Stage baseline:  kernels/target/<name>.c  →  third_party/autocomp/sols/salty-rvv/<id>_<name>.c
       (rename entry function to `test`)
    2. Run autocomp's beam search on prob_type="salty-rvv", prob_id=<id>.
    3. Pick the global best correct candidate from the run's output dir.
    4. Symbolically verify against the staged RVV baseline at the workload size.
    5. Only on a complete proof, write back to kernels/target_optimized/<name>.c (rename `test` → original symbol).

The autocomp harness at third_party/autocomp/harnesses/salty-rvv/test<id>.c is
maintained by the user; this bridge only checks that it exists.

CLI:
    python -m src.workflow.optimize.bridge --kernel f32-vclamp --prob-id 0
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # SALT/
AUTOCOMP_ROOT = PROJECT_ROOT / "third_party" / "autocomp"
SALTY_PROB = "salty-rvv"
SALTY_HARNESS_DIR = AUTOCOMP_ROOT / "harnesses" / SALTY_PROB
SALTY_SOL_DIR = AUTOCOMP_ROOT / "sols" / SALTY_PROB
AUTOCOMP_OUTPUT_ROOT = AUTOCOMP_ROOT / "output"

log = logging.getLogger("pipeline")


@dataclass
class OptimizeResult:
    success: bool
    optimized_path: Optional[Path] = None
    cycles: Optional[int] = None
    output_dir: Optional[Path] = None
    error: str = ""
    verification: Optional[dict] = None


# ---------------------------------------------------------------------------
# Function-name rename: kernel entry symbol ↔ "test"
# ---------------------------------------------------------------------------

def _entry_function_name(rvv_source: str) -> str:
    """Extract the entry function name — the unique `void <name>(` definition."""
    m = re.search(r'\bvoid\s+(test_rvv)\s*\(', rvv_source)
    if m is None:
        m = re.search(r'\bvoid\s+(\w+)\s*\(', rvv_source)
    if m is None:
        raise ValueError("Could not parse RVV function signature")
    return m.group(1)


def _rename_void_function(source: str, old: str, new: str) -> str:
    """Rename the unique `void <old>(` definition to `void <new>(`.

    Matches the `void <name>(` entry pattern only. Fails on ambiguity.
    """
    pattern = re.compile(r'(\bvoid\s+)' + re.escape(old) + r'(\s*\()')
    matches = pattern.findall(source)
    if not matches:
        raise ValueError(f"No 'void {old}(' definition found in source")
    if len(matches) > 1:
        raise ValueError(
            f"Found {len(matches)} 'void {old}(' occurrences; refusing to rename ambiguously")
    return pattern.sub(rf'\g<1>{new}\g<2>', source, count=1)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def _assert_harness_exists(prob_id: int) -> Path:
    p = SALTY_HARNESS_DIR / f"test{prob_id}.c"
    if not p.exists():
        raise FileNotFoundError(
            f"Autocomp harness not found at {p}. "
            f"Author it (saturn-rvv style) before running --optimize.")
    return p


def _stage_baseline(kernel_name: str, prob_id: int, target: Path = None) -> tuple[Path, str]:
    """Read kernels/target/<name>.c, rename entry to `test`, write to sols/.

    Returns (staged_file_path, original_entry_symbol).
    """
    target = target or PROJECT_ROOT / "kernels" / "target" / f"{kernel_name}.c"
    if not target.exists():
        raise FileNotFoundError(f"No verified RVV kernel at {target}")

    source = target.read_text()
    orig_name = _entry_function_name(source)
    renamed = source if orig_name == "test" else _rename_void_function(source, orig_name, "test")

    SALTY_SOL_DIR.mkdir(parents=True, exist_ok=True)
    out = SALTY_SOL_DIR / f"{prob_id}_{kernel_name}.c"
    out.write_text(renamed)
    log.info("Staged baseline: %s → %s (renamed %s → test)", target.name, out, orig_name)
    return out, orig_name


def _run_autocomp(prob_id: int, cfg) -> Path:
    """Programmatic mirror of run_search.main() for prob_type=salty-rvv.

    Returns absolute path to the run's output directory.
    """
    _assert_harness_exists(prob_id)

    # Make autocomp importable without requiring pip install
    if str(AUTOCOMP_ROOT) not in sys.path:
        sys.path.insert(0, str(AUTOCOMP_ROOT))

    import random
    from autocomp.search.search import (
        BeamSearchStrategy, create_backend_and_agents, load_initial_code,
    )
    from autocomp.search.prob import Prob
    from autocomp.hw_config import SaturnHardwareConfig
    import autocomp.common.my_logging as my_logging

    random.seed(1111)  # match run_search.main() determinism

    AUTOCOMP_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output_dir = AUTOCOMP_OUTPUT_ROOT / f"{SALTY_PROB}_{prob_id}_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)

    my_logging.move_log(output_dir, tag="search")
    log.info("Autocomp output dir: %s", output_dir)

    hw_config = SaturnHardwareConfig(vlen=cfg.autocomp_vlen, dlen=cfg.autocomp_dlen)
    prob = Prob(SALTY_PROB, prob_id)
    initial_code = load_initial_code("saturn", prob)

    eval_backend, agent, code_agent = create_backend_and_agents(
        backend_name="saturn",
        agent_name="built:saturn-rvv",
        hw_config=hw_config,
        prob=prob,
        models=cfg.autocomp_models,
        code_models=None,
        menu_strategy="one-shot",
        fine_grained_isa=True,
        example_rate=0.25,
        cache_dir=output_dir,
    )

    optimizer = BeamSearchStrategy(
        output_dir=output_dir,
        eval_backend=eval_backend,
        agent=agent,
        orig_code=initial_code,
        prob=prob,
        metric="latency",
        simulator=None,
        give_score_feedback=1,
        give_util_feedback=0,
        give_hw_feedback=0,
        include_ancestors=False,
        plan_icl_examples=False,
        code_icl_examples=False,
        dropout_menu_options=0.25,
        prevent_duplicate_level=0,
        translate_iters=0,
        translate_perf_threshold=15,
        translate_drop_original=True,
        translate_score=True,
        code_agent=code_agent,
        early_stop_iters=0,
        early_stop_threshold=1.0,
        continue_from="",
        use_edits=False,
        num_analyses=0,
        num_plan_candidates=cfg.autocomp_num_plan_candidates,
        num_code_candidates=cfg.autocomp_num_code_candidates,
        beam_size=cfg.autocomp_beam_size,
        num_pairs_to_combine=0,
        num_gen_per_combine=0,
        trigger_exhaustive_threshold=1,
        trigger_exhaustive_iters=20,
        start_exhaustive_iters=0,
        reimplement_failed=False,
        skip_planning=False,
    )

    log.info("Beam search: iters=%d beam=%d plan=%d code=%d models=%s",
             cfg.autocomp_iterations, cfg.autocomp_beam_size,
             cfg.autocomp_num_plan_candidates, cfg.autocomp_num_code_candidates,
             cfg.autocomp_models)
    optimizer.optimize(cfg.autocomp_iterations)
    return output_dir


def _pick_best(output_dir: Path) -> tuple[str, Optional[int]]:
    """Return (code_str, cycles) for the best correct candidate.

    Code: read autocomp's auto-saved best_candidate_so_far.c.
    Cycles: walk eval-results-iter-*/code_*_result.txt and take the lowest
    `latency` among `correct: true` entries.
    """
    best_path = output_dir / "best_candidate_so_far.c"
    if not best_path.exists():
        raise RuntimeError(
            f"Autocomp produced no best candidate at {best_path}. "
            f"Run logs are in {output_dir}.")
    code = best_path.read_text()

    best_cycles: Optional[int] = None
    for result_file in output_dir.glob("eval-results-iter-*/code_*_result.txt"):
        try:
            stats = json.loads(result_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not stats.get("correct"):
            continue
        latency = stats.get("latency")
        if latency is None:
            continue
        if best_cycles is None or latency < best_cycles:
            best_cycles = int(latency)

    return code, best_cycles


def _write_optimized(kernel_name: str, code: str, orig_symbol: str, kernels_dir: Path = None) -> Path:
    """Rename `test` → original symbol; write kernels/target_optimized/<name>.c."""
    renamed = code if orig_symbol == "test" else _rename_void_function(code, "test", orig_symbol)
    out_dir = (kernels_dir or PROJECT_ROOT / "kernels") / "target_optimized"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{kernel_name}.c"
    out.write_text(renamed)
    log.info("Wrote optimized kernel: %s (renamed test → %s)", out, orig_symbol)
    return out


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def optimize_kernel(kernel_name: str, prob_id: int, cfg) -> OptimizeResult:
    """Stage → search → verify RVV/RVV → publish only a proven candidate."""
    log.info("═══════════════════════════════════════════════════════════")
    log.info("Optimization: %s (prob_id=%d)", kernel_name, prob_id)

    output_dir = None
    try:
        batch = cfg.verification_batch
        if batch <= 0:
            raise ValueError("Post-AutoComp verification requires --verify-batch matching "
                             "the benchmark workload (element count)")
        if cfg.autocomp_vlen <= 0 or cfg.autocomp_vlen % 8:
            raise ValueError("AutoComp VLEN must be positive and byte-aligned")
        if cfg.verification_timeout < 0:
            raise ValueError("Verification timeout must be nonnegative")
        suffix = "" if cfg.vlen == 256 else f"-{cfg.vlen}"
        target = cfg.target_dir / f"{kernel_name}{suffix}.c"
        staged, orig_symbol = _stage_baseline(kernel_name, prob_id, target)
        # Snapshot the exact baseline used by the search; subsequent verification
        # must not accidentally read a changed target file.
        baseline_code = _rename_void_function(staged.read_text(), "test", "test_rvv")
        output_dir = _run_autocomp(prob_id, cfg)
        code, cycles = _pick_best(output_dir)
        reference = output_dir / "verification_reference.c"
        candidate = output_dir / "verification_candidate.c"
        reference.write_text(baseline_code)
        candidate.write_text(_rename_void_function(code, "test", "test_rvv"))
        from ..verification.orchestrator import verify_rvv_pair
        result = verify_rvv_pair(
            str(reference), str(candidate), kernel_name=kernel_name,
            batch=batch, vlen=cfg.autocomp_vlen,
            time_budget=cfg.verification_timeout,
            symbolic_params=cfg.verification_symbolic_params,
            input_range=cfg.verification_input_range,
            backend=cfg.verification_backend,
            build_dir=output_dir / "verification_build",
        )
        report = json.loads(result.to_json())
        report.update(reference_isa="rvv", candidate_isa="rvv", batch=batch,
                      vlen=cfg.autocomp_vlen, comparison="output-bits",
                      reference=str(reference), candidate=str(candidate),
                      symbolic_params=cfg.verification_symbolic_params,
                      input_range=cfg.verification_input_range)
        (output_dir / "verification.json").write_text(json.dumps(report, indent=2))
        if result.verdict != "ALL_PASSED" or result.max_verified_batch != batch:
            return OptimizeResult(False, output_dir=output_dir, verification=report,
                                  error=f"RVV-to-RVV verification: {result.verdict}")
        optimized_path = _write_optimized(kernel_name + suffix, code, orig_symbol,
                                          cfg.kernels_dir)
        log.info("Optimization verified: %s (cycles=%s)", optimized_path, cycles)
        return OptimizeResult(True, optimized_path=optimized_path, cycles=cycles,
                              output_dir=output_dir, verification=report)
    except Exception as e:
        log.exception("Optimization failed for %s", kernel_name)
        return OptimizeResult(success=False, output_dir=output_dir, error=str(e))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_cli_config(args: argparse.Namespace):
    """Return a Config-shaped object with autocomp_* fields set from CLI."""
    from ..config import Config
    cfg = Config()
    cfg.verification_batch = args.verify_batch
    cfg.verification_timeout = args.verification_timeout
    cfg.vlen = args.baseline_vlen
    cfg.autocomp_iterations = args.iterations
    cfg.autocomp_beam_size = args.beam_size
    cfg.autocomp_num_plan_candidates = args.plan_candidates
    cfg.autocomp_num_code_candidates = args.code_candidates
    cfg.autocomp_vlen = args.vlen
    cfg.autocomp_dlen = args.dlen
    if args.model:
        cfg.autocomp_models = list(args.model)
    return cfg


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    p = argparse.ArgumentParser(description="SALTy → autocomp bridge")
    p.add_argument("--kernel", required=True,
                   help="Kernel name (matches kernels/target/<name>.c)")
    p.add_argument("--prob-id", type=int, required=True,
                   help="Autocomp prob_id (matches harnesses/salty-rvv/test<id>.c)")
    p.add_argument("--verify-batch", type=int, required=True,
                   help="Optimization workload element count for the symbolic proof")
    p.add_argument("--verification-timeout", type=int, default=600)
    p.add_argument("--baseline-vlen", type=int, default=256)
    p.add_argument("--iterations", type=int, default=8)
    p.add_argument("--beam-size", type=int, default=4)
    p.add_argument("--plan-candidates", type=int, default=4)
    p.add_argument("--code-candidates", type=int, default=2)
    p.add_argument("--vlen", type=int, default=512)
    p.add_argument("--dlen", type=int, default=256)
    p.add_argument("--model", action="append", default=None,
                   help="Provider::model (repeatable). Defaults to Config.autocomp_models.")
    args = p.parse_args()

    cfg = _build_cli_config(args)
    result = optimize_kernel(args.kernel, args.prob_id, cfg)
    if not result.success:
        log.error("Optimization failed: %s", result.error)
        sys.exit(1)
    log.info("Optimized kernel: %s (cycles=%s)", result.optimized_path, result.cycles)


if __name__ == "__main__":
    main()
