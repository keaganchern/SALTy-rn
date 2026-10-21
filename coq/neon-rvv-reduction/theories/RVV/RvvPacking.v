From stdpp.bitvector Require Import bitvector.
Require Import Reduction.RVV.RvvDefs.

Definition push32 (x : bv 65536) (y : bv 32) : bv 65536 :=
  bv_or (bv_shiftl x (BV 65536 32)) (bv_zero_extend 65536 y).

Lemma get_push32_zero x y : bv_extract 0 32 (push32 x y) = y.
Proof.
  unfold push32. apply bv_eq.
  rewrite bv_extract_0_unsigned, bv_or_unsigned, bv_shiftl_unsigned,
    bv_zero_extend_unsigned by lia.
  change (bv_unsigned (BV 65536 32)) with 32%Z.
  apply Z.bits_inj_iff'; intros k Hk.
  destruct (decide (k < 32)%Z) as [Hlow|Hhigh].
  - rewrite bv_wrap_spec_low by lia. rewrite Z.lor_spec.
    rewrite bv_wrap_spec_low by lia. rewrite Z.shiftl_spec by lia.
    rewrite Z.testbit_neg_r by lia. reflexivity.
  - rewrite bv_wrap_spec_high by lia.
    symmetry. rewrite <- (bv_wrap_bv_unsigned _ y). apply bv_wrap_spec_high. lia.
Qed.

Lemma get_push32_next (i : N) x y : (i < 7)%N ->
  bv_extract (32 * (i+1)) 32 (push32 x y) = bv_extract (32*i) 32 x.
Proof.
  intros Hi. unfold push32. apply bv_eq.
  rewrite !bv_extract_unsigned, bv_or_unsigned, bv_shiftl_unsigned,
    bv_zero_extend_unsigned by lia.
  change (bv_unsigned (BV 65536 32)) with 32%Z.
  apply Z.bits_inj_iff'; intros k Hk.
  destruct (decide (k < 32)%Z) as [Hlow|Hhigh].
  - rewrite !bv_wrap_spec_low by lia.
    rewrite !Z.shiftr_spec by lia. rewrite Z.lor_spec.
    rewrite bv_wrap_spec_low by lia. rewrite Z.shiftl_spec by lia.
    rewrite <- (bv_wrap_bv_unsigned _ y).
    rewrite bv_wrap_spec_high by lia. rewrite orb_false_r. f_equal. lia.
  - rewrite !bv_wrap_spec_high by lia. reflexivity.
Qed.

Lemma pack8_lane (f : N -> bv 32) (i : N) : (i < 8)%N ->
  bv_extract (32*i) 32 (pack8 f) = f i.
Proof.
  intros Hi. assert (i=0 \/ i=1 \/ i=2 \/ i=3 \/ i=4 \/ i=5 \/ i=6 \/ i=7)%N as Hcases by lia.
  destruct Hcases as [H|[H|[H|[H|[H|[H|[H|H]]]]]]]; subst i.
  all: unfold pack8; fold push32.
  all: repeat first [rewrite (get_push32_next 6) by lia |
    rewrite (get_push32_next 5) by lia | rewrite (get_push32_next 4) by lia |
    rewrite (get_push32_next 3) by lia | rewrite (get_push32_next 2) by lia |
    rewrite (get_push32_next 1) by lia | rewrite (get_push32_next 0) by lia].
  all: try apply get_push32_zero.
  apply bv_eq. rewrite bv_extract_0_unsigned, bv_zero_extend_unsigned by lia.
  apply bv_wrap_bv_unsigned.
Qed.
Print Assumptions pack8_lane.
