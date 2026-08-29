# Elementwise M7 program outcome convergence review — 2026-08-29

Reviewer: agent `/root/program_review_convergence`

## Scope and approval boundary

**Confirmed.** This is an independent review of the exact recorded outcome for
each of the nineteen scalar-layout programs. Approval means that the repository
honestly records and binds each `verified(value)`, `counterexample`, or
`external-condition-missing` result. It does not turn a counterexample or blocked
program into an equivalence theorem.

**Confirmed.** The approved claim scope is the generated Lean value model only.
The dashboard keeps C abstract-machine correspondence and ISA/machine-code
correspondence at `not-established` for every row.

## Convergence checks

**Confirmed.** `ProgramReviewPlan.json` and `ProgramReviewChecks.json` have valid
self-digests and equal fresh recomputation from the live artifact graph. Their
current identities are:

- plan: `f3ab122c12f018563956932119d69a67c794eca0b70d4a61097730aaf2c233d6`
- checks: `a6fd17712b87ec3998b9cc90140fe3890b1d856f32e2a57e807118ad72977020`
- checks implementation: `3b77f3944ee6ac073c0f82a2c53c91d819339e53124f61692d0a7900fdd1a7b8`

The plan covers nineteen unique subjects with the exact split 8
`verified(value)` / 4 `counterexample` / 7 `external-condition-missing`. For all
nineteen subjects, an independent script checked the ArtifactIndex self-digest,
the plan-to-index raw hash, the manifest self-digest, Models and Spec raw hashes,
and the bound source and facade hashes. No mismatch was found.

**Confirmed.** All eight verified subjects bind a current frozen ProofTask, the
exact `Proof.lean`, a `Result.json`, the same start/end protected closure, the
current proof checker, and the pinned Lean toolchain. Every proof defines exactly
`completeValueEquivalence : completeValueEquivalenceClaim`; a comment/string-aware
scan found none of the proof policy's forbidden identifiers. The live proof
checker identity is
`469ac021841b5ec89202a377dc4e558ac2175a1bad6f2a0e58c9fa797fc9683c`.
A fresh temporary-copy `f32-vadd` proof check returned `verified(value)`, equal
start/end closure hashes, and the expected toolchain
`1ce7d3879378e751ecae7bb5fd76c57bde9e4957e69b20b4693d759eb34a8c6d`.

**Confirmed.** All four counterexample results bind the exact witness Lean file,
manifest, Models, Spec, live checker, toolchain, Result, and generated claim. The
three whole-program witnesses (`f32-vmax`, `f32-vmin`, `f32-vrndne`) prove a named
`completeValueEquivalenceCounterexample`; `s8-vclamp` proves a named
`neonPhaseFunctionsCounterexample`. The current whole-program and cross-phase
checker identities are respectively
`41244a5ae9e9aa5a7965053270d077d78b3e50ff088235cbf298275da09dc94e`
and
`bac2cca40d26df5f764accba1202d17ea3fe063c0800029aa65ae769438f9ff1`.
Fresh staged elaboration and axiom audits of `f32-vmax` and `s8-vclamp` accepted
only standard axioms plus the exact theorem-local `native_decide` axiom; neither
audit found an unrelated or user-declared axiom.

**Confirmed.** Each of the seven `external-condition-missing` directories records
`required-missing` and contains no ProofTask, Proof, Result, or counterexample
artifact. No proof agent assumption has been substituted for the missing external
condition.

**Confirmed.** The reusable intrinsic closure is complete for this program set:
180 used exact variants, 180 independently reviewed, and 180 Lean-checked.

**Confirmed.** A temporary publication of all nineteen review records loaded back
successfully and produced a website graph with 19 independently reviewed scalar
rows and the exact 8/4/7 outcome split. The separately deferred grouped-layout
`f32-vcmul` remains `layout-unrecognized` and is not counted among the nineteen.
All graph rows kept C and ISA at `not-established`.

**Confirmed.** Publisher and loader fail closed. In a temporary repository clone,
both accepted the unchanged nineteen-record baseline. Changing the live
whole-program counterexample checker caused both publisher and loader to reject
at `f32-vmax`; changing the live plan caused both to reject a stale plan before
accepting any review. The checks closure now includes the proof, whole-program
counterexample, cross-phase counterexample, schema, program-review, and graph
checker sources.

**Confirmed.** The final CLI boundary accepts the `argparse`-produced `Path` for
`--reviewer-report`, normalizes it to a safe repository-relative POSIX path, and
still rejects absolute paths or parent traversal. A real CLI publish in a
temporary repository clone returned `{"published": 19}`; it wrote nineteen
records and the strict loader accepted all nineteen. The live repository review
directory remained empty during this dry run.

**Confirmed.** The supplied focused evidence records `48 passed in 275.85s`.
Additionally, the program-review and web suites passed 22/22 during convergence,
the final program-review suite including the real CLI-`Path` regression passed
6/6, and the proof/counterexample spot checks above were run from temporary
staging roots without changing repository artifacts.

## Nineteen reviewed program outcomes

Each row below approves the integrity of the recorded outcome, subject to the
Lean-value-model boundary above.

| Program ID | Recorded outcome | Review conclusion |
|---|---|---|
| `f32-f16-vcvt` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vadd` | `verified(value)` | Exact binding accepted; proof was freshly spot-checked. |
| `f32-vdiv` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vlrelu` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vmax` | `counterexample` | Named whole-program witness accepted; this records non-equivalence. |
| `f32-vmin` | `counterexample` | Named whole-program witness accepted; this records non-equivalence. |
| `f32-vmul` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vmulc` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vrndne` | `counterexample` | Named whole-program witness accepted; this records non-equivalence. |
| `f32-vsqrt` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `f32-vsub` | `verified(value)` | Exact frozen proof/result binding accepted. |
| `qs8-f32-vcvt` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qs8-vadd-minmax` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qs8-vcvt` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qs8-vlrelu` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qs8-vmul-minmax-fp32` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qu8-f32-vcvt` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `qu8-vadd-minmax` | `external-condition-missing` | Honest blocked outcome accepted; no proof/result exists. |
| `s8-vclamp` | `counterexample` | Named cross-phase witness accepted; this records non-equivalence. |

Verdict: GO (19/19)
