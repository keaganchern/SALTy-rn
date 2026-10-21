(* Arithmetic interpretation of the exact NEON ISA result, with all source
   bytes symbolic. This does not assert a whole-kernel equivalence. *)
From stdpp.bitvector Require Import bitvector.
Require Import Reduction.NEON.NeonPairProof Reduction.NEON.TypeBridge Reduction.NEON.BitsProof.

Lemma wrap_land_pair n x y :
  bv_wrap n (Z.land x y) = Z.land (bv_wrap n x) (bv_wrap n y).
Proof.
  rewrite !bv_wrap_land. apply Z.bits_inj; intros i.
  rewrite !Z.land_spec.
  destruct (Z.testbit x i), (Z.testbit y i), (Z.testbit (Z.ones (Z.of_N n)) i); reflexivity.
Qed.

Lemma wrap_shift_above16 x k :
  (16 <= k)%Z -> bv_wrap 16 (Z.shiftl x k) = 0%Z.
Proof.
  intros H. rewrite Z.shiftl_mul_pow2 by lia.
  replace k with ((k-16)+16)%Z by lia.
  rewrite Z.pow_add_r by lia.
  unfold bv_wrap, bv_modulus. rewrite Z.mul_assoc. apply Z.mod_mul. lia.
Qed.

Lemma low16_keep_upper (acc mask value shift : bv 128) :
  bv_wrap 16 (bv_unsigned mask) = 65535%Z ->
  (16 <= bv_unsigned shift)%Z ->
  bv_extract 0 16 (bv_or (bv_and acc mask) (bv_shiftl value shift)) =
  bv_extract 0 16 acc.
Proof.
  intros Hmask Hshift. apply bv_eq.
  rewrite !bv_extract_0_unsigned, bv_or_unsigned, wrap_lor.
  rewrite bv_and_unsigned, wrap_land_pair, Hmask.
  rewrite bv_shiftl_unsigned, bv_wrap_bv_wrap by lia.
  rewrite wrap_shift_above16 by exact Hshift.
  rewrite Z.lor_0_r.
  change (Z.land (bv_wrap 16 (bv_unsigned acc)) (Z.ones 16) = bv_wrap 16 (bv_unsigned acc)).
  rewrite <- (bv_wrap_land 16). rewrite bv_wrap_bv_wrap by lia. reflexivity.
Qed.

Lemma low16_set_first (acc mask : bv 128) (value : bv 16) :
  bv_wrap 16 (bv_unsigned mask) = 0%Z ->
  bv_extract 0 16 (bv_or (bv_and acc mask) (bv_zero_extend 128 value)) = value.
Proof.
  intros Hmask. apply bv_eq.
  rewrite bv_extract_0_unsigned, bv_or_unsigned, wrap_lor.
  rewrite bv_and_unsigned, wrap_land_pair, Hmask, Z.land_0_r, Z.lor_0_l.
  rewrite bv_zero_extend_unsigned by lia.
  apply Z.mod_small. apply bv_unsigned_in_range.
Qed.

Lemma extract_extended_byte (b : bv 8) :
  bv_extract 0 16 (bv_zero_extend 128 b) = bv_zero_extend 16 b.
Proof. apply bv_eq. rewrite bv_extract_0_unsigned, !bv_zero_extend_unsigned by lia.
  apply Z.mod_small. pose proof (bv_unsigned_in_range 8 b) as H.
  change (0 <= bv_unsigned b < 256)%Z in H.
  change (0 <= bv_unsigned b < 65536)%Z. lia.
Qed.

Lemma neon_uadalp8_low16 acc src :
  bv_extract 0 16 (neon_uadalp8_result acc src) =
  bv_add (bv_extract 0 16 acc)
    (bv_add (bv_zero_extend 16 (bv_extract 0 8 src))
            (bv_zero_extend 16 (bv_extract 8 8 src))).
Proof.
  unfold neon_uadalp8_result, neon_pair_update. cbn zeta.
  repeat (rewrite low16_keep_upper; [|vm_compute; reflexivity|vm_compute; discriminate]).
  rewrite low16_set_first; [|vm_compute; reflexivity].
  rewrite !extract_extended_byte. reflexivity.
Qed.

Lemma neon_pair_to_word_without_overflow acc src :
  (bv_unsigned (bv_extract 0 16 acc) + bv_unsigned (bv_extract 0 8 src) +
    bv_unsigned (bv_extract 8 8 src) < 65536)%Z ->
  bv_zero_extend 32 (bv_extract 0 16 (neon_uadalp8_result acc src)) =
  bv_add (bv_zero_extend 32 (bv_extract 0 16 acc))
    (bv_add (bv_zero_extend 32 (bv_extract 0 8 src))
            (bv_zero_extend 32 (bv_extract 8 8 src))).
Proof. intros H. rewrite neon_uadalp8_low16. apply widen_pair_without_overflow. exact H. Qed.

Print Assumptions neon_uadalp8_low16.
Print Assumptions neon_pair_to_word_without_overflow.
