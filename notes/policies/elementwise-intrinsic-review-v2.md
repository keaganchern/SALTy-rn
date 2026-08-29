# Elementwise Intrinsic Review Policy v2

An approval covers one exact value-model subject. It binds architecture, C
spelling, Clang function type and arity, canonical descriptor hash, implementation
hash, primary-source audit-variant hash, claim scope, and every stated architecture
condition. A family batch may share evidence and executable checks, but never an
approval identity.

The read-only reviewer checks:

1. the exact C signature and legal immediate set against pinned Arm ACLE or
   RISC-V Vector C Intrinsics evidence;
2. the operation, operand order, lane widths, signedness, lane order, active
   length, immediate handling, and architecture-state conditions against pinned
   primary architecture evidence;
3. the generic structural emitter or named Lean definition bound by the subject;
4. family-specific executable checks, including adversarial edge cases where the
   operation has lane, rounding, saturation, NaN, signed-zero, conversion, or
   implicit-state behavior;
5. that the claim remains Lean value semantics only and does not silently claim
   complete C abstract-machine, ISA-state, or compiled-binary correctness.

The reviewer rejects the whole affected family when a new subject is unclassified,
the evidence selector is absent, a condition is implicit, a required negative test
is missing, or an exact digest has changed. The reviewer may approve records but
may not modify descriptors, semantics, generated specifications, or proofs.
