import shutil
import subprocess
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.scanner import (
    LEXICAL_METHOD,
    InventoryScanError,
    parse_microkernel_manifest,
    scan_pinned_xnnpack,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", message)
    return _git(repository, "rev-parse", "HEAD")


def _fixture_repository(tmp_path: Path) -> tuple[Path, Path, str]:
    parent = tmp_path / "parent"
    xnnpack = parent / "benchmark/XNNPACK"
    xnnpack.mkdir(parents=True)
    _git(xnnpack, "init")
    _git(xnnpack, "config", "user.name", "Scanner Test")
    _git(xnnpack, "config", "user.email", "scanner@example.invalid")

    _write(
        xnnpack / "cmake/gen/neon_microkernels.cmake",
        """SET(PROD_NEON_MICROKERNEL_SRCS
  src/f32-vbinary/gen/prod-neon.c)

SET(NON_PROD_NEON_MICROKERNEL_SRCS
  src/f32-vbinary/gen/nonprod-neon.c)

SET(ALL_NEON_MICROKERNEL_SRCS
  ${PROD_NEON_MICROKERNEL_SRCS} + ${NON_PROD_NEON_MICROKERNEL_SRCS})
""",
    )
    # Empty generated lists are valid and must not consume the following SET.
    _write(
        xnnpack / "cmake/gen/neonbf16_microkernels.cmake",
        """SET(PROD_NEONBF16_MICROKERNEL_SRCS)

SET(NON_PROD_NEONBF16_MICROKERNEL_SRCS)

SET(ALL_NEONBF16_MICROKERNEL_SRCS
  ${PROD_NEONBF16_MICROKERNEL_SRCS} + ${NON_PROD_NEONBF16_MICROKERNEL_SRCS})
""",
    )
    _write(
        xnnpack / "cmake/gen/rvv_microkernels.cmake",
        """SET(PROD_RVV_MICROKERNEL_SRCS
  src/qs8-vadd/gen/prod-rvv.c)

SET(NON_PROD_RVV_MICROKERNEL_SRCS)

SET(ALL_RVV_MICROKERNEL_SRCS
  ${PROD_RVV_MICROKERNEL_SRCS} + ${NON_PROD_RVV_MICROKERNEL_SRCS})
""",
    )
    _write(
        xnnpack / "src/f32-vbinary/gen/prod-neon.c",
        r"""void kernel(void) {
  vaddq_f32(a, b);
  vaddq_f32(a, b);
  vld1q_f32(input);
  // vmulq_f32(comment_only, comment_only);
  const char* text = "vsubq_f32(string_only, string_only)";
}
""",
    )
    _write(
        xnnpack / "src/f32-vbinary/gen/nonprod-neon.c",
        "void kernel(void) { vmulq_f32(a, b); }\n",
    )
    _write(
        xnnpack / "src/qs8-vadd/gen/prod-rvv.c",
        "void kernel(void) {\n"
        "  __riscv_vsetvl_e8m1(n);\n"
        "  __riscv_vsetvl_e8m1(n);\n"
        "}\n",
    )
    pinned_commit = _commit(xnnpack, "fixture XNNPACK")

    _git(parent, "init")
    _git(parent, "config", "user.name", "Scanner Test")
    _git(parent, "config", "user.email", "scanner@example.invalid")
    _git(parent, "add", "benchmark/XNNPACK")
    _git(parent, "commit", "-m", "pin fixture XNNPACK")
    return parent, xnnpack, pinned_commit


def test_scan_uses_parent_gitlink_objects_and_counts_relations(tmp_path: Path) -> None:
    parent, xnnpack, pinned_commit = _fixture_repository(tmp_path)

    # A dirty checkout must not change the inventory at the committed gitlink.
    _write(
        xnnpack / "src/f32-vbinary/gen/prod-neon.c",
        "void kernel(void) { vsubq_f32(a, b); }\n",
    )
    inventory = scan_pinned_xnnpack(parent)

    assert inventory.pinned_commit == pinned_commit
    assert inventory.method == LEXICAL_METHOD
    assert len(inventory.manifests) == 3
    assert len(inventory.programs) == 3
    assert {usage.operator for usage in inventory.usages} == {
        "vaddq_f32",
        "vld1q_f32",
        "vmulq_f32",
        "__riscv_vsetvl_e8m1",
    }
    assert "vsubq_f32" not in {usage.operator for usage in inventory.usages}

    summaries = {
        (summary.architecture, summary.operator): summary
        for summary in inventory.operator_summaries()
    }
    vadd = summaries[("neon", "vaddq_f32")]
    assert vadd.occurrences == 2
    assert vadd.family_count == 1
    assert vadd.program_count == 1
    assert vadd.production_occurrences == 2
    assert vadd.production_program_count == 1

    vmul = summaries[("neon", "vmulq_f32")]
    assert vmul.occurrences == 1
    assert vmul.production_occurrences == 0
    assert vmul.production_program_count == 0

    rvv = summaries[("rvv", "__riscv_vsetvl_e8m1")]
    assert rvv.occurrences == 2
    assert rvv.production_family_count == 1


def test_scan_rejects_checkout_head_that_differs_from_gitlink(tmp_path: Path) -> None:
    parent, xnnpack, _pinned_commit = _fixture_repository(tmp_path)
    _write(xnnpack / "new-file.txt", "second commit\n")
    _commit(xnnpack, "move checkout past parent pin")

    with pytest.raises(InventoryScanError, match="does not match the parent gitlink"):
        scan_pinned_xnnpack(parent)


def test_scan_uses_submodule_object_database_without_a_checkout(
    tmp_path: Path,
) -> None:
    parent, xnnpack, pinned_commit = _fixture_repository(tmp_path)
    object_git_dir = parent / ".git/modules/benchmark/XNNPACK"
    object_git_dir.parent.mkdir(parents=True)
    completed = subprocess.run(
        ("git", "clone", "--bare", str(xnnpack), str(object_git_dir)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    shutil.rmtree(xnnpack)

    inventory = scan_pinned_xnnpack(parent)

    assert inventory.pinned_commit == pinned_commit
    assert len(inventory.programs) == 3


def test_manifest_parser_fails_closed_on_duplicate_or_invalid_entries() -> None:
    manifest_path = "cmake/gen/neon_microkernels.cmake"
    duplicate = """SET(PROD_NEON_MICROKERNEL_SRCS
  src/f32-vbinary/gen/same.c)
SET(NON_PROD_NEON_MICROKERNEL_SRCS
  src/f32-vbinary/gen/same.c)
"""
    with pytest.raises(InventoryScanError, match="duplicate C microkernel"):
        parse_microkernel_manifest(duplicate, manifest_path)

    invalid = """SET(PROD_NEON_MICROKERNEL_SRCS
  ../outside.c)
SET(NON_PROD_NEON_MICROKERNEL_SRCS)
"""
    with pytest.raises(InventoryScanError, match="invalid C microkernel path"):
        parse_microkernel_manifest(invalid, manifest_path)


def test_scan_rejects_a_manifest_path_missing_from_the_pinned_tree(
    tmp_path: Path,
) -> None:
    parent, xnnpack, _pinned_commit = _fixture_repository(tmp_path)
    manifest = xnnpack / "cmake/gen/neon_microkernels.cmake"
    manifest.write_text(
        """SET(PROD_NEON_MICROKERNEL_SRCS
  src/f32-vbinary/gen/missing.c)
SET(NON_PROD_NEON_MICROKERNEL_SRCS)
""",
        encoding="utf-8",
    )
    changed_commit = _commit(xnnpack, "manifest references missing source")
    _git(
        parent,
        "update-index",
        "--cacheinfo",
        f"160000,{changed_commit},benchmark/XNNPACK",
    )
    _git(parent, "commit", "-m", "advance broken fixture pin")

    with pytest.raises(InventoryScanError, match="path absent"):
        scan_pinned_xnnpack(parent)
