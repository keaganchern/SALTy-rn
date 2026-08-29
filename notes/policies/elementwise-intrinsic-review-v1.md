# Elementwise Intrinsic Review Policy v1

An approved intrinsic review must bind one exact architecture, C spelling,
Clang function type, arity, canonical descriptor hash, and implementation hash.

The read-only reviewer checks:

1. the exact C signature and immediate range against a pinned primary Arm ACLE or
   RISC-V Vector C Intrinsics source file;
2. the descriptor operation, shape, lane order, widths, signedness, active-length
   operands, and immediate handling against that source;
3. the generic Lean emitter or named Lean definition used by the descriptor;
4. focused executable checks and, where applicable, Lean elaboration;
5. absence of program ids, path/name selection, axioms, and claim-scope promotion.

The reviewer may emit or reject a review record but may not modify the descriptor,
implementation, generated specification, or proof. Approval is evidence about the
repository's value model only; it does not establish complete C, ISA-state, or
compiled-binary correctness.
