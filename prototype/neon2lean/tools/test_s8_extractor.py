#!/usr/bin/env python3
"""Regression and fail-closed checks for extract_s8_vclamp.py."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    repo = workspace / "upstream-main" if (workspace / "upstream-main/kernels").is_dir() else workspace
    tool_dir = Path(__file__).resolve().parent
    source_input = repo / "kernels/source/s8-vclamp.c"
    target_input = repo / "kernels/target/s8-vclamp.c"

    try:
        with tempfile.TemporaryDirectory(prefix="saltyrn-s8-extractor-") as raw_tmp:
            tmp = Path(raw_tmp)
            fixture = tmp / "repo"
            fixture_tools = fixture / "prototype/neon2lean/tools"
            fixture_source_dir = fixture / "kernels/source"
            fixture_target_dir = fixture / "kernels/target"
            testdata = fixture / "testdata"
            fixture_tools.mkdir(parents=True)
            fixture_source_dir.mkdir(parents=True)
            fixture_target_dir.mkdir(parents=True)
            testdata.mkdir()
            for name in (
                "extract_s8_vclamp.py",
                "emit_s8_manifest_lean.py",
                "s8_vclamp_parse_facade.h",
            ):
                shutil.copy2(tool_dir / name, fixture_tools / name)
            source = fixture_source_dir / "s8-vclamp.c"
            target = fixture_target_dir / "s8-vclamp.c"
            shutil.copy2(source_input, source)
            shutil.copy2(target_input, target)
            baseline = tmp / "baseline.json"
            base_command = [
                sys.executable,
                str(fixture_tools / "extract_s8_vclamp.py"),
                "--source",
                "kernels/source/s8-vclamp.c",
                "--target",
                "kernels/target/s8-vclamp.c",
                "--repo-root",
                str(fixture),
            ]

            result = run(base_command + ["--output", str(baseline)], fixture)
            require(result.returncode == 0, f"baseline extraction failed:\n{result.stderr}")
            manifest = json.loads(baseline.read_text(encoding="utf-8"))
            require(
                manifest["units"]["source"]["ast_coverage"]["coverage_percent"] == 100.0,
                "source coverage is not complete",
            )
            require(
                manifest["units"]["target"]["ast_coverage"]["coverage_percent"] == 100.0,
                "target coverage is not complete",
            )
            require(
                manifest["units"]["source"]["path"] == "kernels/source/s8-vclamp.c",
                "source path is not repository relative",
            )
            require(
                manifest["units"]["target"]["path"] == "kernels/target/s8-vclamp.c",
                "target path is not repository relative",
            )
            manifest_text = baseline.read_text(encoding="utf-8")
            require("/Users/" not in manifest_text, "manifest contains a user path")
            require("upstream-main/" not in manifest_text, "manifest contains a wrapper path")
            require(str(tmp) not in manifest_text, "manifest contains a temporary path")

            repeated_baseline = tmp / "baseline-repeated.json"
            result = run(base_command + ["--output", str(repeated_baseline)], fixture)
            require(result.returncode == 0, f"repeated extraction failed:\n{result.stderr}")
            require(
                baseline.read_bytes() == repeated_baseline.read_bytes(),
                "extractor output is not byte deterministic",
            )

            generated_once = tmp / "generated-once.lean"
            generated_twice = tmp / "generated-twice.lean"
            emitter = fixture_tools / "emit_s8_manifest_lean.py"
            for output in (generated_once, generated_twice):
                result = run(
                    [
                        sys.executable,
                        str(emitter),
                        "--manifest",
                        str(baseline),
                        "--output",
                        str(output),
                    ],
                    fixture,
                )
                require(result.returncode == 0, f"Lean emission failed:\n{result.stderr}")
            require(
                generated_once.read_bytes() == generated_twice.read_bytes(),
                "Lean emitter output is not byte deterministic",
            )
            generated_text = generated_once.read_text(encoding="utf-8")
            require("/Users/" not in generated_text, "Lean output contains a user path")
            require("upstream-main/" not in generated_text, "Lean output contains a wrapper path")

            malformed_manifest = json.loads(baseline.read_text(encoding="utf-8"))
            malformed_manifest["units"]["source"]["byte_length"] = "0); #eval true"
            malformed_path = tmp / "malformed-manifest.json"
            malformed_path.write_text(json.dumps(malformed_manifest), encoding="utf-8")
            malformed_output = tmp / "malformed.lean"
            result = run(
                [
                    sys.executable,
                    str(emitter),
                    "--manifest",
                    str(malformed_path),
                    "--output",
                    str(malformed_output),
                ],
                fixture,
            )
            require(result.returncode != 0, "malformed numeric manifest field was accepted")
            require(not malformed_output.exists(), "malformed manifest produced Lean output")

            facade = fixture_tools / "s8_vclamp_parse_facade.h"
            facade.write_text(
                facade.read_text(encoding="utf-8")
                + "\nint8x16_t forbidden_max_s8(int8x16_t, int8x16_t);\n",
                encoding="utf-8",
            )
            unknown_source = testdata / "unknown-call.c"
            unknown_source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "vmaxq_s8(", "forbidden_max_s8(", 1
                ),
                encoding="utf-8",
            )
            unknown_output = tmp / "unknown.json"
            result = run(
                base_command[:2]
                + ["--source", str(unknown_source), "--target", str(target),
                   "--repo-root", str(fixture), "--facade", str(facade),
                   "--output", str(unknown_output)],
                fixture,
            )
            require(result.returncode != 0, "unknown intrinsic was accepted")
            require("unsupported call spelling" in result.stderr, result.stderr)
            require(not unknown_output.exists(), "unknown intrinsic produced an artifact")

            float_source = testdata / "reachable-float.c"
            float_source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "{\n  assert(batch != 0);",
                    "{\n  float forbidden_fp = 1.0f;\n  assert(batch != 0);",
                    1,
                ),
                encoding="utf-8",
            )
            float_output = tmp / "float.json"
            result = run(
                base_command[:2]
                + ["--source", str(float_source), "--target", str(target),
                   "--output", str(float_output)],
                fixture,
            )
            require(result.returncode != 0, "reachable floating point was accepted")
            require("floating" in result.stderr.lower(), result.stderr)
            require(not float_output.exists(), "reachable floating point produced an artifact")

            semantic_source = testdata / "semantic-mutation.c"
            semantic_source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "vminq_s8(", "vmaxq_s8(", 1
                ),
                encoding="utf-8",
            )
            semantic_output = tmp / "semantic.json"
            result = run(
                base_command[:2]
                + ["--source", str(semantic_source), "--target", str(target),
                   "--output", str(semantic_output)],
                fixture,
            )
            require(result.returncode != 0, "semantic intrinsic mutation was accepted")
            require(not semantic_output.exists(), "semantic mutation produced an artifact")

            cast_target = testdata / "nested-cast.c"
            cast_target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "(int8_t) params->scalar.min",
                    "(int8_t) (uint32_t) params->scalar.min",
                    1,
                ),
                encoding="utf-8",
            )
            cast_output = tmp / "nested-cast.json"
            result = run(
                base_command[:2]
                + ["--source", str(source), "--target", str(cast_target),
                   "--output", str(cast_output)],
                fixture,
            )
            require(result.returncode != 0, "nested integer cast was accepted")
            require("cast" in result.stderr.lower(), result.stderr)
            require(not cast_output.exists(), "nested integer cast produced an artifact")

            signature_type_source = testdata / "signature-type.c"
            signature_type_source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "    size_t batch,", "    uint32_t batch,", 1
                ),
                encoding="utf-8",
            )
            signature_type_output = tmp / "signature-type.json"
            result = run(
                base_command[:2]
                + ["--source", str(signature_type_source), "--target", str(target),
                   "--output", str(signature_type_output)],
                fixture,
            )
            require(result.returncode != 0, "changed source parameter type was accepted")
            require("signature" in result.stderr.lower(), result.stderr)
            require(
                not signature_type_output.exists(),
                "changed source parameter type produced an artifact",
            )

            signature_arity_target = testdata / "signature-arity.c"
            signature_arity_target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "    size_t batch,", "    size_t batch,\n    int8_t unused,", 1
                ),
                encoding="utf-8",
            )
            signature_arity_output = tmp / "signature-arity.json"
            result = run(
                base_command[:2]
                + ["--source", str(source), "--target", str(signature_arity_target),
                   "--output", str(signature_arity_output)],
                fixture,
            )
            require(result.returncode != 0, "changed target parameter count was accepted")
            require("signature" in result.stderr.lower(), result.stderr)
            require(
                not signature_arity_output.exists(),
                "changed target parameter count produced an artifact",
            )
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print(
        "PASS: deterministic coverage/emission, unknown-intrinsic rejection, "
        "FP rejection, cast/malformed-manifest rejection, semantic-mutation rejection, "
        "signature rejection"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
