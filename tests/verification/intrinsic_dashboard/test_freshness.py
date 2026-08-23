from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard import freshness
from src.workflow.verification.intrinsic_dashboard.freshness import (
    GENERATED_CASES,
    check_generated_models,
    check_semantic_mutation_sensitivity,
    clang_producer_digest,
    generation_watch_digest,
)


ROOT = Path(__file__).resolve().parents[3]


def test_all_checked_in_generated_models_are_deterministically_fresh() -> None:
    assert check_generated_models(ROOT) == {
        case_id: True for case_id in GENERATED_CASES
    }


def test_generation_watch_digest_is_stable_and_content_shaped() -> None:
    first = generation_watch_digest(ROOT)
    second = generation_watch_digest(ROOT)
    producer_first = clang_producer_digest()
    producer_second = clang_producer_digest()

    assert first == second
    assert len(first) == 64
    assert producer_first == producer_second
    assert len(producer_first) == 64


def _make_fake_clang(
    path: Path,
    *,
    version_file: Path,
    resource_pointer: Path,
) -> None:
    path.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        f'  --version) cat "{version_file}" ;;\n'
        f'  --print-resource-dir) cat "{resource_pointer}" ;;\n'
        "  *) exit 2 ;;\n"
        "esac\n",
        encoding="ascii",
    )
    path.chmod(0o755)


def test_generation_watch_digest_binds_complete_clang_identity(
    tmp_path: Path,
) -> None:
    version_file = tmp_path / "version.txt"
    version_file.write_text("clang test version 1\n", encoding="ascii")
    resource_a = tmp_path / "resource-a"
    resource_a.mkdir()
    (resource_a / "include.h").write_text("#define VALUE 1\n", encoding="ascii")
    resource_pointer = tmp_path / "resource.txt"
    resource_pointer.write_text(f"{resource_a}\n", encoding="ascii")
    clang_a = tmp_path / "clang-a"
    _make_fake_clang(
        clang_a,
        version_file=version_file,
        resource_pointer=resource_pointer,
    )

    original = generation_watch_digest(ROOT, clang=str(clang_a))

    clang_b = tmp_path / "clang-b"
    shutil.copyfile(clang_a, clang_b)
    clang_b.chmod(0o755)
    other_resolved_path = generation_watch_digest(ROOT, clang=str(clang_b))
    assert other_resolved_path != original

    clang_a.write_text(
        clang_a.read_text(encoding="ascii") + "# binary-only mutation\n",
        encoding="ascii",
    )
    binary_changed = generation_watch_digest(ROOT, clang=str(clang_a))
    assert binary_changed != original

    version_file.write_text("clang test version 2\n", encoding="ascii")
    version_changed = generation_watch_digest(ROOT, clang=str(clang_a))
    assert version_changed != binary_changed

    (resource_a / "include.h").write_text("#define VALUE 2\n", encoding="ascii")
    resource_content_changed = generation_watch_digest(ROOT, clang=str(clang_a))
    assert resource_content_changed != version_changed

    resource_b = tmp_path / "resource-b"
    resource_b.mkdir()
    (resource_b / "include.h").write_text("#define VALUE 2\n", encoding="ascii")
    resource_pointer.write_text(f"{resource_b}\n", encoding="ascii")
    resource_path_changed = generation_watch_digest(ROOT, clang=str(clang_a))
    assert resource_path_changed != resource_content_changed


def test_all_semantic_mutations_are_frontend_or_emitter_sensitive() -> None:
    assert check_semantic_mutation_sensitivity(ROOT) == {
        case_id: True for case_id in GENERATED_CASES
    }


def test_mutation_gate_does_not_count_provenance_hash_only_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_hash = "0" * 64
    mutated_hash = "1" * 64

    def same_semantics_with_changed_provenance(
        _root: Path,
        _case_id: str,
        neon_source: Path,
        *,
        clang: str,
    ) -> str:
        del clang
        source_hash = (
            mutated_hash
            if neon_source.parent.name.startswith("saltyrn-")
            else original_hash
        )
        return (
            "def neonSourceSha256 : String :=\n"
            f'  "{source_hash}"\n'
            "def neonModel (x : BitVec 8) := x\n"
        )

    monkeypatch.setattr(
        freshness,
        "_emit_model_with_neon_source",
        same_semantics_with_changed_provenance,
    )
    assert check_semantic_mutation_sensitivity(ROOT) == {
        case_id: False for case_id in GENERATED_CASES
    }


def test_mutation_anchors_are_exactly_unique_in_selected_sources() -> None:
    for mutation in freshness._SEMANTIC_MUTATIONS:
        source = (ROOT / "kernels" / "source" / f"{mutation.case_id}.c").read_text(
            encoding="ascii"
        )
        assert source.count(mutation.anchor) == 1
