"""Name/path-independent acceptance gate for the elementwise compiler slice."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Callable, Mapping

from .compiler import CompilerRequest, compile_pair
from .proof import check_proof, prepare_proof_task
from .schema import ResultStatus, canonical_sha256


ProofProvider = Callable[[Path, str], None]


class HeldoutGateError(RuntimeError):
    """A positive, negative, determinism, or no-framework-edit gate failed."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_snapshot(repository: Path) -> str:
    completed = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise HeldoutGateError("cannot enumerate tracked framework files")
    records = []
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8")
        path = repository / relative
        records.append(
            {
                "path": relative,
                "sha256": _sha256(path) if path.is_file() else "absent",
            }
        )
    return canonical_sha256(records)


def _tree_digest(root: Path) -> str:
    return canonical_sha256(
        [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
            }
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ]
    )


def _request(
    repository: Path,
    neon: Path,
    rvv: Path,
    neon_function: str,
    rvv_function: str,
    namespace: str,
    output: Path,
) -> CompilerRequest:
    facade = repository / "src/workflow/verification/lean_backend/facade/s8_vmax_example.h"
    return CompilerRequest(
        repository,
        neon,
        rvv,
        neon_function,
        rvv_function,
        facade,
        facade,
        "aarch64-none-elf",
        "riscv64-none-elf",
        namespace,
        output,
    )


def _positive(
    repository: Path,
    request: CompilerRequest,
    proof_provider: ProofProvider,
) -> Mapping[str, object]:
    first = compile_pair(request)
    prepare_proof_task(repository, request.output_directory)
    deterministic = _tree_digest(request.output_directory)
    shutil.rmtree(request.output_directory)
    second = compile_pair(request)
    prepare_proof_task(repository, request.output_directory)
    if _tree_digest(request.output_directory) != deterministic:
        raise HeldoutGateError("delete/regenerate changed a positive artifact stack")
    if first.manifest != second.manifest:
        raise HeldoutGateError("delete/regenerate changed the program manifest")
    proof_provider(request.output_directory, request.namespace)
    checked = check_proof(repository, request.output_directory)
    if checked.result.status is not ResultStatus.VERIFIED_VALUE:
        raise HeldoutGateError(f"positive proof did not verify: {checked.result.detail}")
    return {
        "status": checked.result.status.value,
        "manifest_sha256": second.manifest.sha256,
        "proof_task_sha256": checked.task.sha256,
        "result_sha256": checked.result.sha256,
        "deterministic": True,
    }


def _expect_rejected(request: CompilerRequest) -> str:
    try:
        compile_pair(request)
    except Exception as error:  # The public contract is fail-closed across stages.
        return f"{type(error).__name__}: {error}"
    raise HeldoutGateError("structural mutation unexpectedly generated artifacts")


def run_heldout_gate(
    repository_root: str | Path,
    proof_provider: ProofProvider,
) -> dict[str, object]:
    """Run two new-program positives, one semantic negative, and four mutations."""

    repository = Path(repository_root).resolve()
    before = _tracked_snapshot(repository)
    token = uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix=".elementwise-heldout-", dir=repository) as name:
        work = Path(name)
        original_neon = repository / "examples/s8-vmax-to-lean/neon.c"
        original_rvv = repository / "examples/s8-vmax-to-lean/rvv.c"

        positive_a = _request(
            repository,
            original_neon,
            original_rvv,
            "test_neon",
            "test_rvv",
            f"SALT.Heldout.First{token}",
            work / "positive-a",
        )
        first = _positive(repository, positive_a, proof_provider)

        random_source = work / f"unseen-{token}" / "neon-side" / f"alpha-{token}.c"
        random_target = work / f"unseen-{token}" / "rvv-side" / f"omega-{token}.c"
        random_source.parent.mkdir(parents=True)
        random_target.parent.mkdir(parents=True)
        neon_function = f"fresh_neon_{token}"
        rvv_function = f"fresh_rvv_{token}"
        random_source.write_text(
            original_neon.read_text(encoding="utf-8").replace("test_neon", neon_function),
            encoding="utf-8",
        )
        random_target.write_text(
            original_rvv.read_text(encoding="utf-8").replace("test_rvv", rvv_function),
            encoding="utf-8",
        )
        namespace = f"SALT.Heldout.Random{token}.Nested"
        positive_b = _request(
            repository,
            random_source,
            random_target,
            neon_function,
            rvv_function,
            namespace,
            work / f"random-output-{token}",
        )
        second = _positive(repository, positive_b, proof_provider)

        negative_neon = work / "negative" / "semantic.c"
        negative_neon.parent.mkdir(parents=True)
        negative_neon.write_text(
            random_source.read_text(encoding="utf-8").replace("vmaxq_s8", "vminq_s8", 1),
            encoding="utf-8",
        )
        negative_request = _request(
            repository,
            negative_neon,
            random_target,
            neon_function,
            rvv_function,
            f"SALT.Heldout.Negative{token}",
            work / "negative-output",
        )
        compile_pair(negative_request)
        prepare_proof_task(repository, negative_request.output_directory)
        proof_provider(negative_request.output_directory, negative_request.namespace)
        negative = check_proof(repository, negative_request.output_directory)
        if negative.result.status is ResultStatus.VERIFIED_VALUE:
            raise HeldoutGateError("max-to-min semantic mutation retained the original proof")

        mutation_specs = {
            "pointer-step": (
                random_source,
                "input += 16",
                "input += 15",
                random_target,
            ),
            "loop-update": (
                random_source,
                "batch -= 16",
                "batch -= 15",
                random_target,
            ),
            "entry-assert": (
                random_source,
                "batch % 16 == 0",
                "batch % 8 == 0",
                random_target,
            ),
            "active-vl": (
                random_target,
                "__riscv_vse8_v_i8m8(output, vx, vl)",
                "__riscv_vse8_v_i8m8(output, vx, 1)",
                random_source,
            ),
        }
        mutations: dict[str, str] = {}
        for label, (selected, old, new, partner) in mutation_specs.items():
            mutated = work / "mutations" / f"{label}.c"
            mutated.parent.mkdir(parents=True, exist_ok=True)
            source_text = selected.read_text(encoding="utf-8")
            if old not in source_text:
                raise HeldoutGateError(f"mutation anchor disappeared: {label}")
            mutated.write_text(source_text.replace(old, new, 1), encoding="utf-8")
            if selected == random_source:
                neon, rvv = mutated, partner
            else:
                neon, rvv = partner, mutated
            mutations[label] = _expect_rejected(
                _request(
                    repository,
                    neon,
                    rvv,
                    neon_function,
                    rvv_function,
                    f"SALT.Heldout.Mutation{token}{label.replace('-', '')}",
                    work / "mutation-output" / label,
                )
            )

        report = {
            "schema_version": 1,
            "positive_a": first,
            "positive_b_random_identity": second,
            "negative_max_to_min": {
                "status": negative.result.status.value,
                "result_sha256": negative.result.sha256,
            },
            "structural_mutations": mutations,
            "framework_unchanged": _tracked_snapshot(repository) == before,
        }
    if not report["framework_unchanged"]:
        raise HeldoutGateError("held-out gate modified tracked framework files")
    return report


def report_json(report: Mapping[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"
