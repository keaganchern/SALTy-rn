From stdpp.bitvector Require Import bitvector.
Require Import Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvLiterals.

Definition push8 (x : bv 65536) (y : bv 8) : bv 65536 :=
  bv_or (bv_shiftl x wide8) (bv_zero_extend 65536 y).

Lemma get_push8_zero x y : bv_extract 0 8 (push8 x y) = y.
Proof.
  unfold push8. apply bv_eq.
  rewrite bv_extract_0_unsigned, bv_or_unsigned, bv_shiftl_unsigned,
    bv_zero_extend_unsigned by lia.
  change (bv_unsigned wide8) with 8%Z.
  apply Z.bits_inj_iff'; intros k Hk.
  destruct (decide (k < 8)%Z) as [Hlow|Hhigh].
  - rewrite bv_wrap_spec_low by lia. rewrite Z.lor_spec.
    rewrite bv_wrap_spec_low by lia. rewrite Z.shiftl_spec by lia.
    rewrite Z.testbit_neg_r by lia. reflexivity.
  - rewrite bv_wrap_spec_high by lia.
    symmetry. rewrite <- (bv_wrap_bv_unsigned _ y). apply bv_wrap_spec_high. lia.
Qed.

Lemma get_push8_next (i : N) x y : (i < 31)%N ->
  bv_extract (8 * (i+1)) 8 (push8 x y) = bv_extract (8*i) 8 x.
Proof.
  intros Hi. unfold push8. apply bv_eq.
  rewrite !bv_extract_unsigned, bv_or_unsigned, bv_shiftl_unsigned,
    bv_zero_extend_unsigned by lia.
  change (bv_unsigned wide8) with 8%Z.
  apply Z.bits_inj_iff'; intros k Hk.
  destruct (decide (k < 8)%Z) as [Hlow|Hhigh].
  - rewrite !bv_wrap_spec_low by lia.
    rewrite !Z.shiftr_spec by lia. rewrite Z.lor_spec.
    rewrite bv_wrap_spec_low by lia. rewrite Z.shiftl_spec by lia.
    rewrite <- (bv_wrap_bv_unsigned _ y).
    rewrite bv_wrap_spec_high by lia. rewrite orb_false_r. f_equal. lia.
  - rewrite !bv_wrap_spec_high by lia. reflexivity.
Qed.

Local Opaque bv_or bv_shiftl bv_zero_extend.
Lemma pack32bytes_lane (f : N -> bv 8) (i : N) : (i < 8)%N ->
  bv_extract (8*i) 8 (pack32bytes f) = f i.
Proof.
  intros Hi.
  assert (i=0 \/ i=1 \/ i=2 \/ i=3 \/ i=4 \/ i=5 \/ i=6 \/ i=7)%N as Hcases by lia.
  destruct Hcases as [Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|Hcase]]]]]]]; subst i.
  all: unfold pack32bytes; fold push8.
  all: repeat first [rewrite (get_push8_next 30) by lia |
    rewrite (get_push8_next 29) by lia |
    rewrite (get_push8_next 28) by lia |
    rewrite (get_push8_next 27) by lia |
    rewrite (get_push8_next 26) by lia |
    rewrite (get_push8_next 25) by lia |
    rewrite (get_push8_next 24) by lia |
    rewrite (get_push8_next 23) by lia |
    rewrite (get_push8_next 22) by lia |
    rewrite (get_push8_next 21) by lia |
    rewrite (get_push8_next 20) by lia |
    rewrite (get_push8_next 19) by lia |
    rewrite (get_push8_next 18) by lia |
    rewrite (get_push8_next 17) by lia |
    rewrite (get_push8_next 16) by lia |
    rewrite (get_push8_next 15) by lia |
    rewrite (get_push8_next 14) by lia |
    rewrite (get_push8_next 13) by lia |
    rewrite (get_push8_next 12) by lia |
    rewrite (get_push8_next 11) by lia |
    rewrite (get_push8_next 10) by lia |
    rewrite (get_push8_next 9) by lia |
    rewrite (get_push8_next 8) by lia |
    rewrite (get_push8_next 7) by lia |
    rewrite (get_push8_next 6) by lia |
    rewrite (get_push8_next 5) by lia |
    rewrite (get_push8_next 4) by lia |
    rewrite (get_push8_next 3) by lia |
    rewrite (get_push8_next 2) by lia |
    rewrite (get_push8_next 1) by lia |
    rewrite (get_push8_next 0) by lia].
  all: apply get_push8_zero.
Qed.

Lemma loaded8_lane (vl : bv 64) old f (i : N) : (i < 8)%N ->
  bv_extract (8*i) 8 (loaded8 vl old f) =
  if decide (Z.of_N i < bv_unsigned vl)%Z then f i else bv_extract (8*i) 8 old.
Proof.
  intros Hi. unfold loaded8. apply pack32bytes_lane. exact Hi.
Qed.
Print Assumptions pack32bytes_lane.
Print Assumptions loaded8_lane.
