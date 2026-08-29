from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.intrinsic_audit import (
    _architecture_conditions,
    _rvv_prototypes,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256
from workflow.verification.intrinsic_dashboard.elementwise_graph import (
    ElementwiseGraphError,
    build_elementwise_graph,
)
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
)


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"


def _spec(architecture: str, spelling: str):
    matches = [
        variant.spec
        for variant in CANONICAL_INTRINSIC_INDEX.variants
        if variant.spec.architecture.value == architecture
        and variant.spec.spelling == spelling
    ]
    assert len(matches) == 1
    return matches[0]


def test_checked_in_primary_source_audit_covers_exact_registry() -> None:
    audit = json.loads((CORPUS / "IntrinsicAudit.json").read_text(encoding="utf-8"))
    unsigned = dict(audit)
    assert unsigned.pop("audit_sha256") == canonical_sha256(unsigned)
    assert audit["schema_version"] == 2
    assert audit["counts"] == {
        "conditioned_variants": 23,
        "neon_variants": 108,
        "registry_variants": 189,
        "rvv_variants": 81,
        "used_variants": 180,
    }
    assert len({row["capability_id"] for row in audit["variants"]}) == 189
    for row in audit["variants"]:
        subject = {
            key: value
            for key, value in row.items()
            if key not in {"used", "programs", "audit_variant_sha256"}
        }
        assert row["audit_variant_sha256"] == canonical_sha256(subject)

    graph = build_elementwise_graph(CORPUS)
    assert graph["summary"]["primary_source_audited_intrinsic_variants"] == 189
    assert graph["summary"]["conditioned_intrinsic_variants"] == 23
    assert graph["summary"]["reviewed_used_intrinsic_variants"] == 180


def test_audit_exposes_exact_vshrn_immediates_and_fp_state_scope() -> None:
    audit = json.loads((CORPUS / "IntrinsicAudit.json").read_text(encoding="utf-8"))
    vshrn = next(row for row in audit["variants"] if row["spelling"] == "vshrn_n_u32")
    assert vshrn["immediate_constraints"] == [
        {
            "allowed_values": [13, 16],
            "argument_index": 1,
            "erased_from_semantics": False,
        }
    ]
    assert _architecture_conditions(_spec("neon", "vabsq_f32")) == ()
    assert _architecture_conditions(_spec("neon", "vbslq_f32")) == ()
    assert _architecture_conditions(_spec("rvv", "__riscv_vfsgnj_vv_f32m8")) == ()
    assert _architecture_conditions(_spec("rvv", "__riscv_vmfgt_vf_f32m8_b4")) == (
        "rvv.fflags-outside-value-claim",
    )
    assert "rvv.frm=RNE" in _architecture_conditions(
        _spec("rvv", "__riscv_vfcvt_x_f_v_i32m8")
    )


def test_rvv_primary_evidence_binds_exact_official_prototype() -> None:
    audit = json.loads((CORPUS / "IntrinsicAudit.json").read_text(encoding="utf-8"))
    rows = [row for row in audit["variants"] if row["architecture"] == "rvv"]
    assert len(rows) == 81
    for row in rows:
        evidence = row["primary_evidence"]
        assert evidence["path"] == "auto-generated/intrinsic_funcs.adoc"
        assert evidence["selector"] == row["spelling"]
        assert evidence["function_type"] == row["function_type"]
        assert row["spelling"] in evidence["prototype"]
        assert evidence["api_test_path"].startswith("auto-generated/api-testing/")


def test_rvv_prototype_parser_handles_wrapped_exact_types(tmp_path: Path) -> None:
    source = tmp_path / "intrinsic_funcs.adoc"
    source.write_text(
        "[,c]\n----\n"
        "vuint16m4_t __riscv_vnsrl_wx_u16m4(vuint32m8_t vs2,\n"
        "                                         size_t rs1, size_t vl);\n"
        "----\n",
        encoding="utf-8",
    )
    row = _rvv_prototypes(source)["__riscv_vnsrl_wx_u16m4"][0]
    assert row["argument_count"] == 3
    assert row["function_type"] == (
        "vuint16m4_t (vuint32m8_t, size_t, size_t)"
    )
    assert row["line"] == 3


def test_mutated_checked_in_audit_is_rejected_fail_closed(tmp_path: Path) -> None:
    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    path = copied / "IntrinsicAudit.json"
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit["variants"][0]["architecture_conditions"] = ["invented-condition"]
    path.write_text(json.dumps(audit), encoding="utf-8")

    with pytest.raises(ElementwiseGraphError, match="audit digest disagrees"):
        build_elementwise_graph(copied)


def test_published_scoped_reviews_require_checked_in_audit_and_plan(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    audit = copied / "IntrinsicAudit.json"
    audit.unlink()
    with pytest.raises(ElementwiseGraphError, match="require IntrinsicAudit"):
        build_elementwise_graph(copied)

    shutil.copy2(CORPUS / "IntrinsicAudit.json", audit)
    (copied / "IntrinsicReviewPlan.json").unlink()
    with pytest.raises(ElementwiseGraphError, match="require IntrinsicReviewPlan"):
        build_elementwise_graph(copied)
