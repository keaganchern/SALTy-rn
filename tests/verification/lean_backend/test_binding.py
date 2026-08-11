from __future__ import annotations

import dataclasses
import json
import shutil
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from workflow.verification.lean_backend.binding import (
    ActiveLengthBindingError,
    ArtifactFreshnessError,
    CallBindingError,
    OperandProvenanceError,
    RegistryInventoryError,
    bind_kernel,
    build_manifest,
    canonical_json,
)
from workflow.verification.lean_backend.frontend import KernelExtraction, parse_kernel


ROOT = Path(__file__).resolve().parents[3]
NEON = ROOT / "kernels/source/qs8-vadd-minmax.c"
RVV = ROOT / "kernels/target/qs8-vadd-minmax.c"
FACADE = ROOT / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"


@contextmanager
def _source_mutation(
    original: Path,
    old: str,
    new: str,
    *,
    function_name: str,
) -> Iterator[KernelExtraction]:
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / original.name
        original_text = original.read_text(encoding="utf-8")
        if old not in original_text:
            raise AssertionError(f"mutation anchor is absent: {old!r}")
        source.write_text(original_text.replace(old, new, 1), encoding="utf-8")
        yield parse_kernel(source, function_name=function_name, facade=FACADE)


def _replace_argument(
    extraction: KernelExtraction,
    call_id: str,
    argument_index: int,
    **changes,
) -> KernelExtraction:
    calls = []
    for call in extraction.calls:
        if call.node_id != call_id:
            calls.append(call)
            continue
        arguments = list(call.arguments)
        arguments[argument_index] = dataclasses.replace(
            arguments[argument_index], **changes
        )
        dependencies = tuple(
            dict.fromkeys(
                dependency
                for argument in arguments
                for dependency in argument.dependencies
            )
        )
        calls.append(
            dataclasses.replace(
                call,
                arguments=tuple(arguments),
                dependencies=dependencies,
            )
        )
    return dataclasses.replace(extraction, calls=tuple(calls))


@unittest.skipUnless(shutil.which("clang"), "system clang is required")
class RegistryBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.neon = parse_kernel(NEON, facade=FACADE)
        cls.rvv = parse_kernel(RVV, facade=FACADE)

    def test_builds_deterministic_workspace_relative_manifest(self) -> None:
        first = build_manifest(self.neon, self.rvv, workspace_root=ROOT)
        second = build_manifest(self.neon, self.rvv, workspace_root=ROOT)
        first_json = canonical_json(first)

        self.assertEqual(first, second)
        self.assertEqual(first_json, canonical_json(second))
        self.assertNotIn(str(ROOT), first_json)
        self.assertEqual(first["registry"]["entry_count"], 43)
        self.assertEqual(
            first["registry"]["source"]["path"],
            "src/workflow/verification/lean_backend/registry.py",
        )
        self.assertRegex(first["registry"]["source"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            first["kernels"]["neon"]["inventory"]["registered_unique_count"],
            30,
        )
        self.assertEqual(
            first["kernels"]["rvv"]["inventory"]["registered_unique_count"],
            13,
        )
        self.assertEqual(
            first["kernels"]["neon"]["source"]["path"],
            "kernels/source/qs8-vadd-minmax.c",
        )
        self.assertEqual(
            first["kernels"]["rvv"]["source"]["path"],
            "kernels/target/qs8-vadd-minmax.c",
        )
        self.assertRegex(
            first["kernels"]["neon"]["source"]["preprocessed_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(
            first["kernels"]["neon"]["frontend"]["target_triple"],
            "aarch64-none-elf",
        )
        self.assertEqual(
            first["kernels"]["rvv"]["frontend"]["target_triple"],
            "riscv64-none-elf",
        )
        self.assertEqual(first["stage"]["name"], "registry-bound-syntax")
        self.assertIn(
            "C abstract-machine or CFG semantics",
            first["stage"]["does_not_establish"],
        )
        json.loads(first_json)

    def test_every_rvv_call_and_progress_update_uses_unique_vsetvl_result(self) -> None:
        manifest = build_manifest(self.neon, self.rvv, workspace_root=ROOT)
        schedule = manifest["kernels"]["rvv"]["schedule_binding"]

        self.assertEqual(schedule["unique_vsetvl_call"], "call_0000")
        self.assertEqual(schedule["active_length_value"], "vl@0")
        self.assertTrue(schedule["all_vector_calls_use_active_length"])
        self.assertEqual(
            set(schedule["progress_updates"]),
            {"input_a", "input_b", "output", "batch"},
        )

    def test_wrong_active_length_dependency_is_rejected(self) -> None:
        mutated = _replace_argument(
            self.rvv,
            "call_0008",
            3,
            dependencies=("batch@0",),
            source_text="batch",
        )

        with self.assertRaisesRegex(ActiveLengthBindingError, "final vl"):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_source_level_wrong_active_length_is_rejected(self) -> None:
        old = "__riscv_vmacc_vx_i32m8(vacc, b_multiplier, vxb32, vl)"
        new = "__riscv_vmacc_vx_i32m8(vacc, b_multiplier, vxb32, batch)"
        with _source_mutation(
            RVV, old, new, function_name="test_rvv"
        ) as extraction:
            with self.assertRaisesRegex(ActiveLengthBindingError, "final vl"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_wrong_rounding_immediate_is_rejected(self) -> None:
        mutated = _replace_argument(
            self.rvv,
            "call_0009",
            2,
            constant_value="__RISCV_VXRM_RDN",
            source_text="__RISCV_VXRM_RDN",
        )

        with self.assertRaisesRegex(CallBindingError, "call_0009"):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_source_level_wrong_rounding_mode_is_rejected(self) -> None:
        with _source_mutation(
            RVV,
            "__RISCV_VXRM_RNU",
            "__RISCV_VXRM_RDN",
            function_name="test_rvv",
        ) as extraction:
            with self.assertRaisesRegex(CallBindingError, "call_0009"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_truncating_immediate_cast_is_not_erased(self) -> None:
        with _source_mutation(
            RVV,
            "__RISCV_VXRM_RDN",
            "(unsigned _BitInt(1)) 2",
            function_name="test_rvv",
        ) as extraction:
            with self.assertRaisesRegex(OperandProvenanceError, "source operations"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_negated_scalar_intrinsic_argument_is_not_erased(self) -> None:
        old = "__riscv_vmul_vx_i32m8(vxa32, a_multiplier, vl)"
        new = "__riscv_vmul_vx_i32m8(vxa32, -a_multiplier, vl)"
        with _source_mutation(RVV, old, new, function_name="test_rvv") as extraction:
            with self.assertRaisesRegex(OperandProvenanceError, "source operations"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_truncating_scalar_intrinsic_argument_is_not_erased(self) -> None:
        old = "__riscv_vmul_vx_i32m8(vxa32, a_multiplier, vl)"
        new = "__riscv_vmul_vx_i32m8(vxa32, (int16_t) a_multiplier, vl)"
        with _source_mutation(RVV, old, new, function_name="test_rvv") as extraction:
            with self.assertRaisesRegex(OperandProvenanceError, "source operations"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_cast_around_vsetvl_result_is_not_erased(self) -> None:
        old = "size_t vl = __riscv_vsetvl_e8m2(batch);"
        new = "size_t vl = (uint8_t) __riscv_vsetvl_e8m2(batch);"
        with _source_mutation(RVV, old, new, function_name="test_rvv") as extraction:
            with self.assertRaisesRegex(ActiveLengthBindingError, "not assigned"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_cast_in_progress_update_is_not_erased(self) -> None:
        with _source_mutation(
            RVV,
            "input_a += vl;",
            "input_a += (uint8_t) vl;",
            function_name="test_rvv",
        ) as extraction:
            with self.assertRaisesRegex(ActiveLengthBindingError, "progress expression"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_extracted_argument_type_must_match_registry_type(self) -> None:
        mutated = _replace_argument(
            self.rvv,
            "call_0009",
            2,
            type_spelling="int",
        )

        with self.assertRaisesRegex(CallBindingError, "extracted type"):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_unbroadcast_requires_broadcast_dataflow_not_only_vector_type(self) -> None:
        mutated = _replace_argument(
            self.neon,
            "call_0018",
            1,
            dependencies=("vacc0123@0",),
            source_text="vacc0123",
        )

        with self.assertRaisesRegex(OperandProvenanceError, "not broadcast"):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_source_level_nonbroadcast_operand_is_rejected(self) -> None:
        old = (
            "vacc4567 = vmlaq_s32(vacc4567, "
            "vmovl_s16(vget_high_s16(vxb01234567)), vb_multiplier)"
        )
        new = (
            "vacc4567 = vmlaq_s32(vacc4567, "
            "vmovl_s16(vget_high_s16(vxb01234567)), vacc0123)"
        )
        with _source_mutation(
            NEON, old, new, function_name="test_neon"
        ) as extraction:
            with self.assertRaisesRegex(OperandProvenanceError, "not broadcast"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_negated_unbroadcast_checks_broadcast_input_syntax(self) -> None:
        calls = []
        for call in self.neon.calls:
            if call.node_id != "call_0004":
                calls.append(call)
                continue
            argument = dataclasses.replace(
                call.arguments[0], source_text="params->scalar.shift"
            )
            calls.append(dataclasses.replace(call, arguments=(argument,)))
        mutated = dataclasses.replace(self.neon, calls=tuple(calls))

        with self.assertRaisesRegex(OperandProvenanceError, "unary-negated"):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_bidirectional_inventory_rejects_missing_registered_spelling(self) -> None:
        mutated = dataclasses.replace(self.neon, calls=self.neon.calls[:-1])

        with self.assertRaises(RegistryInventoryError):
            bind_kernel(mutated, workspace_root=ROOT)

    def test_source_mutation_invalidates_previously_extracted_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "qs8-vadd-minmax.c"
            shutil.copyfile(NEON, source)
            extraction = parse_kernel(
                source,
                function_name="test_neon",
                facade=FACADE,
            )
            source.write_text(
                source.read_text(encoding="utf-8") + "\n/* mutation */\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ArtifactFreshnessError, "stale source"):
                bind_kernel(extraction, workspace_root=Path("/"))

    def test_pointer_progress_update_must_use_same_active_length(self) -> None:
        definitions = []
        for definition in self.rvv.definitions:
            if definition.variable == "output" and definition.definition_kind == "compound-+=":
                definitions.append(
                    dataclasses.replace(
                        definition,
                        dependencies=(definition.dependencies[0], "batch@0"),
                    )
                )
            else:
                definitions.append(definition)
        mutated = dataclasses.replace(self.rvv, definitions=tuple(definitions))

        with self.assertRaisesRegex(ActiveLengthBindingError, "output update"):
            bind_kernel(mutated, workspace_root=ROOT)


if __name__ == "__main__":
    unittest.main()
