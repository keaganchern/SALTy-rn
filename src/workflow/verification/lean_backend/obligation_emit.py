"""Deterministic Lean obligations for reviewed generated loop profiles."""

from __future__ import annotations

from .model_profiles import ModelProfile


def emit_unary_prefix_tail_obligation(profile: ModelProfile) -> str:
    """Emit the protected all-length claim for one unary prefix-tail model."""

    obligation = profile.unary_prefix_tail_obligation
    tail = profile.prefix_tail
    if obligation is None or tail is None or len(profile.inputs) != 1:
        raise ValueError(
            f"{profile.case_id} has no reviewed unary prefix-tail obligation"
        )
    overread_lanes = tail.load_lanes - 1
    return f"""import {profile.lean_namespace}.Models
import {obligation.contract_module}

namespace {profile.lean_namespace}

open {obligation.contract_namespace}

/-- Protected arbitrary-length value claim for the generated {obligation.display_name} models.

This claim does not establish C-memory validity, legal Neon overread, or RVV ISA
schedule adequacy. -/
def {obligation.claim_name}
    (p : {profile.parameter_type})
    (_hwf : {obligation.contract_predicate} p)
    (input overread : List (BitVec {obligation.element_width}))
    (_hOverread : {overread_lanes} <= overread.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) : Prop :=
  neonValueLoopWithOverreadFromIntrinsics p input overread =
    rvvValueLoopFromIntrinsics p input schedule

end {profile.lean_namespace}
"""


def emit_binary_prefix_tail_obligation(profile: ModelProfile) -> str:
    """Emit the protected all-length claim for one binary prefix-tail model."""

    obligation = profile.binary_prefix_tail_obligation
    tail = profile.prefix_tail
    if obligation is None or tail is None or len(profile.inputs) != 2:
        raise ValueError(
            f"{profile.case_id} has no reviewed binary prefix-tail obligation"
        )
    overread_lanes = tail.load_lanes - 1
    return f"""import {profile.lean_namespace}.Models
import {obligation.contract_module}

namespace {profile.lean_namespace}

open {obligation.contract_namespace}

/-- Protected arbitrary-length value claim for the generated {obligation.display_name} models.

This claim does not establish C-memory validity, legal Neon overread, or RVV ISA
schedule adequacy. -/
def {obligation.claim_name}
    (p : {profile.parameter_type})
    (_hwf : {obligation.contract_predicate} p)
    (inputA inputB overreadA overreadB : List (BitVec {obligation.element_width}))
    (sameLength : inputA.length = inputB.length)
    (_hOverreadA : {overread_lanes} <= overreadA.length)
    (_hOverreadB : {overread_lanes} <= overreadB.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition inputA.length) : Prop :=
  neonValueLoopWithOverreadFromIntrinsics p inputA inputB overreadA overreadB
      sameLength =
    rvvValueLoopFromIntrinsics p inputA inputB sameLength schedule

end {profile.lean_namespace}
"""
