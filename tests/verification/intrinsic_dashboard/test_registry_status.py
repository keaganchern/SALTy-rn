import shutil
from pathlib import Path
from pathlib import PurePosixPath

from src.workflow.verification.intrinsic_dashboard.registry_status import (
    collect_registry_implementations,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_RELATIVE = Path("src/workflow/verification/lean_backend")
LEAN_RELATIVE = Path("src/verification_bw/lean/SALT")
REVIEWERS_RELATIVE = Path("verification/intrinsic-dashboard/reviewers.json")


def _copy_registry_tcb(destination: Path) -> Path:
    backend_destination = destination / BACKEND_RELATIVE
    backend_destination.mkdir(parents=True)
    for source in (REPOSITORY_ROOT / BACKEND_RELATIVE).rglob("*.py"):
        relative = source.relative_to(REPOSITORY_ROOT / BACKEND_RELATIVE)
        target = backend_destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in (REPOSITORY_ROOT / BACKEND_RELATIVE / "facade").rglob("*.h"):
        relative = source.relative_to(REPOSITORY_ROOT / BACKEND_RELATIVE)
        target = backend_destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    for relative in (
        LEAN_RELATIVE / "Basic.lean",
        LEAN_RELATIVE / "Intrinsics" / "Neon.lean",
        LEAN_RELATIVE / "Intrinsics" / "RVV.lean",
        REVIEWERS_RELATIVE,
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, target)
    return destination


def test_registry_projection_has_unique_variant_subjects() -> None:
    records = collect_registry_implementations(REPOSITORY_ROOT)

    assert len(records) > 85  # 85 is only the current spelling count.
    assert set(records) == {record["subject_id"] for record in records.values()}
    assert len({record["subject_id"] for record in records.values()}) == len(records)
    assert all(
        key == f"{record['architecture']}:{record['name']}@{record['profile']}"
        for key, record in records.items()
    )
    assert all(
        record["profile"] == record["variant_sha256"] for record in records.values()
    )
    assert all(len(record["variant_sha256"]) == 64 for record in records.values())
    assert all(record["variant"] for record in records.values())
    assert all(record["descriptor_paths"] for record in records.values())
    for record in records.values():
        for descriptor_path in record["descriptor_paths"]:
            parsed = PurePosixPath(descriptor_path)
            assert not parsed.is_absolute()
            assert ".." not in parsed.parts
            assert (REPOSITORY_ROOT / descriptor_path).is_file()
    assert all(record["supported_cases"] for record in records.values())
    assert all(record["signature"] for record in records.values())
    assert all(record["code"] for record in records.values())
    assert all(record["tcb_files"] for record in records.values())
    assert all(
        REVIEWERS_RELATIVE.as_posix() in record["tcb_files"]
        for record in records.values()
    )
    assert all(
        record["implementation_status"] == "case-scoped" for record in records.values()
    )
    assert all(
        record["adequacy_status"] == "not-established" for record in records.values()
    )


def test_equal_canonical_variants_merge_supported_cases() -> None:
    records = collect_registry_implementations(REPOSITORY_ROOT)

    shared = [
        record
        for record in records.values()
        if record["architecture"] == "neon"
        and record["name"] == "vqaddq_s16"
        and {"qs8-vcvt", "qs8-vadd-minmax"}.issubset(record["supported_cases"])
    ]
    assert len(shared) == 1


def test_vnclip_variants_with_distinct_targets_are_not_merged() -> None:
    records = collect_registry_implementations(REPOSITORY_ROOT)
    vnclip = [
        record
        for record in records.values()
        if record["architecture"] == "rvv"
        and record["name"] == "__riscv_vnclip_wx_i16m4"
    ]

    assert len(vnclip) >= 4
    assert len({record["subject_id"] for record in vnclip}) == len(vnclip)
    assert {
        "SALT.Intrinsics.RVV.vnclip_wx_i16",
        "SALT.Intrinsics.RVV.vnclip_wx_i16_mode",
    }.issubset({record["lean_target"] for record in vnclip})
    assert {
        (BACKEND_RELATIVE / "registry.py").as_posix(),
        (BACKEND_RELATIVE / "scaleup_catalog.py").as_posix(),
    } == {
        descriptor_path
        for record in vnclip
        for descriptor_path in record["descriptor_paths"]
    }


def test_semantics_hash_binds_basic_and_frontend_but_not_descriptor_source(
    tmp_path: Path,
) -> None:
    repository = _copy_registry_tcb(tmp_path / "repository")
    baseline = collect_registry_implementations(repository)
    subject_id = next(iter(baseline))

    basic = repository / LEAN_RELATIVE / "Basic.lean"
    basic.write_text(
        basic.read_text(encoding="utf-8") + "\n-- test mutation\n",
        encoding="utf-8",
    )
    after_basic = collect_registry_implementations(repository)
    assert (
        after_basic[subject_id]["source_sha256"]
        == baseline[subject_id]["source_sha256"]
    )
    assert (
        after_basic[subject_id]["semantics_sha256"]
        != baseline[subject_id]["semantics_sha256"]
    )

    frontend = repository / BACKEND_RELATIVE / "frontend.py"
    frontend.write_text(
        frontend.read_text(encoding="utf-8") + "\n# test mutation\n",
        encoding="utf-8",
    )
    after_frontend = collect_registry_implementations(repository)
    assert (
        after_frontend[subject_id]["source_sha256"]
        == baseline[subject_id]["source_sha256"]
    )
    assert (
        after_frontend[subject_id]["semantics_sha256"]
        != after_basic[subject_id]["semantics_sha256"]
    )

    reviewers = repository / REVIEWERS_RELATIVE
    reviewers.write_text(
        reviewers.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    after_authority = collect_registry_implementations(repository)
    assert (
        after_authority[subject_id]["source_sha256"]
        == baseline[subject_id]["source_sha256"]
    )
    assert (
        after_authority[subject_id]["semantics_sha256"]
        != after_frontend[subject_id]["semantics_sha256"]
    )


def test_source_and_semantics_digests_are_independent() -> None:
    records = collect_registry_implementations(REPOSITORY_ROOT)
    neon = [record for record in records.values() if record["architecture"] == "neon"]

    # One architecture shares a conservative semantic TCB, while each
    # descriptor/case binding retains its own source digest.
    assert len({record["semantics_sha256"] for record in neon}) == 1
    assert len({record["source_sha256"] for record in neon}) > 1
    assert all(
        record["source_sha256"] != record["semantics_sha256"]
        for record in records.values()
    )
