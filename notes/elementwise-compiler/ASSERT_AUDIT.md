# Local Assertion Audit

Audit date: 2026-08-29 (Asia/Seoul)  
Corpus: `kernels/source` and `kernels/target` at branch commit `3b7b37b`

## Scope and Counts

**Confirmed:** fourteen paired program names contain assertions below function-entry
control flow. Their Neon files contain 25 local assertion occurrences. Two matching
RVV files contain four occurrences, for 29 side-specific occurrences total.

**Confirmed:** twelve program pairs contain only assertions implied by an immediate
assignment or by the surrounding loop/branch arithmetic. Two pairs contain real
data-dependent non-null requirements on pointer-table elements.

| Program pair | Local assertion | Classification | Reason |
|---|---|---|---|
| `f32-argmaxpool` | `!ab`, `!ib` | derived invariant | both variables were just assigned `NULL` |
| `f32-conv-hwc2chw` | `iw < 4` | derived invariant | preceding loop continues while `iw >= 4` and subtracts 4 |
| `f32-dwconv-minmax` | `i0/i1/i2 != NULL` on both sides | data constraint | values come from the caller-supplied pointer table |
| `f32-dwconv2d-chw` | one-to-four-float remainder | derived invariant | positive aligned width; loop subtracts four floats while more than four remain |
| `f32-f16-vcvt` | one-to-three-float tail | derived invariant | four-float loop exit plus nonzero tail branch |
| `f32-igemm-minmax` | `a0 != NULL` on both sides | data constraint | value comes from the caller-supplied indirection table |
| `f32-raddstoreexpminusmax` | one-to-three-float tail | derived invariant | four-float loop exit plus nonzero tail branch |
| `qs8-f32-vcvt` | one-to-seven-byte tail | derived invariant | eight-byte loop exit plus nonzero tail branch |
| `qs8-rsum` | `1 <= batch < 2048` | derived invariant | 2048-byte loop exit plus nonzero tail branch |
| `qs8-vcvt` | one-to-seven-byte tail | derived invariant | eight-byte loop exit plus nonzero tail branch |
| `qs8-vlrelu` | one-to-seven-byte tail | derived invariant | eight-byte loop exit plus nonzero tail branch |
| `qu8-f32-vcvt` | one-to-seven-byte tail | derived invariant | eight-byte loop exit plus nonzero tail branch |
| `qu8-rdsum` | `1 <= channels <= 31` | derived invariant | 32-channel loop exit plus nonzero tail branch |
| `qu8-rsum` | `1 <= batch < 2048` | derived invariant | 2048-byte loop exit plus nonzero tail branch |

## Elementwise Phase-One Consequence

**Confirmed:** among the nineteen scalar-layout phase-one elementwise pairs, five
Neon files contain eleven local assertions: `f32-f16-vcvt`, `qs8-f32-vcvt`,
`qs8-vcvt`, `qs8-vlrelu`, and `qu8-f32-vcvt`. All eleven are derived tail-remainder
invariants. Their RVV partners contain no local assertions because RVV processes the
remaining active length directly.

**Proposal:** the fixed-tail recognizer consumes only local assertions matching its
derived remainder facts. Those facts include both the strict remainder range and
preserved element-size divisibility/alignment; `f32-f16-vcvt` exercises both. It
records matching assertions as automatically discharged. Any other local assertion
fails recognition instead of being silently erased or promoted to an entry
assumption. This is a family rule, not a per-program profile.

## Claim Boundary

The parse facade erases runtime `assert`, so a value theorem is about that pinned
assert-erased preprocessing context. Treating entry assertions as the shared caller
contract is an additional project policy. A debug-build theorem that observes
assertion failure would require explicit abort behavior and is outside phase one.
