From stdpp.bitvector Require Import bitvector.
Lemma vl_minus_one (vl : bv 64) :
  (bv_unsigned vl <= 8)%Z ->
  bv_signed (bv_sub (bv_zero_extend 128 vl) (BV 128 1)) = (bv_unsigned vl - 1)%Z.
Proof. intros Hvl. bv_simplify. apply bv_swrap_small.
  pose proof (bv_unsigned_in_range 64 vl).
  change (-170141183460469231731687303715884105728 <= bv_unsigned vl - 1 <
    170141183460469231731687303715884105728)%Z. lia.
Qed.
Print Assumptions vl_minus_one.
