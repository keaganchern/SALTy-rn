# Elementwise Compiler

This package compiles an explicit Neon/RVV C pair into a content-addressed value
verification stack. It has no program catalogue. The caller supplies both C
paths, function names, target triples, facades, namespace, and output directory.

The generated chain is:

```text
Capabilities -> ProgramManifest -> Models.lean -> Spec.lean
             -> ProofTask.json -> Proof.lean -> Result.json
```

`Models.lean` and `Spec.lean` are generated parents. `Spec.lean` is proof-free.
An agent may write only the designated `Proof.lean`; the checker validates the
frozen theorem type, protected closure, forbidden identifiers, transitive axioms,
toolchain identity, and every parent digest before publishing a result.

## Corpus refresh

From the repository root:

```sh
PYTHONPATH=src python3 -m workflow.verification.elementwise_compiler.corpus \
  --repository-root . \
  --output-directory verification/elementwise-compiler
```

The scanner discovers paired elementwise-shaped C functions structurally. The
current checked-in report contains nineteen scalar-lane pairs and one deferred
grouped complex pair. A lexical missing-intrinsic inventory is only a blocker
report; it is never presented as a semantic proof.

## Claim boundary

The current compiler targets arbitrary-length logical **value equality** relative
to the checked Lean intrinsic definitions. Scalar-lane layouts may have different
C types on different streams. The compiler does not yet establish complete C
memory behavior, legal overreads, aliasing, Arm/RISC-V ISA correspondence, or
compiled-binary correctness. The dashboard displays those layers separately.
