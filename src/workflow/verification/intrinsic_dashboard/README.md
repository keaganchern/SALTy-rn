# Intrinsic Verification Dashboard

This package is a local, read-only view of translation and review evidence. It
keeps four different records separate:

1. the 107 XNNPACK kernel-group labels in `kernels/xnnpack-kernel-families.csv`;
2. the 40 local SALTyRN source kernels and their available RVV target files;
3. exact Neon and RVV call-shaped intrinsic candidates used by those local files;
4. exact descriptor variants, case-scoped Lean mappings, and independent,
   hash-bound review attestations.

The intrinsic tables are local-only. XNNPACK generated sources are not scanned by
the live dashboard and cannot contribute a table row or related-program link. The
local scan strips C comments and literals and inventories direct call-shaped
tokens. It is not a typed C parser, header-resolution result, or intrinsic
semantic proof.

## Run

From the repository root:

```sh
python3 -m src.workflow.verification.intrinsic_dashboard.cli serve --check-lean
```

The server listens only on `http://127.0.0.1:8765/`. `--check-lean` first builds
each of the five generated proof targets with Lake file rehashing and remote-cache
downloads disabled. It then reads each designated theorem from Lean's checked
environment and applies the tracked theorem/contract policy. A passing result is
displayed only while both the complete Lean source/configuration digest and
proof-policy/checker digest remain unchanged.

The page's **Element-wise compiler puzzle** is a separate projection from
`verification/elementwise-compiler/CorpusReport.json`. Refresh its checked-in
inputs with:

```sh
PYTHONPATH=src python3 -m workflow.verification.elementwise_compiler.corpus \
  --repository-root . \
  --output-directory verification/elementwise-compiler
```

That projection verifies the complete content-addressed chain before showing
Manifest, Models, Spec, ProofTask, or Result progress. It does not read the legacy
`supported_cases` lists. Missing intrinsic spellings are puzzle dependencies;
changing one generated child marks the corresponding row stale.

For element-wise programs this projection is the sole production status
authority. Its API declares the structural discovery rule and
`legacy_case_lists_used: false`. The lower "Legacy proof prototypes" table keeps
older case-scoped records visible for historical comparison and for other kernel
families, but those rows do not determine element-wise compiler progress. A
checked-in held-out VMax regression compiles a new source pair, adds its generated
artifact index to a temporary report, and verifies that the page reaches
`proof-ready` without any dashboard program entry.

The tracked policy also pins the exact local Lean and Lake binaries, their
reported versions, the shared Lean runtime, and every importable `.olean` under
the selected Lean sysroot. The checker resolves absolute executables and removes
Lean/Lake/compiler and dynamic-loader overrides from the subprocess environment.
Before auditing tracked theorems, it copies the Lean sources without `.lake` and
performs a fresh build in a temporary root; repository build products are neither
trusted nor updated.
This initial identity is platform-specific (`arm64-apple-darwin`); another host
must add and independently review its own toolchain identity before it can report
a passing proof check.

Without `--check-lean`, proof checks are deliberately `not-run`:

```sh
python3 -m src.workflow.verification.intrinsic_dashboard.cli serve
python3 -m src.workflow.verification.intrinsic_dashboard.cli snapshot
```

Every browser poll reloads the registry, local C files, Lean artifacts, review
ledger, and activity records so current agent work appears without restarting the
server. The 107-row catalog is used only to assign concise kernel-group labels.

## Status Meaning

- `mapping present` / `automation configured` means at least one exact,
  case-scoped descriptor variant currently maps the spelling to backend/Lean
  code. It does not claim that every use of that spelling is supported.
- `approved` means every displayed descriptor variant has an independent review
  binding its descriptor digest and the complete current Lean/backend semantic
  TCB digest. Variants with different signatures, immediate constraints, operand
  lowering, or Lean targets never share an approval.
- `stale` means at least one bound identity, author, descriptor, or semantics
  digest changed after review.
- Each Neon/RVV file cell reports two counts. `Mapped x/y` means every displayed
  dependency has a case-scoped registry descriptor and Lean lowering;
  `Reviewed x/y` counts only independently reviewed C-intrinsic-to-Lean semantic
  mappings. A matching spelling from another, unconfigured case cannot satisfy a
  file dependency. Mapping completeness is not semantic approval.
- `Contract/spec artifact` means the designated policy contract exists and, for a
  generated-obligation case, its protected `Obligation.lean` also exists. A
  contract may be case-specific or shared, such as `Kernel/QS8/Params.lean`. A
  theorem can typecheck without a separate contract artifact, so a missing one
  does not by itself prevent compilation; it does lock final scope review.
- `Lean proof file` means the designated proof artifact for a known case exists.
- `Lean theorem check` requires an actual current `lake --rehash --no-cache
  build`, the pinned structurally encoded elaborated entry-theorem type and
  contract, a repository-wide forbidden-identifier scan, an allowed-axiom audit
  from Lean's checked environment, and one-side semantic mutation sensitivity.
  It is never inferred from file presence.
- `Scope review` is possible only after both intrinsic counts, deterministic model
  regeneration, spec, proof, and Lean check pass. It binds source, target, exact
  dependencies, generated model, contract, proof, claim scope, and proof-check
  attestation through one artifact digest.
- `selected-local-block` means only the generated local block and theorem were
  checked. It must never be read as complete C-function or ISA equivalence.
- `arbitrary-length-value` means the designated theorem quantifies over arbitrary
  logical input lengths. It still does not claim that complete C control flow,
  byte memory, pointer updates, aliasing, undefined behavior, or legal ISA traces
  have been connected to that value model.
- `complete-c-function` is reserved for a theorem with the explicit C-level
  contract and observation bridge. No current row has this scope.

The scope stored in a row is the policy target. The summary counts a layer only
when the row is schema-valid, its generated model and designated artifacts are
current, and the exact policy-bound Lean check passed in this run. Layers are
cumulative: an attested arbitrary-length theorem also counts as a checked local
value theorem. Starting the server without `--check-lean` leaves these achieved
counts at zero rather than inferring success from checked-in files.

Consequently, a row may have a present contract, proof file, and passing Lean
theorem while showing `0/n` Neon/RVV reviews. That state proves equality only of
the current Lean models. It does not yet establish that the models faithfully
denote the corresponding C intrinsic calls.

The initial tracked ledger at `verification/intrinsic-dashboard/reviews.json`
contains no approvals. The tracked reviewer policy at
`verification/intrinsic-dashboard/reviewers.json` is also initially empty. A
reviewer entry names the exact author groups it may review, for example:

```json
{
  "id": "reviewer-id",
  "display_name": "Reviewer name",
  "may_review_authors": ["saltyrn-lean-backend", "unassigned"]
}
```

Registry presence and earlier internal proof work are intentionally not promoted
to semantic review.

## Intrinsic Review

There is no bulk-approval command. One reviewer must explicitly acknowledge all
six checks and provide evidence:

```sh
python3 -m src.workflow.verification.intrinsic_dashboard.cli approve-intrinsic \
  --subject 'neon:vmaxq_s8@EXACT_VARIANT_SHA256' \
  --reviewer REVIEWER_ID \
  --ack-identity-signature \
  --ack-operand-order-types \
  --ack-value-semantics \
  --ack-fused-rounding-saturation \
  --ack-architectural-state \
  --ack-mutation-tests \
  --evidence notes/reviews/REVIEW_EVIDENCE.md
```

The subject id is shown in each spelling's variant details. Reviewer ids must
already exist in the tracked reviewer allowlist. Evidence must be an existing,
repository-relative file; the CLI records its SHA-256, so a URL or missing path
cannot serve as mutable evidence. Authoritative web or ISA sources should first
be recorded in a reviewed local evidence note with precise citations.

`architectural-state` includes relevant Neon state and, for RVV, the reviewed
scope of `vl`, masks, tail policy, `vxrm`, and `vxsat`. The fused/rounding check is
mandatory even when the reviewer records that it is inapplicable, specifically
to avoid silently identifying fused and separately rounded pipelines.

The artifact author cannot self-approve under the recorded identity. Directly
editing the ledger cannot introduce an unlisted reviewer because live state
validates it against the tracked allowlist. This remains a process and schema
control, not cryptographic identity authentication: reviewer configuration and
ledger changes still require independent code review.

After all gates pass:

```sh
python3 -m src.workflow.verification.intrinsic_dashboard.cli approve-file \
  --program-id qs8-vcvt \
  --reviewer REVIEWER_ID \
  --evidence notes/reviews/QS8_VCVT_SCOPE_REVIEW.md
```

## Agent Activity

Agents update their own runtime record atomically:

```sh
python3 -m src.workflow.verification.intrinsic_dashboard.cli activity \
  --agent-id translator-1 \
  --name "Translator 1" \
  --status running \
  --task "Implement one RVV descriptor" \
  --current-item __riscv_vadd_vv_i8m2 \
  --completed 2 --total 5
```

Runtime records live under `.intrinsic-dashboard/activity/` and are ignored by
Git. They report work; they do not grant review authority or change coverage.

## Claim Boundary

The dashboard reports lexical usage, configured descriptor variants, deterministic
generated-model freshness, Lean build results, claim scope, and review evidence.
For each configured generated case, freshness means that the current C inputs,
facades, resolved Clang binary/resource headers, and generator reproduce the
checked-in `Models.lean` byte-for-byte. Where a reviewed obligation profile is
configured, the same check also reproduces `Obligation.lean` byte-for-byte. The
freshness digest is part of the kernel artifact binding. A stale generated
artifact locks final review even when an older proof still typechecks.

The proof policy in `verification/intrinsic-dashboard/proof-policy.json` pins one
designated entry theorem per case and the current contract file where one exists.
The fixed `lean/ProofAudit.lean` program dynamically imports the target only after
the auditor itself has elaborated. It requires a theorem owned by that exact
module, reads it from Lean's checked environment, structurally serializes its
elaborated `Expr` type, and obtains its transitive axioms through
`Lean.CollectAxioms`. Output parsing is exact and fail-closed. This prevents target
command macros from forging a `#print axioms` transcript and avoids relying on a
pretty-printed or source-text theorem header. It is still a local policy control,
not a proof that every public theorem in the module has the intended API.

The policy digest binds the policy, full dashboard and Lean-backend Python source,
parse facades, fixed Lean auditor, Lean toolchain selector, Python producer, and
resolved Clang producer. Schema v3 fixes the complete Lean source/configuration
digest. Schema v4 additionally supports a proof-agent pilot: a case may explicitly
name one `candidate_proof_path` and one separately hashed `obligation`. The active
pilot applies this boundary to `qs8-vlrelu`; its designated theorem is in
`QS8VLReLU/CandidateProof.lean` while the generated claim remains in
`QS8VLReLU/Obligation.lean`. Only the
enumerated candidate path is omitted from the protected-project digest; models,
contracts, the obligation, other proofs, project configuration, and every other
Lean source remain protected. Cases without this pair remain fully protected.

The complete live Lean digest always includes candidate proofs. It is recorded in
each attestation and checked before and after every build and elaborated theorem
audit. The repository-wide forbidden-identifier scan also continues to inspect
candidate files. The fixed auditor loads the exact candidate module/theorem and
checks its elaborated type and transitive axioms against the policy. This lets a
reviewer accept changes confined to the named candidate without re-signing the
reviewed semantic inputs. Toolchain identity is recomputed from disk; it is not
accepted from `PATH` or a cached path-only lookup.

This policy is a review and accidental-change gate, not an OS security boundary.
It assumes that a trusted reviewer anchors the policy/checker and verifies that
the submitted diff changes only the named candidate. A process with write access
to the whole repository could also change the policy or race the in-place build;
fully adversarial proof generation requires a fresh read-only snapshot anchored
by the reviewer plus process isolation.

It does not establish that a Lean intrinsic definition is adequate to Arm ACLE or
the RISC-V V specification, that
a complete C kernel has been modeled, or that compiled Arm/RISC-V binaries are
equivalent. RVV review evidence must explicitly record the modeled scope of
`vl`, masks, tail policy, `vxrm`, and `vxsat` whenever relevant.
