#!/usr/bin/env python3
"""Regression checks for the generated s8-clamp16 semantic IR slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def extractor_command(repo_root: Path, neon: Path, rvv: Path, facade: Path,
                      output: Path) -> list[str]:
    return [
        sys.executable,
        str(repo_root / "prototype/neon2lean/tools/extract_s8_clamp16.py"),
        "--repo-root", str(repo_root),
        "--neon", str(neon),
        "--rvv", str(rvv),
        "--facade", str(facade),
        "--output", str(output),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    case_dir = repo_root / "prototype/neon2lean/cases/s8-clamp16"
    neon = case_dir / "neon.c"
    rvv = case_dir / "rvv.c"
    facade = case_dir / "intrinsics_facade.h"
    checked_manifest = repo_root / "prototype/neon2lean/artifacts/s8-clamp16/manifest.json"
    checked_lean = repo_root / "prototype/neon2lean/Neon2LeanDemo/S8Clamp16/Generated.lean"
    emitter = repo_root / "prototype/neon2lean/tools/emit_s8_clamp16_lean.py"

    try:
        with tempfile.TemporaryDirectory(
            prefix="s8-clamp16-regression-", dir=repo_root / "prototype/neon2lean"
        ) as raw_tmp:
            tmp = Path(raw_tmp)
            baseline = tmp / "baseline.json"
            repeated = tmp / "repeated.json"
            for output in (baseline, repeated):
                result = run(extractor_command(repo_root, neon, rvv, facade, output), repo_root)
                require(result.returncode == 0, f"baseline extraction failed:\n{result.stderr}")
            require(baseline.read_bytes() == repeated.read_bytes(), "extractor is not deterministic")
            require(baseline.read_bytes() == checked_manifest.read_bytes(), "checked manifest is stale")

            generated = tmp / "Generated.lean"
            generated_again = tmp / "Generated-again.lean"
            for output in (generated, generated_again):
                result = run(
                    [sys.executable, str(emitter), "--manifest", str(baseline), "--output", str(output)],
                    repo_root,
                )
                require(result.returncode == 0, f"Lean emission failed:\n{result.stderr}")
            require(generated.read_bytes() == generated_again.read_bytes(), "emitter is not deterministic")
            require(generated.read_bytes() == checked_lean.read_bytes(), "checked Lean data is stale")

            mutation_dir = tmp / "mutation"
            mutation_dir.mkdir()
            mutated_neon = mutation_dir / "neon.c"
            mutated_rvv = mutation_dir / "rvv.c"
            mutated_facade = mutation_dir / "intrinsics_facade.h"
            shutil.copy2(neon, mutated_neon)
            shutil.copy2(facade, mutated_facade)
            mutated_rvv.write_text(
                rvv.read_text(encoding="utf-8").replace(
                    "__riscv_vmin_vx_i8m1(value, hi, vl)",
                    "__riscv_vmax_vx_i8m1(value, hi, vl)",
                    1,
                ),
                encoding="utf-8",
            )
            mutated_manifest = tmp / "mutated.json"
            result = run(
                extractor_command(
                    repo_root, mutated_neon, mutated_rvv, mutated_facade, mutated_manifest
                ),
                repo_root,
            )
            require(result.returncode == 0, f"supported mutation was rejected:\n{result.stderr}")
            mutation = json.loads(mutated_manifest.read_text(encoding="utf-8"))
            spellings = [
                operation["spelling"]
                for operation in mutation["units"]["rvv"]["ir"]["blocks"][0]["operations"]
            ]
            require(
                spellings.count("__riscv_vmax_vx_i8m1") == 2
                and "__riscv_vmin_vx_i8m1" not in spellings,
                "supported mutation did not produce distinct semantic IR",
            )
            mutated_lean = tmp / "MutatedGenerated.lean"
            result = run(
                [sys.executable, str(emitter), "--manifest", str(mutated_manifest),
                 "--output", str(mutated_lean)],
                repo_root,
            )
            require(result.returncode == 0, f"mutated IR emission failed:\n{result.stderr}")
            result = run(["lake", "env", "lean", str(mutated_lean)], repo_root / "prototype/neon2lean")
            require(
                result.returncode == 0,
                f"mutated generated Lean data did not compile:\n{result.stdout}{result.stderr}",
            )

            unknown_dir = tmp / "unknown"
            unknown_dir.mkdir()
            unknown_neon = unknown_dir / "neon.c"
            unknown_rvv = unknown_dir / "rvv.c"
            unknown_facade = unknown_dir / "intrinsics_facade.h"
            shutil.copy2(neon, unknown_neon)
            shutil.copy2(rvv, unknown_rvv)
            unknown_facade.write_text(
                facade.read_text(encoding="utf-8")
                + "\nvint8m1_t forbidden_op(vint8m1_t, int8_t, size_t);\n",
                encoding="utf-8",
            )
            unknown_rvv.write_text(
                rvv.read_text(encoding="utf-8").replace(
                    "__riscv_vmin_vx_i8m1(value, hi, vl)", "forbidden_op(value, hi, vl)", 1
                ),
                encoding="utf-8",
            )
            unknown_output = tmp / "unknown.json"
            result = run(
                extractor_command(repo_root, unknown_neon, unknown_rvv, unknown_facade, unknown_output),
                repo_root,
            )
            require(result.returncode != 0, "unknown intrinsic was accepted")
            require("unsupported call spelling" in result.stderr, result.stderr)
            require(not unknown_output.exists(), "unknown intrinsic produced an artifact")

            unsupported_dir = tmp / "unsupported"
            unsupported_dir.mkdir()
            unsupported_neon = unsupported_dir / "neon.c"
            unsupported_rvv = unsupported_dir / "rvv.c"
            unsupported_facade = unsupported_dir / "intrinsics_facade.h"
            shutil.copy2(neon, unsupported_neon)
            shutil.copy2(facade, unsupported_facade)
            unsupported_rvv.write_text(
                rvv.read_text(encoding="utf-8").replace(
                    "    const size_t vl =", "    if (remaining == 1) remaining = 0;\n    const size_t vl =", 1
                ),
                encoding="utf-8",
            )
            unsupported_output = tmp / "unsupported.json"
            result = run(
                extractor_command(
                    repo_root, unsupported_neon, unsupported_rvv, unsupported_facade,
                    unsupported_output
                ),
                repo_root,
            )
            require(result.returncode != 0, "unsupported AST was accepted")
            require(not unsupported_output.exists(), "unsupported AST produced an artifact")

            malformed = json.loads(baseline.read_text(encoding="utf-8"))
            malformed["units"]["neon"]["artifact"]["byte_length"] = "0); #eval true"
            malformed_path = tmp / "malformed.json"
            malformed_path.write_text(json.dumps(malformed), encoding="utf-8")
            malformed_output = tmp / "malformed.lean"
            result = run(
                [sys.executable, str(emitter), "--manifest", str(malformed_path),
                 "--output", str(malformed_output)],
                repo_root,
            )
            require(result.returncode != 0, "malformed numeric field was accepted")
            require(not malformed_output.exists(), "malformed manifest produced Lean output")
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print(
        "PASS: deterministic semantic IR/emission, supported-mutation lowering, "
        "unknown/unsupported rejection, malformed-manifest rejection"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
