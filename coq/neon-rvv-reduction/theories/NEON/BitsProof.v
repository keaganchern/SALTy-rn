From stdpp.bitvector Require Import bitvector.

Lemma wrap_lor n x y :
  bv_wrap n (Z.lor x y) = Z.lor (bv_wrap n x) (bv_wrap n y).
Proof.
  unfold bv_wrap, bv_modulus.
  rewrite <- !Z.land_ones by lia.
  apply Z.land_lor_distr_l.
Qed.

Lemma extract_packed_low32 (upper : bv 65536) (low : bv 32) :
  bv_extract 0 32 (bv_or (upper ≪ (BV 65536 32)) (bv_zero_extend 65536 low)) = low.
Proof.
  apply bv_eq.
  rewrite bv_extract_0_unsigned, bv_or_unsigned, wrap_lor.
  rewrite bv_shiftl_unsigned, bv_zero_extend_unsigned; [|lia].
  rewrite bv_wrap_bv_wrap; [|lia].
  change (Z.lor (bv_wrap 32 (bv_unsigned upper ≪ 32))
                (bv_wrap 32 (bv_unsigned low)) = bv_unsigned low).
  rewrite Z.shiftl_mul_pow2 by lia.
  unfold bv_wrap, bv_modulus at 1.
  rewrite Z.mod_mul by lia.
  rewrite Z.lor_0_l.
  apply Z.mod_small. apply bv_unsigned_in_range.
Qed.
