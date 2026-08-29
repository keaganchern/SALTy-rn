# Elementwise Compiler Memory Protocol

This directory is the branch-local source of truth for
`feat/elementwise-compiler`.

Read in this order before substantive work:

1. `PROJECT_STATE.md` — current facts, scope, and immediate gap.
2. `DECISIONS.md` — accepted architectural constraints; append, do not rewrite.
3. `PLAN.md` — active milestones, exit gates, and next executable slice.
4. `../elementwise-compiler/ARCHITECTURE.md` — stable system and artifact design.
5. `DISCUSSION_LOG.md` — chronological rationale and superseded discussion.

## File Responsibilities

- `PROJECT_STATE.md` stays below roughly 250 lines and describes only current
  truth. Move history into `DISCUSSION_LOG.md`.
- `DECISIONS.md` is append-only. Supersede an earlier decision explicitly.
- `PLAN.md` contains only active or upcoming work plus completed milestone gates.
  Do not turn it into a historical task dump.
- `DISCUSSION_LOG.md` is append-only and may grow.
- The dashboard and generated manifests own live coverage counts. Memory records
  only audited snapshots with a commit and date; it does not manually duplicate
  changing program/intrinsic status.

## Update Rule

After substantive implementation or analysis:

1. update current facts in `PROJECT_STATE.md`;
2. advance exactly one active milestone in `PLAN.md`;
3. append a decision only if an architectural choice was accepted or superseded;
4. append one dated discussion-log entry with question, conclusion, evidence, and
   unresolved points;
5. label claims **Confirmed**, **Inference**, or **Proposal**;
6. bind repository claims to branch, commit, and Asia/Seoul date.

Generated files, build outputs, API keys, credentials, and unrelated personal
information do not belong in memory.
