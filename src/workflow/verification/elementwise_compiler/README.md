# Elementwise Compiler

This package compiles an explicit Neon/RVV C pair into a content-addressed value
verification stack. It has no program catalogue. The caller supplies both C
paths, function names, target triples, facades, namespace, and output directory.

The generated chain is:

```text
Capabilities + mandatory ExternalCondition.json
             -> ProgramManifest -> Models.lean -> Spec.lean
             -> CrossPhaseAudit.json
             -> ProofTask.json -> Proof.lean -> Result.json

Models.lean + Spec.lean -> optional Counterexample.lean/json -> Result.json
```

`Models.lean` and `Spec.lean` are generated parents. `Spec.lean` is proof-free.
An agent may write only the designated `Proof.lean`; the checker validates the
frozen theorem type, protected closure, forbidden identifiers, transitive axioms,
toolchain identity, and every parent digest before publishing a result.

`ExternalCondition.json` is never omitted. In the XNNPACK corpus it follows a
unique registration to its registered parameter initializer and binds every
consulted file plus the pinned submodule commit. A standalone compilation instead
records that its generated claim is unconditional over all modeled parameters;
this does not claim that the theorem is true. A condition suggested by the
XNNPACK audit remains a **candidate** until the caller-to-kernel guarantee is
established. The proof gate rejects `required-missing`; a proof agent cannot
promote the candidate to an assumption.

Every compilation emits `CrossPhaseAudit.json`. For multi-phase programs the
generic compiler performs a deterministic bounded search over generated scalar
phase functions; a missing parameter domain is recorded as a separate blocker.
A found witness is emitted as
`Counterexample.lean` and checked by Lean before `Counterexample.json` is
published. The proof gate rejects a checked witness. Absence from this bounded
search is not a proof of phase equality.

Before proof delegation, a second generic bounded search compares the generated
`fNeon` and `fRvv` functions on a deterministic scalar edge corpus. A hit is
lifted to a concrete negation of `completeValueEquivalenceClaim`, checked with the
exact Lean toolchain, and published as a terminal counterexample. This search
currently exposes NaN-related disagreements in nine floating-point programs. A
miss remains only diagnostic and never becomes a proof.

After every program has an honest outcome, the result publisher validates the
artifact chain and copies the curated results into the checked-in result tree.

## Corpus refresh

From the repository root:

```sh
PYTHONPATH=src python3 -m workflow.verification.elementwise_compiler.corpus \
  --repository-root . \
  --output-directory build/verification/elementwise-compiler
```

The scanner discovers paired elementwise-shaped C functions structurally. The
current checked-in report contains nineteen scalar-lane pairs and one deferred
grouped complex pair. A lexical missing-intrinsic inventory is only a blocker
report; it is never presented as a semantic proof.

The report also distinguishes external conditions from intrinsic blockers. At
the current pinned XNNPACK revision, twelve programs need no external parameter
condition of this kind and eight quantized programs are `required-missing`.
`s8-vclamp` additionally has a Lean-checked direct cross-phase counterexample.

The current nineteen-program outcome set is two `verified(value)`, ten checked
counterexamples, and seven `external-condition-missing`. Nine counterexamples are
NaN-related floating-point disagreements. The remaining counterexample is the
`s8-vclamp` phase-order witness. These counts are derived from artifacts rather
than a program allowlist.

## Result publication

After proof and counterexample results are final, publish the curated result set:

```sh
PYTHONPATH=src python3 -m workflow.verification.elementwise_compiler.publish_results \
  --build-root build/verification/elementwise-compiler \
  --destination-root verification/elementwise-results
```

The publisher rejects incomplete, stale, missing, or extra artifacts and checks
the expected result counts and content hashes.

## Claim boundary

The current compiler targets arbitrary-length logical **value equality** relative
to the checked Lean intrinsic definitions. Scalar-lane layouts may have different
C types on different streams. The compiler does not yet establish complete C
memory behavior, legal overreads, aliasing, Arm/RISC-V ISA correspondence, or
compiled-binary correctness.
