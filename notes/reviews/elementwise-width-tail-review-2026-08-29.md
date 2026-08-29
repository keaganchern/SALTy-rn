# Elementwise Width and Tail Milestone Review

Date: 2026-08-29 (Asia/Seoul)

Reviewed state: `feat/elementwise-compiler`, base `939cfaa` plus the uncommitted
width/tail milestone.

## Verdict

**GO.** No blocker remains within the M1 scope.

## Confirmed Findings

- The new compiler path chooses behavior from parsed layout, control, widths, and
  typed intrinsic descriptors. The review found no new program-name, path, or
  case-id authority.
- Fixed-no-tail and fixed-tail generation carries 8/16/32-bit input/output widths
  through Models and Spec. The I32-to-I16 held-out pair exercises the complete
  `compile_pair -> ProofTask` path.
- Prefix-tail profiles require a complete descending power-of-two decomposition.
  Both accepted storage encodings are structurally checked and fail closed.
- A wide RVV loop cannot use byte-count `batch` directly as its element count. A
  separate count must have the exact parsed definition
  `count = batch / sizeof(T)`, with `T` matching the input stream.
- Multi-phase generation no longer silently maps the secondary block through the
  primary `fNeon`. It generates `fNeonSecondary`, maps the secondary block through
  it, and exposes `neonPhaseFunctionsEqualClaim` as a separate proof obligation.
- A golden test fixes one pre-existing integer descriptor digest across the new
  floating-type schema extension.

## Reproduced Checks

The reviewer ran 38 focused compiler, wide-generation, and intrinsic-index tests,
all passing. It also generated `s8-vclamp` and `qs8-vadd-minmax` in temporary
directories and inspected their phase-specific Models and Spec.

## Scope Reservation

The generated `neonPhaseFunctionsEqualClaim` is an explicit obligation, not a
proof that phases agree. The later counterexample/external-condition milestone
must decide this obligation and publish a terminal status. This review accepts M1
as honest width/tail generation; it does not claim the multi-phase condition gap
is already solved.
