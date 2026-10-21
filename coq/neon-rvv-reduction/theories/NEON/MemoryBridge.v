From stdpp.bitvector Require Import bitvector.
Require Import Reduction.NEON.BitsProof.

Lemma aligned16_mask (address : bv 64) :
  (bv_unsigned address mod 16 = 0)%Z -> bv_and address (BV 64 15) = BV 64 0.
Proof.
  intros H. apply bv_eq. rewrite bv_and_unsigned.
  change (Z.land (bv_unsigned address) (Z.ones 4) = 0)%Z.
  rewrite <- (bv_wrap_land 4). exact H.
Qed.

Lemma loaded_pair_concat (old : bv 128) (low high : bv 64) :
  bv_or (bv_and
    (bv_or (bv_and old (BV 128 0xffffffffffffffff0000000000000000))
      (bv_zero_extend 128 low)) (BV 128 0xffffffffffffffff))
    (bv_shiftl (bv_zero_extend 128 high) (BV 128 64)) =
  bv_concat 128 high low.
Proof.
  apply bv_eq.
  repeat (rewrite bv_or_unsigned || rewrite bv_and_unsigned).
  rewrite bv_shiftl_unsigned, !bv_zero_extend_unsigned, bv_concat_unsigned' by lia.
  cbn [bv_unsigned].
  rewrite Z.land_lor_distr_l, <- Z.land_assoc.
  change (Z.lor (Z.lor (Z.land (bv_unsigned old) 0)
    (Z.land (bv_unsigned low) (Z.ones 64)))
    (bv_wrap 128 (Z.shiftl (bv_unsigned high) 64)) =
    bv_wrap 128 (Z.lor (Z.shiftl (bv_unsigned high) 64) (bv_unsigned low))).
  rewrite Z.land_0_r, Z.lor_0_l, <- (bv_wrap_land 64), bv_wrap_bv_unsigned.
  rewrite wrap_lor, (bv_wrap_small 128 (bv_unsigned low)).
  - apply Z.lor_comm.
  - pose proof (bv_unsigned_in_range 64 low) as H.
    change (0 <= bv_unsigned low < 18446744073709551616)%Z in H.
    change (0 <= bv_unsigned low < 340282366920938463463374607431768211456)%Z. lia.
Qed.

Print Assumptions aligned16_mask.
Print Assumptions loaded_pair_concat.
