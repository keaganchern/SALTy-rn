#!/usr/bin/env python3
"""Run the reproducibility, build, source, and exported-axiom gates."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile


EXPORTED_THEOREMS = (
    "Neon2LeanDemo.generated_stores_correct",
    "Neon2LeanDemo.exact_write_footprint",
    "Neon2LeanDemo.extracted_loop_metadata",
    "Neon2LeanDemo.S8VClamp.neon_rvv_policy_value_equiv",
    "Neon2LeanDemo.S8Clamp16.source_coverage_bound",
    "Neon2LeanDemo.S8Clamp16.target_coverage_bound",
    "Neon2LeanDemo.S8Clamp16.source_registry_checked",
    "Neon2LeanDemo.S8Clamp16.target_registry_checked",
    "Neon2LeanDemo.S8Clamp16.source_use_order_checked",
    "Neon2LeanDemo.S8Clamp16.target_use_order_checked",
    "Neon2LeanDemo.S8Clamp16.generated_value_equivalence",
    "Neon2LeanDemo.S8Clamp16.generated_memory_execution_equal",
    "Neon2LeanDemo.S8Clamp16.generated_end_to_end",
    "Neon2LeanDemo.S8Clamp16.generated_success_under_contract",
)

ALLOWED_AXIOMS = {"propext", "Quot.sound"}
FORBIDDEN_SOURCE = re.compile(
    r"\b(?:sorry|admit|axiom|unsafe|native_decide|bv_decide)\b"
)
AXIOM_DEPENDENCY = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
NO_AXIOMS = re.compile(r"^'([^']+)' does not depend on any axioms$")


class CheckError(RuntimeError):
    pass


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        rendered = " ".join(command)
        raise CheckError(
            f"command failed ({result.returncode}): {rendered}\n"
            f"{result.stdout}{result.stderr}"
        )
    output = result.stdout + result.stderr
    if output.strip():
        print(output.rstrip())
    return output


def scan_lean_sources(project: Path) -> None:
    violations: list[str] = []
    sources = [project / "Neon2LeanDemo.lean"]
    sources.extend(sorted((project / "Neon2LeanDemo").rglob("*.lean")))
    for source in sources:
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN_SOURCE.search(line):
                violations.append(f"{source.relative_to(project)}:{line_number}: {line.strip()}")
    if violations:
        raise CheckError("forbidden Lean source tokens:\n" + "\n".join(violations))


def audit_axioms(project: Path) -> None:
    audit_source = "import Neon2LeanDemo\n\n" + "\n".join(
        f"#print axioms {name}" for name in EXPORTED_THEOREMS
    ) + "\n"
    with tempfile.TemporaryDirectory(prefix="saltyrn-lean-axioms-") as raw_tmp:
        audit_path = Path(raw_tmp) / "AxiomAudit.lean"
        audit_path.write_text(audit_source, encoding="utf-8")
        output = run(["lake", "env", "lean", str(audit_path)], project)

    seen: set[str] = set()
    violations: list[str] = []
    for line in output.splitlines():
        dependency = AXIOM_DEPENDENCY.match(line.strip())
        if dependency:
            theorem, raw_axioms = dependency.groups()
            seen.add(theorem)
            axioms = {item.strip() for item in raw_axioms.split(",") if item.strip()}
            unexpected = axioms - ALLOWED_AXIOMS
            if unexpected:
                violations.append(f"{theorem}: unexpected axioms {sorted(unexpected)}")
            continue
        no_axioms = NO_AXIOMS.match(line.strip())
        if no_axioms:
            seen.add(no_axioms.group(1))

    missing = set(EXPORTED_THEOREMS) - seen
    if missing:
        violations.append(f"missing #print axioms output for {sorted(missing)}")
    if violations:
        raise CheckError("axiom audit failed:\n" + "\n".join(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    project = repo_root / "prototype/neon2lean"

    try:
        run(
            [sys.executable, str(project / "tools/test_s8_extractor.py"),
             "--workspace", str(repo_root)],
            repo_root,
        )
        run(
            [sys.executable, str(project / "tools/test_s8_clamp16.py"),
             "--repo-root", str(repo_root)],
            repo_root,
        )
        run(["lake", "build"], project)
        scan_lean_sources(project)
        audit_axioms(project)
    except (CheckError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("PASS: regeneration, frontend failures, Lean build, source policy, and axiom audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
