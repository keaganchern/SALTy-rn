# Elementwise Program Outcome Review Policy v1

An approved program review means an independent reviewer accepted the accuracy
and integrity of one generated program **outcome**.  It does not turn a failed,
blocked, or counterexample outcome into a correctness proof.

The reviewer must check that:

1. the source pair, manifest, generated Models and proof-free Spec are connected
   by the recorded content hashes;
2. the normalized entry condition and cross-phase audit are present and their
   status is reported without adding assumptions;
3. every used exact intrinsic variant has its own current independent review;
4. a `verified(value)` outcome binds the frozen ProofTask, the exact Proof.lean,
   the checker policy and toolchain, and an unchanged protected closure;
5. a `counterexample` outcome binds a Lean-checked concrete witness to a generated
   claim;
6. an `external-condition-missing` outcome has no proof task or accepted proof;
7. the dashboard presents value-model verification separately from C and ISA
   correspondence, which remain unestablished here.

Approval is fail-closed: any changed parent artifact, missing program, unbound
proof file, stale result, or mismatched review subject invalidates the review.

Concrete counterexamples may use Lean's `native_decide` evaluator. Their checker
must bind the exact Lean toolchain, accept only the theorem-local generated native
decision axiom, and reject every user-declared or unrelated axiom. This is a
toolchain-bound executable witness, not an axiom-free general proof.
