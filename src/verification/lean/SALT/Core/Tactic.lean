/-
  Kernel-facing tactics over the CoreOp layer, centralising the CoreOp
  unfolds and cross-ISA lemmas that kernel bridge proofs need.
-/
import SALT.Core.Lane
import SALT.Core.CrossISA

namespace SALT.Core

open Lean.Parser.Tactic

/-- `simp_core_unfold [args]` runs `simp only` over the standard SALT.Core
    unfolds (lane combinators, family `*.eval`, `RoundingMode.apply`) plus
    the kernel-specific simp args in the bracket. -/

syntax "simp_core_unfold" ("[" simpLemma,* "]")? : tactic

macro_rules
  | `(tactic| simp_core_unfold) =>
    `(tactic| simp only [
        SALT.Core.lanewise, SALT.Core.lanewiseBin, SALT.Core.broadcast,
        SALT.Core.BVBinOp.eval, SALT.Core.BVExtOp.eval,
        SALT.Core.BVNarrowOp.eval, SALT.Core.BVShiftOp.eval,
        SALT.Core.RoundingMode.apply])
  | `(tactic| simp_core_unfold [$args,*]) =>
    `(tactic| simp only [
        SALT.Core.lanewise, SALT.Core.lanewiseBin, SALT.Core.broadcast,
        SALT.Core.BVBinOp.eval, SALT.Core.BVExtOp.eval,
        SALT.Core.BVNarrowOp.eval, SALT.Core.BVShiftOp.eval,
        SALT.Core.RoundingMode.apply, $args,*])

/-- `simp_cross_isa [args]` applies the cross-ISA lemma set over the CoreOp
    semantics. Kernels pass their local bound hypotheses (e.g.
    `h_shift_bound : p.shift.toNat ≤ 31`) in the bracket. -/
syntax "simp_cross_isa" ("[" simpLemma,* "]")? : tactic

macro_rules
  | `(tactic| simp_cross_isa) =>
    `(tactic| simp only [
        SALT.Core.CrossISA.roundShr_modes_equiv])
  | `(tactic| simp_cross_isa [$args,*]) =>
    `(tactic| simp only [
        SALT.Core.CrossISA.roundShr_modes_equiv, $args,*])

/-- `elem_equiv_tac [fns, hyps]` composes `simp_core_unfold` and
    `simp_cross_isa` into one pass for a kernel's `elem_equiv` proof.

    `BVShiftOp.eval` and `RoundingMode.apply` are deliberately excluded:
    the cross-ISA rounding-shift lemma is stated on the unreduced
    `(BVShiftOp.roundShr .neon).eval` form, so unfolding further would
    strand the goal at the primitive level where no lemma applies. -/
syntax "elem_equiv_tac" ("[" simpLemma,* "]")? : tactic

macro_rules
  | `(tactic| elem_equiv_tac) =>
    `(tactic| simp only [
        SALT.Core.lanewise, SALT.Core.lanewiseBin, SALT.Core.broadcast,
        SALT.Core.BVBinOp.eval, SALT.Core.BVExtOp.eval,
        SALT.Core.BVNarrowOp.eval,
        SALT.Core.CrossISA.roundShr_modes_equiv])
  | `(tactic| elem_equiv_tac [$args,*]) =>
    `(tactic| simp only [
        SALT.Core.lanewise, SALT.Core.lanewiseBin, SALT.Core.broadcast,
        SALT.Core.BVBinOp.eval, SALT.Core.BVExtOp.eval,
        SALT.Core.BVNarrowOp.eval,
        SALT.Core.CrossISA.roundShr_modes_equiv, $args,*])

end SALT.Core
