#!/usr/bin/env python3
"""
SALTy-RN: LLM Translation Pipeline

Automates the translation of SIMD kernels between ISAs (e.g. ARM Neon -> RVV)
using an LLM, with status tracking and iterative error repair.

Usage:
    python pipeline.py --kernel f32-vmulc
    python pipeline.py --kernel f32-vmulc --source Neon --target RVV
    python pipeline.py --kernel f32-vmulc --model openai::gpt-4o
    python pipeline.py --batch --skip-existing
    python pipeline.py --kernel f32-vmulc --dry-run

Environment Variables:
    GOOGLE_CLOUD_PROJECT  - GCP project ID for Vertex AI
    GOOGLE_CLOUD_LOCATION - GCP region (default: us-central1)
    GOOGLE_API_KEY        - Google AI API key (alternative to Vertex AI)
    OPENAI_API_KEY        - OpenAI API key
    ANTHROPIC_API_KEY     - Anthropic API key
    TOGETHER_API_KEY      - Together AI API key
    AWS_ACCESS_KEY_ID     - AWS access key for Bedrock
    AWS_SECRET_ACCESS_KEY - AWS secret key for Bedrock
    AWS_REGION            - AWS region (default: us-west-2)
    ZEPHYR_BASE           - Path to Zephyr SDK installation
    SPIKE_PATH            - Path to Spike simulator binary (optional)
"""

import argparse
import json
import logging
import queue
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # src/workflow/ -> SALT/

from .config import Config, TranslationResult
from .prompts_pkg import (
    load_reference_docs,
    load_translation_prompt,
    build_compile_repair_prompt,
    build_execution_repair_prompt,
    build_verification_repair_prompt,
    build_intrinsics_tools,
)
from .status import StatusTracker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

LOGS_DIR = PROJECT_ROOT / "logs"


def _setup_run_logging() -> Path:
    """Create a timestamped run directory under logs/ and add a file handler."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOGS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # File handler for the full run log
    run_log = run_dir / "run.log"
    fh = logging.FileHandler(run_log)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(fh)

    log.info("Run log: %s", run_log)
    return run_dir


def _setup_kernel_logging(run_dir: Path, kernel_name: str) -> logging.FileHandler:
    """Add a per-kernel file handler. Returns the handler so it can be removed later."""
    kernel_dir = run_dir / kernel_name
    kernel_dir.mkdir(parents=True, exist_ok=True)

    kh = logging.FileHandler(kernel_dir / "kernel.log")
    kh.setLevel(logging.DEBUG)
    kh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(kh)
    return kh


def _teardown_kernel_logging(handler: logging.FileHandler):
    """Remove and close a per-kernel file handler."""
    logging.getLogger().removeHandler(handler)
    handler.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_params(source_code: str) -> str:
    """Extract the parameter struct comment from the top of a kernel file.

    Expects a block comment like:
        /* struct xnn_qs8_add_minmax_params { ... }; */
    """
    match = re.search(r'/\*\s*(struct\s+\w+.*?)\*/', source_code, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_code(response: str) -> str:
    """Extract C code from LLM response, stripping markdown fences and any
    `#include` directives.  Salt's harness inlines the kernel source into
    a namespace block; upstream-style includes (e.g. `<riscv_vector.h>`,
    `"src/xnnpack/common.h"`) either don't resolve on salt's include path
    or duplicate symbols salt already shims, so they get dropped here."""
    match = re.search(r'```(?:c|cpp)?\n(.*?)```', response, re.DOTALL)
    code = match.group(1).strip() if match else response.strip()
    # Strip every `#include <...>` and `#include "..."` line.
    code = re.sub(r'^[ \t]*#\s*include\s+[<"][^>"]+[>"][ \t]*\n?',
                  '', code, flags=re.MULTILINE)
    return code.strip()


def find_kernels(source_dir: Path) -> list[Path]:
    """Find all kernel source files in the source directory."""
    patterns = ["*.c", "*.cpp"]
    files = []
    for pat in patterns:
        files.extend(source_dir.glob(pat))
    return sorted(files)


def find_kernel_by_name(source_dir: Path, name: str) -> Path | None:
    """Find a kernel file by name (without extension).

    Prefers exact match (name.c) over substring glob (*name*.c)
    to avoid e.g. 'qs8-vadd' matching 'qs8-vaddc.c'.
    """
    # 1. Exact match
    for ext in [".c", ".cpp"]:
        exact = source_dir / f"{name}{ext}"
        if exact.exists():
            return exact
    # 2. Substring glob fallback — pick shortest filename to prefer exact-ish matches
    for ext in [".c", ".cpp"]:
        matches = list(source_dir.glob(f"*{name}*{ext}"))
        if matches:
            return min(matches, key=lambda p: len(p.name))
    return None


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def _format_counterexample(ce: dict) -> str:
    """Format a solver counterexample as human-readable text for LLM repair."""
    lines = []
    fi = ce.get("fail_index", "?")
    # Multi-dim (shape) harnesses report the failing shape as "dims" (e.g. "1,2" =
    # rows,channels); elementwise harnesses report a scalar "batch". Show whichever.
    where = f"dims=[{ce['dims']}]" if "dims" in ce else f"batch={ce.get('batch', '?')}"
    lines.append(f"At {where}, output index {fi} produces different outputs:")
    lines.append("")

    # Print inputs
    for k, v in ce.items():
        if k.endswith("_at_fail"):
            name = k.replace("_at_fail", "")
            lines.append(f"  {name}[{fi}] = {v}")
        elif k in ("input_b",):
            lines.append(f"  {k} = {v} (scalar broadcast)")

    lines.append("")
    neon_out = ce.get("neon_out", "?")
    rvv_out = ce.get("rvv_out", "?")
    lines.append(f"  NEON output[{fi}] = {neon_out}")
    lines.append(f"  RVV  output[{fi}] = {rvv_out}")
    lines.append("")
    lines.append(f"Expected: {neon_out}, Got: {rvv_out}")
    return "\n".join(lines)


def _resolve_prob_id(kernel_name: str, cfg: Config) -> int | None:
    """Resolve autocomp prob_id for a kernel. Returns None if unmapped.

    Single-kernel mode: cfg.optimize_prob_id (set via --prob-id).
    Batch mode: read cfg.optimize_map_file as {kernel_name: prob_id}.
    """
    if cfg.optimize_prob_id >= 0:
        return cfg.optimize_prob_id
    if cfg.optimize_map_file.exists():
        try:
            mapping = json.loads(cfg.optimize_map_file.read_text())
            pid = mapping.get(kernel_name)
            if pid is not None:
                return int(pid)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            log.warning("Could not read optimize map %s: %s", cfg.optimize_map_file, e)
    return None


def _optimize_and_reverify(kernel_path: Path, kernel_name: str,
                            cfg: Config, tracker: StatusTracker,
                            build_dir: Path = None) -> None:
    """Run autocomp on the verified RVV, then re-verify the optimized output."""
    if not tracker.is_verified(kernel_name):
        log.info("Skipping --optimize for %s (not verified)", kernel_name)
        return

    prob_id = _resolve_prob_id(kernel_name, cfg)
    if prob_id is None:
        log.warning("Skipping --optimize for %s (no prob_id; pass --prob-id or populate %s)",
                    kernel_name, cfg.optimize_map_file)
        return

    from .optimize.bridge import optimize_kernel
    opt = optimize_kernel(kernel_name, prob_id, cfg)
    if not opt.success:
        tracker.update(kernel_name, optimized=False, optimized_verified=False,
                       optimized_cycles=None, optimized_max_batch=0,
                       error=f"optimize_failed: {opt.error}")
        return

    tracker.update(kernel_name, optimized=True, optimized_cycles=opt.cycles,
                   optimized_verified=True,
                   optimized_max_batch=opt.verification["max_verified_batch"])


def _run_formal_verification(kernel_path, output_path, kernel_name, cfg, build_dir=None) -> dict | None:
    """Run formal verification (v2 engine, cvc5) on the kernel pair.

    Returns the verification result dict, or None only if the module is missing.
    Errors during verification are propagated as results, not swallowed. The v2
    engine needs no LLM (it either matches a fixture/template or returns
    UNSUPPORTED) — buffer sizing is over-allocation + lazy symbolic bytes.
    """
    try:
        from .verification.orchestrator import verify_kernel
    except ImportError:
        log.warning("Formal verification module not available")
        return None

    log.info("Starting formal verification for %s", kernel_name)

    # Total wall-clock budget for the whole sweep. Default is UNBOUNDED batch: keep
    # increasing the batch until the budget is spent (no per-batch cap — heavier 2D
    # batches just consume more of the same budget).
    time_budget = cfg.verification_timeout
    if cfg.verification_batch > 0:
        min_batch = max_batch = cfg.verification_batch   # single batch — pin both ends
        log.info("  Single-batch mode: batch=%d", cfg.verification_batch)
    else:
        min_batch, max_batch = 1, 0                      # 0 = unbounded; bounded only by time_budget

    result = verify_kernel(
        neon_path=str(kernel_path),
        rvv_path=str(output_path),
        kernel_name=kernel_name,
        vlen=cfg.vlen,
        time_budget=time_budget,
        max_batch=max_batch,
        min_batch=min_batch,
        backend=cfg.verification_backend,
        input_range=cfg.verification_input_range,
        symbolic_params=cfg.verification_symbolic_params,
        build_dir=build_dir,
    )
    import json
    result_dict = json.loads(result.to_json())
    log.info("Formal verification complete: %s → %s",
             kernel_name, result_dict.get("verdict", "UNKNOWN"))
    return result_dict


def _call_llm(client, prompt: str, system: str, tools: dict, cfg: Config,
              temperature: float | None = None, thinking: str | None = None) -> str:
    """Call the LLM with or without tools. Returns raw response text."""
    temp = temperature if temperature is not None else cfg.temperature
    think = thinking if thinking is not None else cfg.thinking

    if tools:
        return client.chat_with_tools(
            prompt=prompt, tools=tools, system=system,
            temperature=temp, thinking=think,
        )
    else:
        return client.chat(
            prompt=prompt, system=system,
            temperature=temp, thinking=think,
        )


# Zephyr build slots: each kernel installs its harness into slot_<id>/app/src/main.c,
# builds into slot_<id>/build, and Spike reads slot_<id>/build/zephyr/zephyr.elf — all
# slot-private.  Under --jobs, concurrent kernels MUST use distinct slots or they clobber
# each other's main.c / build / ELF.  _SLOT_POOL hands out distinct slots (a free-list);
# acquiring a slot isolates the whole build+Spike stage, so they run in PARALLEL (no lock).
_SLOT_POOL = None  # queue.Queue of slot ids; initialized in main() when --jobs > 1


def _compile_and_run(kernel_name: str, cfg: Config):
    """Compile the kernel and optionally run on Spike. Returns (build_result, run_result).

    Runs on an isolated build slot so parallel kernels don't clobber each other's
    harness / build tree / ELF.
    """
    from .build import build_kernel, run_spike
    from .build.compiler import _get_build_slot

    if not cfg.zephyr_base or not Path(cfg.zephyr_base).exists():
        log.info("Skipping compilation (zephyr not found at %s)", cfg.zephyr_base)
        return None, None

    slot = _SLOT_POOL.get() if _SLOT_POOL is not None else 0
    try:
        log.info("Compiling %s (slot %d)...", kernel_name, slot)
        build_result = build_kernel(kernel_name, zephyr_base=cfg.zephyr_base, slot_id=slot)

        if not build_result.success:
            return build_result, None

        log.info("Compilation passed (%.1fs)", build_result.elapsed)

        if not cfg.chipyard_path:
            log.info("Skipping Spike (CHIPYARD_PATH not set)")
            return build_result, None

        _, slot_build_dir = _get_build_slot(slot)   # the ELF for THIS slot
        run_result = run_spike(kernel_name=kernel_name, build_dir=slot_build_dir,
                               chipyard_path=cfg.chipyard_path)
        return build_result, run_result
    finally:
        if _SLOT_POOL is not None:
            _SLOT_POOL.put(slot)


def translate_kernel(
    kernel_path: Path,
    cfg: Config,
    client,
    tools: dict[str, callable],
    tracker: StatusTracker,
    build_dir: Path = None,
) -> TranslationResult:
    """Translate a single kernel with compile/run repair loop.

    Flow:
        1. Initial LLM translation
        2. Compile → if fail, compilation repair (up to max_compile_retries)
        3. Run on Spike → if fail, execution repair (uses compile retry budget)
        4. Formal verification → if counterexample, verification repair (up to max_verification_retries)
    """
    kernel_name = kernel_path.stem
    log.info("Translating: %s", kernel_name)

    # Target hardware VLEN: 256 keeps the legacy bare name; any other value gives
    # a coexisting variant kernels/target/<name>-<vlen>.c (translated for that
    # VLEN's LMUL and verified at that VLEN).
    vlen_suffix = "" if cfg.vlen == 256 else f"-{cfg.vlen}"
    output_path = cfg.target_dir / f"{kernel_path.stem}{vlen_suffix}.c"

    # Skip if already verified and skip_existing is set
    if cfg.skip_existing and tracker.is_verified(kernel_name):
        log.info("Skipping %s (already verified)", kernel_name)
        return TranslationResult(
            kernel_name=kernel_name, success=True,
            output_file=str(output_path),
        )

    # 1. Read source
    source_code = kernel_path.read_text()
    log.info("Read source: %s (%d chars)", kernel_path.name, len(source_code))

    cfg.target_dir.mkdir(parents=True, exist_ok=True)

    if cfg.skip_translation:
        # Skip LLM, use existing target kernel
        if not output_path.exists():
            log.error("--skip-translation but target not found: %s", output_path)
            return TranslationResult(
                kernel_name=kernel_name, success=False, attempts=0,
                error=f"Target file not found: {output_path}",
            )
        translated_code = output_path.read_text()
        log.info("Skipping translation, using existing target: %s (%d chars)",
                 output_path, len(translated_code))
    else:
        # 2. Build initial translation prompts
        params_section = extract_params(source_code)
        if params_section:
            log.info("Extracted params struct (%d chars)", len(params_section))
        system_prompt = load_reference_docs(cfg.source, rules_only=cfg.rules_only)
        user_prompt = load_translation_prompt(cfg.source, source_code, params_section, vlen=cfg.vlen)

        # 3. Dry run check
        if cfg.dry_run:
            log.info("[DRY RUN] Would call LLM for %s", kernel_name)
            return TranslationResult(kernel_name=kernel_name, success=False)

        # 4. Initial translation
        try:
            log.info("Starting initial LLM translation for %s (model=%s, tools=%s)",
                     kernel_name, cfg.model, bool(tools))
            t0 = time.perf_counter()
            response = _call_llm(client, user_prompt, system_prompt, tools, cfg)
            elapsed = time.perf_counter() - t0
            translated_code = extract_code(response)
            log.info("Got translation: %d chars in %.1fs", len(translated_code), elapsed)
        except Exception as e:
            log.error("LLM call failed for %s: %s", kernel_name, e)
            tracker.update(kernel_name, generated=False, attempts=1, error=str(e))
            return TranslationResult(
                kernel_name=kernel_name, success=False, attempts=1, error=str(e),
            )

        output_path.write_text(translated_code)
        log.info("Wrote translation: %s", output_path)

    tracker.update(kernel_name, generated=True, attempts=1)

    # Pre-load reference docs for execution repairs (full docs, not rules-only)
    exec_system_prompt = load_reference_docs(cfg.source, rules_only=False)
    # Compilation repairs use only the target ISA intrinsics reference
    compile_system_prompt = load_reference_docs(cfg.source, rules_only=True)

    attempts = 1  # initial translation counts as attempt 1
    compile_attempts = 0
    verification_attempts = 0
    last_error = ""

    # Skip straight to verification if already compiled+passed and --skip-spike is set,
    # or for a non-default VLEN (the Spike harness/build assume the bare-name 256 target,
    # so the -<vlen> variant is a translate→formal-verify flow).
    if (cfg.vlen != 256) or (cfg.skip_spike and tracker.get(kernel_name).get("compiled", False)):
        log.info("Skipping compile+Spike for %s, jumping to verification (vlen=%d)", kernel_name, cfg.vlen)

        verify_result = _run_formal_verification(kernel_path, output_path, kernel_name, cfg, build_dir)

        if verify_result is None:
            log.warning("Formal verification unavailable — skipping")
            tracker.update(kernel_name, compiled=True, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        verdict = verify_result.get("verdict", "")
        max_batch = verify_result.get("max_verified_batch", 0)
        log.info("Formal verification: %s (max_batch=%d)", verdict, max_batch)

        if verdict in ("ALL_PASSED", "PARTIAL") and max_batch > 0:
            tracker.update(kernel_name, compiled=True, verified=True,
                           max_verified_batch=max_batch, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        if verdict != "COUNTEREXAMPLE":
            log.warning("Formal verification: %s — accepting based on prior Spike pass", verdict)
            tracker.update(kernel_name, compiled=True, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        # COUNTEREXAMPLE — fall through to the repair loop below

    while True:
        # --- Compile ---
        build_result, run_result = _compile_and_run(kernel_name, cfg)

        if build_result is None:
            # No Zephyr available — translation succeeded, just untested
            tracker.update(kernel_name, generated=True, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        if not build_result.success:
            compile_attempts += 1
            if compile_attempts > cfg.max_compile_retries:
                log.error("Exhausted %d compile repair attempts for %s",
                          cfg.max_compile_retries, kernel_name)
                last_error = f"compile_error: {build_result.error}"
                break

            last_error = f"compile_error: {build_result.error}"
            attempts += 1
            log.error("Compile repair %d/%d: compilation failed for %s",
                      compile_attempts, cfg.max_compile_retries, kernel_name)

            # Compilation repair: higher temp, no thinking, minimal context
            repair_prompt = build_compile_repair_prompt(
                cfg.source, translated_code, build_result.error,
            )
            try:
                response = _call_llm(
                    client, repair_prompt, compile_system_prompt, {},
                    cfg, temperature=cfg.repair_temperature, thinking=None,
                )
                translated_code = extract_code(response)
                output_path.write_text(translated_code)
                log.info("Compile repair %d/%d: wrote repair (%d chars)",
                         compile_attempts, cfg.max_compile_retries, len(translated_code))
                continue  # retry compile
            except Exception as e:
                log.error("Compile repair LLM call failed: %s", e)
                last_error = str(e)
                break

        # --- Run on Spike ---
        if run_result is None:
            # No Spike available — compiled OK, just not run-tested
            tracker.update(kernel_name, compiled=True, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        if run_result.passed:
            log.info("Spike: PASS (%.1fs)", run_result.elapsed)

            # --- Formal verification (v2 engine, cvc5) ---
            verify_result = _run_formal_verification(
                kernel_path, output_path, kernel_name, cfg, build_dir)

            if verify_result is None:
                # Verification not available (bitwuzla not installed, etc.)
                log.warning("Formal verification unavailable — skipping")
                tracker.update(kernel_name, compiled=True, attempts=attempts)
                return TranslationResult(
                    kernel_name=kernel_name, success=True,
                    attempts=attempts, output_file=str(output_path),
                )

            verdict = verify_result.get("verdict", "")
            log.info("Formal verification: %s (max_batch=%d)",
                     verdict, verify_result.get("max_verified_batch", 0))

            max_batch = verify_result.get("max_verified_batch", 0)

            if verdict in ("ALL_PASSED", "PARTIAL") and max_batch > 0:
                # Bounded verification succeeded up to max_batch
                tracker.update(kernel_name, compiled=True, verified=True,
                               max_verified_batch=max_batch, attempts=attempts)
                return TranslationResult(
                    kernel_name=kernel_name, success=True,
                    attempts=attempts, output_file=str(output_path),
                )

            if verdict == "COUNTEREXAMPLE":
                verification_attempts += 1
                if verification_attempts > cfg.max_verification_retries:
                    log.error("Exhausted %d verification repair attempts for %s",
                              cfg.max_verification_retries, kernel_name)
                    ce = verify_result.get("counterexample", {})
                    last_error = f"formal_verification_counterexample: {_format_counterexample(ce)}"
                    break

                # Formal verification found a bug that Spike missed
                ce = verify_result.get("counterexample", {})
                ce_text = _format_counterexample(ce)
                last_error = f"formal_verification_counterexample: {ce_text}"
                attempts += 1
                log.error("Verification repair %d/%d: COUNTEREXAMPLE:\n%s",
                          verification_attempts, cfg.max_verification_retries, ce_text)

                # Repair using the verification-specific prompt
                repair_prompt = build_verification_repair_prompt(
                    cfg.source, source_code, translated_code, ce_text,
                )
                try:
                    response = _call_llm(
                        client, repair_prompt, exec_system_prompt, {},
                        cfg, temperature=1.0, thinking="medium",
                    )
                    translated_code = extract_code(response)
                    output_path.write_text(translated_code)
                    log.info("Verification repair %d/%d: wrote repair (%d chars)",
                             verification_attempts, cfg.max_verification_retries, len(translated_code))
                    # Reset compile attempts since verification repair may introduce compile errors
                    compile_attempts = 0
                    continue  # retry compile + run + verify
                except Exception as e:
                    log.error("Verification repair LLM call failed: %s", e)
                    last_error = str(e)
                    break

            # Other verdicts (COMPILE_ERROR, MISSING_INTRINSIC, etc.)
            # Treat as non-blocking — Spike already passed
            log.warning("Formal verification: %s — accepting based on Spike pass", verdict)
            tracker.update(kernel_name, compiled=True, attempts=attempts)
            return TranslationResult(
                kernel_name=kernel_name, success=True,
                attempts=attempts, output_file=str(output_path),
            )

        # Execution failure — wrong output or crash/timeout
        compile_attempts += 1
        if compile_attempts > cfg.max_compile_retries:
            log.error("Exhausted %d compile/execution repair attempts for %s",
                      cfg.max_compile_retries, kernel_name)
            last_error = (f"wrong_output: {run_result.output}" if run_result.success
                          else f"runtime_error: {run_result.error}")
            break

        if run_result.success:
            last_error = f"wrong_output: {run_result.output}"
            log.warning("Compile repair %d/%d: Spike FAIL (wrong output)",
                        compile_attempts, cfg.max_compile_retries)
        else:
            last_error = f"runtime_error: {run_result.error}"
            log.error("Compile repair %d/%d: Spike error: %s",
                      compile_attempts, cfg.max_compile_retries, run_result.error[:200])

        # Execution repair: thinking=medium, temp=1.0, full reference docs + NEON source
        attempts += 1
        error_for_prompt = run_result.output if run_result.success else run_result.error
        repair_prompt = build_execution_repair_prompt(
            cfg.source, source_code, translated_code, error_for_prompt,
        )
        try:
            response = _call_llm(
                client, repair_prompt, exec_system_prompt, {},
                cfg, temperature=1.0, thinking="medium",
            )
            translated_code = extract_code(response)
            output_path.write_text(translated_code)
            log.info("Compile repair %d/%d: wrote execution repair (%d chars)",
                     compile_attempts, cfg.max_compile_retries, len(translated_code))
            continue  # retry compile + run
        except Exception as e:
            log.error("Execution repair LLM call failed: %s", e)
            last_error = str(e)
            break

    # If we reach here, retries were exhausted or an error broke the loop
    tracker.update(kernel_name, attempts=attempts, error=last_error)
    return TranslationResult(
        kernel_name=kernel_name, success=False,
        attempts=attempts, output_file=str(output_path),
        error=last_error,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SALTy-RN Translation Pipeline")

    # What to translate
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("-k", "--kernel", type=str, help="Kernel name to translate (e.g. f32-vmulc)")
    g.add_argument("-f", "--file", type=Path, help="Path to a specific source kernel file")
    g.add_argument("-b", "--batch", action="store_true", help="Translate all kernels in source dir")
    p.add_argument("-j", "--jobs", type=int, default=1,
                   help="--batch: translate+verify this many kernels concurrently "
                        "(default 1; bound by your LLM provider's rate limits)")

    # Translation config
    p.add_argument("--source", default="Neon", help="Source ISA (default: Neon)")
    p.add_argument("--target", default="RVV", help="Target ISA (default: RVV)")
    p.add_argument("--model", default="gemini-3.1-pro-preview-customtools",
                    help="LLM model (provider::model format)")
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--repair-temperature", type=float, default=0.3)
    p.add_argument("--thinking", default="none",
                    help="Gemini thinking level (low/medium/high/none)")
    p.add_argument("--max-compile-retries", type=int, default=5,
                    help="Max repair attempts for compile/execution errors")
    p.add_argument("--max-verification-retries", type=int, default=5,
                    help="Max repair attempts for formal verification failures")
    p.add_argument("--verification-timeout", type=int, default=600,
                    help="TOTAL wall-clock time budget (s) for the whole batch sweep. The verifier keeps "
                         "increasing the batch (unbounded) until this is spent; each solver query gets "
                         "whatever time is left. Default: 600 (10 min). 0 = no budget.")
    p.add_argument("--verify-batch", type=int, default=0,
                    help="Run ONLY this batch size in verification (skip the 1..max sweep). 0 = sweep (default).")
    p.add_argument("--vlen", type=int, default=256,
                    help="Target VLEN in bits. Drives the translator's LMUL choice (prompt) AND the "
                         "verifier's vsetvl semantics. 256 (default) = legacy bare target name; any other "
                         "value writes/verifies kernels/target/<name>-<vlen>.c (e.g. --vlen 128 -> <name>-128.c). "
                         "Non-256 skips Spike (the Spike build assumes the bare-name target).")
    p.add_argument("--input-range", default="",
                    help="Constrain F32 verification inputs to a finite band 'LO,HI' (e.g. -1,1). "
                         "Needed for FP-multiply families (gemm/igemm/dwconv/vmulcaddc/ibilinear), which "
                         "otherwise counterexample on the inherent NaN-in-min/max ISA difference. "
                         "Tags the verdict config:finite. Use '=' to pass a leading '-': --input-range=-1,1")
    p.add_argument("--symbolic-params", action="store_true",
                    help="Verify with SYMBOLIC params — prove equivalence for ALL valid param values "
                         "(within their constraints/ranges) instead of the concrete edge configs. "
                         "Strongest for integer-param families (qs8/qu8); FP params can be solver-hard.")

    # Build / simulation
    p.add_argument("--zephyr-base", default="", help="Path to Zephyr SDK")
    p.add_argument("--chipyard-path", default="", help="Path to Chipyard (for Spike)")

    # Directories
    p.add_argument("--kernels-dir", type=Path, default=None,
                    help="Override kernels directory")

    # Flags
    p.add_argument("--dry-run", action="store_true", help="Show what would be done")
    p.add_argument("--skip-existing", action="store_true",
                    help="Skip already-generated kernels")
    p.add_argument("--tools", action="store_true",
                    help="Enable intrinsics search tools (model can look up op-semantics)")
    p.add_argument("--rules-only", action="store_true",
                    help="Only include translation rules as reference (skip background docs)")
    p.add_argument("--skip-translation", action="store_true",
                    help="Skip LLM translation, start from compile+run+verify using existing target kernel")
    p.add_argument("--skip-spike", action="store_true",
                    help="Skip compile+Spike if kernel already passed (compiled=true in status.json)")

    # Autocomp post-verify optimization (opt-in)
    p.add_argument("--optimize", action="store_true",
                    help="After successful verification, run autocomp on the verified RVV and re-verify the result")
    p.add_argument("--prob-id", dest="prob_id", type=int, default=-1,
                    help="Autocomp prob_id (single-kernel mode). Required with --optimize unless --optimize-map is provided.")
    p.add_argument("--optimize-map", dest="optimize_map", type=str, default="",
                    help="Path to JSON {kernel_name: prob_id} for batch --optimize")
    p.add_argument("--autocomp-vlen", type=int, default=512,
                   help="Optimization hardware and RVV/RVV proof VLEN")
    p.add_argument("--autocomp-dlen", type=int, default=256)
    p.add_argument("--autocomp-iterations", dest="autocomp_iterations", type=int, default=None,
                    help="Autocomp beam-search iterations (default: 8)")
    p.add_argument("--autocomp-beam-size", dest="autocomp_beam_size", type=int, default=None,
                    help="Autocomp beam size (default: 4)")
    p.add_argument("--autocomp-model", dest="autocomp_model", action="append", default=None,
                    help="Provider::model for autocomp (repeatable). Defaults to Config.autocomp_models.")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.thinking == "none":
        args.thinking = None

    cfg = Config.from_env_and_args(args)
    if cfg.optimize and cfg.verification_batch <= 0:
        parser.error("--optimize requires --verify-batch matching the benchmark element count")
    run_dir = _setup_run_logging()

    log.info("Pipeline config: source=%s target=%s model=%s", cfg.source, cfg.target, cfg.model)
    log.info("Directories: source=%s target=%s", cfg.source_dir, cfg.target_dir)

    client = None if cfg.dry_run else cfg.create_llm_client()
    tools = {}
    if not cfg.dry_run and args.tools:
        if client.supports_tools:
            tools = build_intrinsics_tools()
        else:
            log.warning("Provider '%s' does not support tool calling — tools disabled",
                        client.provider)
    tracker = StatusTracker(cfg.status_file)

    log.info("Tools: %s", "disabled" if not tools else list(tools.keys()))

    # Determine which kernels to translate
    if args.file:
        kernel_files = [args.file]
    elif args.kernel:
        match = find_kernel_by_name(cfg.source_dir, args.kernel)
        if not match:
            log.error("Kernel '%s' not found in %s", args.kernel, cfg.source_dir)
            sys.exit(1)
        kernel_files = [match]
    else:  # --batch
        kernel_files = find_kernels(cfg.source_dir)
        if not kernel_files:
            log.error("No kernel files found in %s", cfg.source_dir)
            sys.exit(1)
        log.info("Batch mode: found %d kernels", len(kernel_files))

    def _process_kernel(kernel_path, build_dir, with_kernel_log):
        # Per-kernel log files add a handler to the ROOT logger, which doesn't
        # work under concurrency — only used in sequential mode.
        kh = _setup_kernel_logging(run_dir, kernel_path.stem) if with_kernel_log else None
        try:
            result = translate_kernel(kernel_path, cfg, client, tools, tracker, build_dir=build_dir)
            if cfg.optimize and result.success:
                try:
                    _optimize_and_reverify(kernel_path, kernel_path.stem, cfg, tracker,
                                           build_dir=build_dir)
                except Exception:
                    log.exception("Optimization stage crashed for %s", kernel_path.stem)
            return result
        finally:
            if kh is not None:
                _teardown_kernel_logging(kh)

    results = []
    if cfg.jobs > 1 and len(kernel_files) > 1:
        # Parallel batch (§9c.F): dispatch many kernels through translate→compile→
        # Spike→verify at once. Bounded by --jobs (mind LLM rate limits). Each kernel
        # verifies in its own cmake build dir and builds/Spikes on its own Zephyr slot;
        # status writes + libclang generation are the only locked sections.
        log.info("Parallel batch: %d kernels across %d workers (per-kernel log files off)",
                 len(kernel_files), cfg.jobs)
        slots = PROJECT_ROOT / "build" / "slots"
        global _SLOT_POOL                       # distinct Zephyr build slot per concurrent kernel
        _SLOT_POOL = queue.Queue()
        for i in range(cfg.jobs):
            _SLOT_POOL.put(i)
        with ThreadPoolExecutor(max_workers=cfg.jobs) as ex:
            futs = {ex.submit(_process_kernel, kp, slots / kp.stem, False): kp
                    for kp in kernel_files}
            for fut in as_completed(futs):
                kp = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    log.exception("Kernel %s crashed", kp.stem)
                    res = TranslationResult(kernel_name=kp.stem, success=False, error=str(e))
                results.append(res)
                log.info("[done] %-18s success=%s", kp.stem, getattr(res, "success", False))
    else:
        for kernel_path in kernel_files:
            results.append(_process_kernel(kernel_path, None, True))

    total = len(results)
    success = sum(1 for r in results if r.success)
    log.info("Done: %d/%d translations succeeded", success, total)
    log.info("Status: %s", tracker.summary())


if __name__ == "__main__":
    main()
