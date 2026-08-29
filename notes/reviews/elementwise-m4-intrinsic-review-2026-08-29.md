# Elementwise M4 Intrinsic Review

Date: 2026-08-29 (Asia/Seoul)

## Scope

Read-only audit of the first nine shared F32 structural/schedule descriptors,
their generic lowering, held-out real-name compilation, official primary evidence,
and dashboard review bindings.

## First Verdict: NO-GO (8/9)

`vst1_lane_f32` allowed the official lane range `{0, 1}`, but
`_consume_little_endian_lane_store` always generated `.take 1`. A held-out source
using lane 1 therefore compiled while being modeled as lane 0.

## Correction

The lowering now requires an integer constant lane, computes
`offset = lane * width`, and selects `((value).drop offset).take width`. A lane-1
fixture checks that exact generated model; lane 2 is rejected by exact intrinsic
resolution. The descriptor continues to allow `{0, 1}`.

Intrinsic implementation hashes now cover `emit_lean.py` and `case_emit.py`, plus
the relevant Lean definition file for semantic/schedule capabilities. This binds
the context-specific lowering that exposed the bug.

## Convergence Verdict: GO (9/9)

The independent reviewer reran the real-name ProofTask and lane positive/negative
tests, checked that the legal set was not narrowed, and approved all nine exact
variants. The per-intrinsic review details are stored in the content-addressed
records under `verification/elementwise-compiler/intrinsic-reviews/`.

This verdict concerns the repository's Lean value model. It is not a complete C,
ISA-state, or compiled-binary correctness claim.
