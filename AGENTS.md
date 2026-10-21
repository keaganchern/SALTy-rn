# SaltyRN Project Memory Protocol

This repository is used for an ongoing research discussion about trustworthy,
unbounded verification of Neon-to-RVV translations.

## Read First

Before substantive work, read these files in order:

1. `notes/memory/PROJECT_STATE.md` for the current shared understanding.
2. `notes/memory/DECISIONS.md` for accepted defaults and superseded decisions.
3. `notes/memory/PLAN.md` for the active implementation plan and acceptance gates.
4. `notes/memory/DISCUSSION_LOG.md` for discussion history.
5. `notes/neon-to-lean-mapping.md` for the current frontend design analysis.

The original private project correspondence is intentionally not part of this
repository. Its relevant technical goals and decisions must be captured in the
memory files above before they are used as implementation requirements.

## Evidence Rules

- Label conclusions as **Confirmed**, **Inference**, or **Proposal**.
- A Lean theorem typechecks only relative to its Lean definitions. Do not call it
  a C/ISA correctness theorem unless a correspondence bridge has been established.
- Distinguish value semantics, full intrinsic semantics, C abstract-machine
  semantics, and machine-code semantics.
- Bind repository claims to a branch, commit, and audit date when possible.
- Prefer official Arm, RISC-V, Lean, LLVM/Clang, and XNNPACK sources for semantic
  claims. Record links near the claim.
- Treat the existing SMT shims and differential tests as engineering oracles, not
  automatically as part of the trusted computing base.

## Updating Memory

After a substantive analysis or implementation:

1. Update `notes/memory/PROJECT_STATE.md` in place so it remains concise and
   reflects the latest accepted understanding.
2. Update `notes/memory/PLAN.md` incrementally while implementation is active.
3. Record accepted or superseded choices in `notes/memory/DECISIONS.md`; do not
   silently rewrite a prior decision.
4. Append one dated entry to `notes/memory/DISCUSSION_LOG.md` with the question,
   conclusion, evidence, and unresolved points.
5. Move superseded claims into the log instead of leaving contradictions in the
   current state.
6. Do not store API keys, private credentials, personal paperwork, or unrelated
   conversation details.

Use Asia/Seoul dates. Keep the current-state file useful to a new agent in under
roughly 300 lines; detailed investigations belong in separate notes linked from it.
