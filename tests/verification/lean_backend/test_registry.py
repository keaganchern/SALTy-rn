from __future__ import annotations

import dataclasses
import unittest

from workflow.verification.lean_backend.registry import (
    ArchitectureMismatchError,
    DuplicateIntrinsicError,
    I8,
    I32X4,
    INT,
    QS8_VADD_MINMAX_NEON_SPECS,
    QS8_VADD_MINMAX_REGISTRY,
    QS8_VADD_MINMAX_RVV_SPECS,
    QS8_VADD_MINMAX_SPECS,
    UnknownIntrinsicError,
    build_registry,
    lookup_intrinsic,
    resolve_call,
)
from workflow.verification.lean_backend.schema import (
    Architecture,
    ImmediateConstraintError,
    LeanArgument,
    NodeKind,
    OperandTransform,
    ScheduleNode,
    SchemaError,
    SemanticNode,
    SignatureMismatchError,
    StructuralNode,
    TypedOperand,
    VectorType,
)


EXPECTED_NEON = {
    "vcombine_s16",
    "vcombine_s8",
    "vdup_n_s8",
    "vdupq_n_s16",
    "vdupq_n_s32",
    "vdupq_n_s8",
    "vext_s8",
    "vget_high_s16",
    "vget_low_s16",
    "vget_low_s8",
    "vld1_s8",
    "vmax_s8",
    "vmaxq_s8",
    "vmin_s8",
    "vminq_s8",
    "vmlaq_s32",
    "vmovl_s16",
    "vmulq_s32",
    "vqaddq_s16",
    "vqmovn_s16",
    "vqmovn_s32",
    "vreinterpret_u16_s8",
    "vreinterpret_u32_s8",
    "vrshlq_s32",
    "vst1_lane_s8",
    "vst1_lane_u16",
    "vst1_lane_u32",
    "vst1_s8",
    "vst1q_s8",
    "vsubl_s8",
}

EXPECTED_RVV = {
    "__riscv_vle8_v_i8m2",
    "__riscv_vmacc_vx_i32m8",
    "__riscv_vmax_vx_i8m2",
    "__riscv_vmin_vx_i8m2",
    "__riscv_vmul_vx_i32m8",
    "__riscv_vnclip_wx_i16m4",
    "__riscv_vnclip_wx_i8m2",
    "__riscv_vsadd_vx_i16m4",
    "__riscv_vse8_v_i8m2",
    "__riscv_vsetvl_e8m2",
    "__riscv_vsext_vf2_i32m8",
    "__riscv_vssra_vx_i32m8",
    "__riscv_vwsub_vx_i16m4",
}


def operands_for(spec, constants=None):
    constants = constants or {}
    return tuple(
        TypedOperand(parameter.name, parameter.type, constants.get(index))
        for index, parameter in enumerate(spec.signature.parameters)
    )


class RegistryCompletenessTests(unittest.TestCase):
    def test_exact_kernel_scoped_inventory(self):
        neon = {spec.spelling for spec in QS8_VADD_MINMAX_NEON_SPECS}
        rvv = {spec.spelling for spec in QS8_VADD_MINMAX_RVV_SPECS}

        self.assertEqual(neon, EXPECTED_NEON)
        self.assertEqual(rvv, EXPECTED_RVV)
        self.assertEqual(len(QS8_VADD_MINMAX_SPECS), 43)
        self.assertEqual(set(QS8_VADD_MINMAX_REGISTRY), EXPECTED_NEON | EXPECTED_RVV)

    def test_architecture_and_node_kind_are_explicit(self):
        self.assertTrue(
            all(spec.architecture is Architecture.NEON for spec in QS8_VADD_MINMAX_NEON_SPECS)
        )
        self.assertTrue(
            all(spec.architecture is Architecture.RVV for spec in QS8_VADD_MINMAX_RVV_SPECS)
        )
        self.assertEqual(
            {spec.kind for spec in QS8_VADD_MINMAX_SPECS},
            {NodeKind.STRUCTURAL, NodeKind.SEMANTIC, NodeKind.SCHEDULE},
        )

    def test_semantic_entries_target_reviewed_salt_names(self):
        semantic = [spec for spec in QS8_VADD_MINMAX_SPECS if spec.kind is NodeKind.SEMANTIC]
        structural_or_schedule = [
            spec for spec in QS8_VADD_MINMAX_SPECS if spec.kind is not NodeKind.SEMANTIC
        ]

        self.assertTrue(semantic)
        self.assertTrue(all(spec.lean_name.startswith("SALT.Intrinsics.") for spec in semantic))
        self.assertTrue(all(spec.lean_name is None for spec in structural_or_schedule))

    def test_fixed_neon_and_scalable_rvv_shapes_are_distinct(self):
        neon_vector = lookup_intrinsic("vdupq_n_s8").signature.result
        rvv_vector = lookup_intrinsic("__riscv_vle8_v_i8m2").signature.result

        self.assertIsInstance(neon_vector, VectorType)
        self.assertEqual(neon_vector.fixed_lanes, 16)
        self.assertFalse(neon_vector.scalable)
        self.assertIsInstance(rvv_vector, VectorType)
        self.assertEqual(rvv_vector.lmul, "m2")
        self.assertTrue(rvv_vector.scalable)

    def test_existing_salt_normalizations_are_recorded(self):
        vmaxq = lookup_intrinsic("vmaxq_s8")
        self.assertEqual(vmaxq.lean_name, "SALT.Intrinsics.Neon.vmax_s8")
        self.assertEqual(vmaxq.lean_arguments[1].transform, OperandTransform.UNBROADCAST)

        neon_shift = lookup_intrinsic("vrshlq_s32")
        self.assertEqual(
            neon_shift.lean_arguments[1].transform,
            OperandTransform.NEGATED_UNBROADCAST_TO_NAT,
        )

        rvv_shift = lookup_intrinsic("__riscv_vssra_vx_i32m8")
        self.assertEqual(rvv_shift.lean_name, "SALT.Intrinsics.RVV.vssra_vx_rnu")
        self.assertEqual(
            tuple(argument.source_index for argument in rvv_shift.lean_arguments),
            (0, 1),
        )

    def test_semantic_operand_cannot_be_duplicated_or_omitted(self):
        vmacc = lookup_intrinsic("__riscv_vmacc_vx_i32m8")
        with self.assertRaisesRegex(
            SchemaError, "cover semantic C operands exactly once"
        ):
            dataclasses.replace(
                vmacc,
                lean_arguments=(
                    LeanArgument(0),
                    LeanArgument(1),
                    LeanArgument(0),
                ),
            )

    def test_constrained_immediate_can_remain_semantic(self):
        narrow = lookup_intrinsic("__riscv_vnclip_wx_i16m4")
        shift, mode = narrow.immediate_constraints
        semantic_shift = dataclasses.replace(
            narrow,
            immediate_constraints=(
                dataclasses.replace(shift, erased_from_semantics=False),
                mode,
            ),
            lean_arguments=(LeanArgument(0), LeanArgument(1)),
        )

        self.assertFalse(semantic_shift.immediate_constraints[0].erased_from_semantics)
        self.assertEqual(
            tuple(argument.source_index for argument in semantic_shift.lean_arguments),
            (0, 1),
        )


class FailClosedTests(unittest.TestCase):
    def test_unknown_lookup_is_exact_case_sensitive_and_untrimmed(self):
        for spelling in (
            "VADDQ_S8",
            " vmax_s8",
            "vmax_s8 ",
            "vmaxq_s16",
            "__riscv_vmax_vx_i8m1",
            "vmax",
        ):
            with self.subTest(spelling=spelling), self.assertRaises(UnknownIntrinsicError):
                lookup_intrinsic(spelling)

    def test_architecture_mismatch_is_rejected(self):
        with self.assertRaises(ArchitectureMismatchError):
            lookup_intrinsic("vmax_s8", Architecture.RVV)
        with self.assertRaises(ArchitectureMismatchError):
            lookup_intrinsic("__riscv_vmax_vx_i8m2", Architecture.NEON)

    def test_duplicate_spelling_is_rejected(self):
        entry = lookup_intrinsic("vmax_s8")
        with self.assertRaises(DuplicateIntrinsicError):
            build_registry((entry, entry))

    def test_signature_and_arity_mismatches_are_rejected(self):
        spec = lookup_intrinsic("vmulq_s32")
        good = operands_for(spec)
        self.assertIsInstance(resolve_call("vmulq_s32", good), SemanticNode)

        with self.assertRaises(SignatureMismatchError):
            resolve_call("vmulq_s32", good[:1])
        wrong_type = (
            TypedOperand("left", I32X4),
            TypedOperand("right", I8),
        )
        with self.assertRaises(SignatureMismatchError):
            resolve_call("vmulq_s32", wrong_type)

    def test_required_rounding_mode_is_enforced(self):
        spec = lookup_intrinsic("__riscv_vssra_vx_i32m8")
        self.assertIsInstance(
            resolve_call(spec.spelling, operands_for(spec, {2: 0})),
            SemanticNode,
        )
        signed_vxrm = list(operands_for(spec, {2: 0}))
        signed_vxrm[2] = TypedOperand("vxrm", INT, 0)
        with self.assertRaises(SignatureMismatchError):
            resolve_call(spec.spelling, tuple(signed_vxrm))
        with self.assertRaises(ImmediateConstraintError):
            resolve_call(spec.spelling, operands_for(spec, {2: 2}))
        with self.assertRaises(ImmediateConstraintError):
            resolve_call(spec.spelling, operands_for(spec))

    def test_narrowing_and_tail_immediates_are_enforced(self):
        narrow = lookup_intrinsic("__riscv_vnclip_wx_i16m4")
        self.assertIsInstance(
            resolve_call(narrow.spelling, operands_for(narrow, {1: 0, 2: 2})),
            SemanticNode,
        )
        with self.assertRaises(ImmediateConstraintError):
            resolve_call(narrow.spelling, operands_for(narrow, {1: 1, 2: 2}))

        lane_store = lookup_intrinsic("vst1_lane_s8")
        self.assertIsInstance(
            resolve_call(lane_store.spelling, operands_for(lane_store, {2: 0})),
            StructuralNode,
        )
        with self.assertRaises(ImmediateConstraintError):
            resolve_call(lane_store.spelling, operands_for(lane_store, {2: 1}))

    def test_node_variant_tracks_operation_class(self):
        load = lookup_intrinsic("vld1_s8")
        schedule = lookup_intrinsic("__riscv_vsetvl_e8m2")

        self.assertIsInstance(resolve_call(load.spelling, operands_for(load)), StructuralNode)
        self.assertIsInstance(
            resolve_call(schedule.spelling, operands_for(schedule)), ScheduleNode
        )


if __name__ == "__main__":
    unittest.main()
