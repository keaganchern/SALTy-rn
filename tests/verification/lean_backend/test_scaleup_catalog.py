from __future__ import annotations

import re
import unittest
from pathlib import Path

from workflow.verification.lean_backend.profiles import FRONTEND_PROFILES
from workflow.verification.lean_backend.registry import QS8_VADD_MINMAX_REGISTRY
from workflow.verification.lean_backend.scaleup_catalog import (
    CATALOG_SCHEMA_LIMITATIONS,
    QS8_VCVT_CATALOG,
    QS8_VLRELU_CATALOG,
    QU8_VADD_MINMAX_CATALOG,
    S8_VCLAMP_CATALOG,
    SCALEUP_CATALOGS,
    VBOOL4,
)
from workflow.verification.lean_backend.schema import (
    Architecture,
    NodeKind,
    OperandTransform,
    SemanticIntrinsic,
    StructuralIntrinsic,
    StructuralOp,
    render_clang_function_type,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CALL_PATTERN = re.compile(r"\b(?:__riscv_[A-Za-z0-9_]+|v[A-Za-z0-9_]+)\s*\(")


def source_intrinsics(relative_path: str) -> set[str]:
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//.*", "", source)
    return {
        match.group(0).removesuffix("(").strip()
        for match in CALL_PATTERN.finditer(source)
    }


def spec(catalog, architecture: Architecture, spelling: str):
    result = catalog.registry[spelling]
    if result.architecture is not architecture:
        raise AssertionError(f"{spelling} has unexpected architecture")
    return result


class SourceInventoryTests(unittest.TestCase):
    def test_catalogs_cover_every_call_spelling_in_the_four_kernel_pairs(self):
        expected_counts = {
            "s8-vclamp": (16, 5),
            "qs8-vcvt": (14, 11),
            "qs8-vlrelu": (17, 13),
            "qu8-vadd-minmax": (25, 17),
        }

        self.assertEqual(set(SCALEUP_CATALOGS), set(expected_counts))
        for kernel_name, catalog in SCALEUP_CATALOGS.items():
            with self.subTest(kernel=kernel_name, architecture="neon"):
                actual = {entry.spelling for entry in catalog.neon_specs}
                self.assertEqual(
                    actual,
                    source_intrinsics(f"kernels/source/{kernel_name}.c"),
                )
                self.assertEqual(len(actual), expected_counts[kernel_name][0])
            with self.subTest(kernel=kernel_name, architecture="rvv"):
                actual = {entry.spelling for entry in catalog.rvv_specs}
                self.assertEqual(
                    actual,
                    source_intrinsics(f"kernels/target/{kernel_name}.c"),
                )
                self.assertEqual(len(actual), expected_counts[kernel_name][1])

    def test_catalog_signatures_match_the_reviewed_clang_profiles(self):
        for kernel_name, catalog in SCALEUP_CATALOGS.items():
            profile = FRONTEND_PROFILES[kernel_name]
            for architecture, entries, side in (
                (Architecture.NEON, catalog.neon_specs, profile.neon),
                (Architecture.RVV, catalog.rvv_specs, profile.rvv),
            ):
                expected = {
                    entry.spelling: (
                        entry.arity,
                        entry.function_type,
                    )
                    for entry in side.intrinsic_specs
                }
                actual = {
                    entry.spelling: (
                        len(entry.signature.parameters),
                        render_clang_function_type(entry.signature),
                    )
                    for entry in entries
                }
                with self.subTest(kernel=kernel_name, architecture=architecture.value):
                    self.assertEqual(actual, expected)

    def test_each_catalog_has_explicit_architecture_and_unique_spellings(self):
        for kernel_name, catalog in SCALEUP_CATALOGS.items():
            with self.subTest(kernel=kernel_name):
                self.assertTrue(
                    all(
                        entry.architecture is Architecture.NEON
                        for entry in catalog.neon_specs
                    )
                )
                self.assertTrue(
                    all(
                        entry.architecture is Architecture.RVV
                        for entry in catalog.rvv_specs
                    )
                )
                self.assertEqual(len(catalog.registry), len(catalog.specs))


class LoweringContractTests(unittest.TestCase):
    def test_existing_entries_are_reused_only_where_the_contract_is_unchanged(self):
        self.assertIs(
            spec(S8_VCLAMP_CATALOG, Architecture.NEON, "vdupq_n_s8"),
            QS8_VADD_MINMAX_REGISTRY["vdupq_n_s8"],
        )
        self.assertIs(
            spec(QS8_VCVT_CATALOG, Architecture.NEON, "vqaddq_s16"),
            QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"],
        )
        self.assertIs(
            spec(
                QS8_VLRELU_CATALOG,
                Architecture.RVV,
                "__riscv_vse8_v_i8m2",
            ),
            QS8_VADD_MINMAX_REGISTRY["__riscv_vse8_v_i8m2"],
        )
        self.assertIs(
            spec(QU8_VADD_MINMAX_CATALOG, Architecture.NEON, "vmulq_s32"),
            QS8_VADD_MINMAX_REGISTRY["vmulq_s32"],
        )

        self.assertIsNot(
            spec(S8_VCLAMP_CATALOG, Architecture.NEON, "vmaxq_s8"),
            QS8_VADD_MINMAX_REGISTRY["vmaxq_s8"],
        )
        self.assertIsNot(
            spec(
                QS8_VCVT_CATALOG,
                Architecture.RVV,
                "__riscv_vnclip_wx_i16m4",
            ),
            QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"],
        )
        self.assertIsNot(
            spec(QU8_VADD_MINMAX_CATALOG, Architecture.NEON, "vrshlq_s32"),
            QS8_VADD_MINMAX_REGISTRY["vrshlq_s32"],
        )

    def test_semantic_entries_name_definitions_exported_by_salt_intrinsics(self):
        definitions: dict[str, set[str]] = {}
        for architecture in ("Neon", "RVV"):
            source = (
                REPO_ROOT
                / "src/verification_bw/lean/SALT/Intrinsics"
                / f"{architecture}.lean"
            ).read_text(encoding="utf-8")
            definitions[architecture] = set(
                re.findall(r"^(?:def|abbrev)\s+([A-Za-z0-9_]+)\b", source, re.MULTILINE)
            )

        for catalog in SCALEUP_CATALOGS.values():
            for entry in catalog.specs:
                if not isinstance(entry, SemanticIntrinsic):
                    continue
                _, _, architecture, lean_spelling = entry.lean_name.split(".")
                with self.subTest(kernel=catalog.kernel_name, intrinsic=entry.spelling):
                    self.assertIn(lean_spelling, definitions[architecture])

    def test_vector_intrinsics_keep_vector_operands(self):
        exact_targets = {
            "vmaxq_s8": "SALT.Intrinsics.Neon.vmaxq_s8",
            "vminq_s8": "SALT.Intrinsics.Neon.vminq_s8",
            "vmax_s8": "SALT.Intrinsics.Neon.vmax_s8_vec",
            "vmin_s8": "SALT.Intrinsics.Neon.vmin_s8_vec",
        }
        for spelling, lean_name in exact_targets.items():
            entry = spec(S8_VCLAMP_CATALOG, Architecture.NEON, spelling)
            self.assertEqual(entry.lean_name, lean_name)
            self.assertEqual(
                tuple(argument.transform for argument in entry.lean_arguments),
                (OperandTransform.IDENTITY, OperandTransform.IDENTITY),
            )

        shift = spec(
            QU8_VADD_MINMAX_CATALOG,
            Architecture.NEON,
            "vrshlq_s32",
        )
        self.assertEqual(shift.lean_name, "SALT.Intrinsics.Neon.vrshlq_s32_vec")
        self.assertEqual(
            tuple(argument.transform for argument in shift.lean_arguments),
            (OperandTransform.IDENTITY, OperandTransform.IDENTITY),
        )

    def test_shift_and_rounding_operands_are_not_erased(self):
        cases = (
            (
                QS8_VCVT_CATALOG,
                Architecture.NEON,
                "vshlq_n_s16",
                (0, 1),
                ((1, frozenset({7})),),
            ),
            (
                QS8_VCVT_CATALOG,
                Architecture.RVV,
                "__riscv_vnclip_wx_i16m4",
                (0, 1, 2),
                ((1, frozenset({16})), (2, frozenset({0}))),
            ),
            (
                QS8_VLRELU_CATALOG,
                Architecture.RVV,
                "__riscv_vnclip_wx_i16m4",
                (0, 1, 2),
                ((1, frozenset({15})), (2, frozenset({0}))),
            ),
            (
                QU8_VADD_MINMAX_CATALOG,
                Architecture.RVV,
                "__riscv_vssra_vx_i32m8",
                (0, 1, 2),
                ((2, frozenset({0})),),
            ),
            (
                QU8_VADD_MINMAX_CATALOG,
                Architecture.RVV,
                "__riscv_vnclipu_wx_u8m2",
                (0, 1, 2),
                ((1, frozenset({0})), (2, frozenset({2}))),
            ),
        )
        for catalog, architecture, spelling, argument_indices, constraints in cases:
            entry = spec(catalog, architecture, spelling)
            with self.subTest(kernel=catalog.kernel_name, intrinsic=spelling):
                self.assertEqual(
                    tuple(argument.source_index for argument in entry.lean_arguments),
                    argument_indices,
                )
                self.assertEqual(
                    tuple(
                        (constraint.argument_index, constraint.allowed_values)
                        for constraint in entry.immediate_constraints
                    ),
                    constraints,
                )
                self.assertTrue(
                    all(
                        not constraint.erased_from_semantics
                        for constraint in entry.immediate_constraints
                    )
                )

    def test_mask_and_operation_classes_are_explicit(self):
        compare = spec(
            QS8_VLRELU_CATALOG,
            Architecture.RVV,
            "__riscv_vmslt_vx_i16m4_b4",
        )
        merge = spec(
            QS8_VLRELU_CATALOG,
            Architecture.RVV,
            "__riscv_vmerge_vxm_i16m4",
        )
        broadcast = spec(
            QS8_VLRELU_CATALOG,
            Architecture.RVV,
            "__riscv_vmv_v_x_i16m4",
        )

        self.assertEqual(compare.signature.result, VBOOL4)
        self.assertEqual(merge.signature.parameters[2].type, VBOOL4)
        self.assertEqual(VBOOL4.element.bit_width, 1)
        self.assertEqual(VBOOL4.lmul, "b4")
        self.assertIsInstance(broadcast, StructuralIntrinsic)
        self.assertEqual(broadcast.operation, StructuralOp.BROADCAST)

        for catalog in SCALEUP_CATALOGS.values():
            self.assertIn(NodeKind.SEMANTIC, {entry.kind for entry in catalog.specs})
            self.assertIn(NodeKind.STRUCTURAL, {entry.kind for entry in catalog.specs})
            self.assertIn(NodeKind.SCHEDULE, {entry.kind for entry in catalog.specs})

    def test_known_schema_limits_remain_visible(self):
        limitations = "\n".join(CATALOG_SCHEMA_LIMITATIONS)
        self.assertIn("vbool4_t", limitations)
        self.assertIn("vxrm", limitations)
        self.assertIn("vrshlq_s32", limitations)
        self.assertIn("mask", limitations)


if __name__ == "__main__":
    unittest.main()
