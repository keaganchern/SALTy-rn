(* Composition of ISA-proved arithmetic result functions. This is not yet a
   Hoare proof of the intervening machine-code control flow. *)
From stdpp.bitvector Require Import bitvector.
Require Import Reduction.NEON.NeonProof Reduction.NEON.NeonPairProof Reduction.NEON.NeonWordProof Reduction.NEON.TypeBridge Reduction.NEON.LanePacking Reduction.NEON.WordPacking.

Lemma extract_extract n s l t m (v : bv n) :
  (s+l <= m)%N ->
  bv_extract s l (bv_extract t m v) = bv_extract (t+s) l v.
Proof.
  intros Hbound. apply bv_eq.
  rewrite !bv_extract_unsigned, !bv_wrap_land.
  apply Z.bits_inj_iff'; intros k Hk.
  repeat first [rewrite Z.land_spec | rewrite Z.shiftr_spec by lia |
                rewrite Z.ones_spec by lia].
  destruct (decide (k < Z.of_N l)%Z) as [Hlow|Hhigh].
  - rewrite !bool_decide_true by lia. rewrite !andb_true_r. f_equal. lia.
  - rewrite (bool_decide_false (k < Z.of_N l)%Z) by lia. rewrite !andb_false_r. reflexivity.
Qed.

Lemma neon_sum4_view v : neon_sum4 v = sum32 (neon_u32_lanes v).
Proof.
  unfold neon_sum4, sum32, neon_u32_lanes. cbn [fold_left].
  rewrite !extract_extract by lia.
  bv_simplify.
  repeat first [rewrite bv_wrap_add_idemp_l | rewrite bv_wrap_add_idemp_r].
  f_equal.
  repeat match goal with |- context [Z.of_N ?n] =>
    let z := eval vm_compute in (Z.of_N n) in change (Z.of_N n) with z end.
  ring.
Qed.

Definition neon_arithmetic_result (words halves bytes : bv 128) : bv 32 :=
  neon_sum4 (neon_uadalp16_result words (neon_uadalp8_result halves bytes)).

Definition reduction_block_spec (words halves bytes : bv 128) : bv 32 :=
  bv_add (sum32 (neon_u32_lanes words))
    (bv_add (sum32 (map (bv_zero_extend 32) (neon_u16_lanes halves)))
            (sum32 (map (bv_zero_extend 32) (neon_byte_lanes bytes)))).

Lemma neon_arithmetic_refines_block_spec words halves bytes :
  (forall i : N, (i < 8)%N ->
    (bv_unsigned (bv_extract (16*i) 16 halves) +
     bv_unsigned (bv_extract (16*i) 8 bytes) +
     bv_unsigned (bv_extract (16*i+8) 8 bytes) < 65536)%Z) ->
  neon_arithmetic_result words halves bytes = reduction_block_spec words halves bytes.
Proof.
  intros Hbound. unfold neon_arithmetic_result, reduction_block_spec.
  rewrite neon_sum4_view, neon_uadalp16_sum_as_words.
  rewrite neon_uadalp8_sum_as_words by exact Hbound. reflexivity.
Qed.

Print Assumptions neon_arithmetic_refines_block_spec.
