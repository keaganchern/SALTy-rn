# SaltyRN Active Plan

Last updated: 2026-10-02 (Asia/Seoul)

## Active Milestone

Prepare the `proof/sum` Coq reduction PR locally, including all selected completed
RVV instruction proofs alongside the complete NEON partial-correctness route.

- [x] Create an isolated branch/worktree from fork `origin/main@94e88f4`.
- [x] Include the selected roots' complete dependency closure, all 39 program
  instruction definitions/traces, and four NEON bridge traces.
- [x] Audit source migration for omitted dependencies or weakened statements.
- [x] Add `_CoqProject`, make/opam build inputs, portable extraction entry points,
  provenance checks and an explicit recursive object/assumption gate.
- [x] Reassemble both programs and compare every instruction with executable ELF
  bytes; regenerate selected traces from each group with identical hashes.
- [x] Complete a fresh compilation of all project sources.
- [x] Run recursive `coqchk` and the 35 exported theorem assumption reports.
- [x] Commit and publish `proof/sum`; keep the PR description local for review.

Dependency setup from an empty opam root remains a separate reproduction check.
Complete RVV program verification still requires load VL=2..8.

## Prior Lean Milestone

Build the first reproducible integer-only paired verification slice for current-main
`s8-vclamp`, without claiming that the C-to-IR bridge is already formally verified.

## Work Items

- [x] Establish project-state and chronological discussion memory.
- [x] Add a durable decision ledger and active-plan file.
- [x] Implement `ArtifactEnvelope`, typed feature tags, byte memory, contracts, and
  explicit observation in the Lean prototype.
- [x] Extract and audit the full Neon source and RVV target bodies fail-closed.
- [x] Emit deterministic source/target audit artifacts and complete audit manifests.
- [x] Prove the modeled Neon value schedule refines pointwise signed clamp.
- [x] Prove any positive partition and the abstract RVV progress policy refine clamp.
- [ ] Lower every audited AST construct into semantic `KernelIR`; replace all
  `AST_AUDIT_ONLY` exclusions with checked typed IR references.
- [x] Add function identity/range and local SSA use-order checks for the synthetic
  executable slice.
- [ ] Add per-entry lowering certificates and general CFG/dominance checks before
  interpreting arbitrary emitted control flow or accepting the real kernel.
- [ ] Connect real RVV `vsetvl`/intrinsic semantics to the abstract progress policy.
- [ ] Prove paired output-prefix equivalence and frame properties.
- [x] Add deterministic regeneration, unsupported-feature, signature, FP, and
  semantic-mutation checks for the audit extractor.
- [x] Complete the synthetic `s8-clamp16` generated semantic-IR E2E with direct
  operation interpretation, contract success, final-memory equality, frame/write-set
  theorems, and a supported semantic-mutation counterexample.
- [x] Add one local reproducibility command covering regeneration, frontend failures,
  Lean build, forbidden proof tokens, and exported-theorem axiom policy.
- [ ] Automate exported-theorem axiom checks and artifact-binding checks in CI.

## Immediate Next Steps

1. Replace the real `s8-vclamp` answer-shaped audit extractor with supported-subset
   normalization/lowering that emits semantic operations even for valid mutations.
2. Add structured 64/8/tail control and physical 8-byte tail reads, then reuse the
   generated interpreter proof for arbitrary batch and exact partial stores.
3. Add an actual RVV `vsetvl` bridge parameterized by VLEN/VLMAX; prove its traces are
   positive partitions instead of equating all positive partitions with ISA legality.
4. Automate digest regeneration, registry identity, `#print axioms`, coverage binding,
   and mutation checks in CI.

## Acceptance Gates

1. Both checked-in C files and their exact hashes/build context are named by the
   generated artifacts.
2. Every body statement, cast, call, and effect is consumed or extraction fails;
   reachable FP constructs always fail.
3. The theorem covers arbitrary input length satisfying the contract and arbitrary
   legal RVV progress schedules, not one test batch or VLEN.
4. Tail padding may be read but only the first `batch` output bytes may be written;
   all other observed memory is unchanged.
5. Lean builds with no `sorry`, `admit`, `unsafe`, custom axioms, or native decision
   axioms in exported theorems.
6. At least one supported semantic mutation lowers to different IR and exposes an
   inequivalence/counterexample; one unsupported-AST mutation fails extraction.

## Explicitly Deferred

- Float32 semantics and FP kernels.
- Complete Arm/RISC-V machine-state adequacy.
- A formally verified C parser or compiler frontend.
- Machine-code correctness.

## Next Kernel

After `s8-vclamp`, use current-main `qs8-vadd-minmax` to exercise widening,
rounding, saturation, two inputs, and richer parameter contracts.
