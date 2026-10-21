From stdpp.bitvector Require Import bitvector.
Lemma advance_blocks (p : bv 64) (n : nat) :
  bv_add (bv_add p (BV 64 16)) (Z_to_bv 64 (16 * Z.of_nat n)) =
  bv_add p (Z_to_bv 64 (16 * Z.of_nat (S n))).
Proof.
  rewrite <- bv_add_assoc. f_equal. apply bv_eq. bv_simplify.
  rewrite Nat2Z.inj_succ.
  repeat first [rewrite bv_wrap_add_idemp_l | rewrite bv_wrap_add_idemp_r].
  f_equal. lia.
Qed.
Print Assumptions advance_blocks.
