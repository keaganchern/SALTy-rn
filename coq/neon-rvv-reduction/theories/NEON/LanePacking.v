(* Checked lane decoding for packed NEON accumulator updates. *)
From stdpp.bitvector Require Import bitvector.
Require Import Reduction.NEON.NeonPairProof Reduction.NEON.NeonLaneBridge Reduction.NEON.TypeBridge.

Definition put16 (j : N) (acc : bv 128) (value : bv 16) : bv 128 :=
  bv_or (bv_and acc (bv_not (bv_shiftl (bv_zero_extend 128 (BV 16 65535)) (Z_to_bv 128 (16 * Z.of_N j)))))
        (bv_shiftl (bv_zero_extend 128 value) (Z_to_bv 128 (16 * Z.of_N j))).

Lemma get_put16 i j acc value :
  (i < 8)%N -> (j < 8)%N ->
  bv_extract (16*i) 16 (put16 j acc value) =
  if N.eqb i j then value else bv_extract (16*i) 16 acc.
Proof.
  intros Hi Hj. unfold put16.
  destruct (N.eqb_spec i j) as [->|Hne].
  all: apply bv_eq.
  all: rewrite !bv_extract_unsigned, bv_or_unsigned, bv_and_unsigned,
    bv_not_unsigned, !bv_shiftl_unsigned, !bv_zero_extend_unsigned by lia.
  all: rewrite !Z_to_bv_unsigned.
  all: rewrite (bv_wrap_small 128 (16 * Z.of_N j)) by (change (0 <= 16 * Z.of_N j < 340282366920938463463374607431768211456)%Z; lia).
  all: rewrite !bv_wrap_land.
  all: apply Z.bits_inj_iff'; intros k Hk.
  all: rewrite !Z.land_spec, !Z.shiftr_spec, !Z.lor_spec by lia.
  all: try rewrite !Z.lnot_spec by lia.
  all: try rewrite !Z.ones_spec by lia.
  all: destruct (decide (k < 16)%Z) as [Hlow|Hhigh].
  all: rewrite ?bool_decide_true by lia.
  all: rewrite ?bool_decide_false by lia.
  all: rewrite ?andb_false_r, ?andb_true_r.
  2: rewrite <-(bv_wrap_bv_unsigned _ value), bv_wrap_spec_high by lia; reflexivity.
  3: reflexivity.
  all: change (bv_unsigned (BV 16 65535)) with (Z.ones 16).
  all: repeat first [ rewrite Z.land_spec | rewrite Z.lnot_spec by lia |
    rewrite Z.shiftl_spec by lia | rewrite Z.ones_spec by lia ].
  all: rewrite ?bool_decide_true by lia.
  all: rewrite ?bool_decide_false by lia.
  all: cbn [andb orb negb].
  - rewrite andb_false_r, andb_true_r. cbn. f_equal. lia.
  - rewrite !(Z.ones_spec 128) by lia.
    rewrite !bool_decide_true by lia.
    rewrite !andb_true_r.
    destruct (N.lt_ge_cases i j) as [Hlt|Hge].
    + rewrite (Z.testbit_neg_r (Z.ones 16)) by lia.
      rewrite (Z.testbit_neg_r (bv_unsigned value)) by lia. cbn. rewrite andb_true_r, orb_false_r. reflexivity.
    + rewrite Z.ones_spec by lia. rewrite bool_decide_false by lia.
      rewrite <-(bv_wrap_bv_unsigned _ value), bv_wrap_spec_high by lia.
      cbn. rewrite andb_true_r, orb_false_r. reflexivity.
Qed.
Print Assumptions get_put16.

Definition pair_value16 (j : N) (acc src : bv 128) : bv 16 :=
  bv_add (bv_extract (16*j) 16 acc)
    (bv_add (bv_zero_extend 16 (bv_extract (16*j) 8 src))
            (bv_zero_extend 16 (bv_extract (16*j+8) 8 src))).

Lemma wrap128_of16 x : bv_wrap 128 (bv_wrap 16 x) = bv_wrap 16 x.
Proof.
  apply bv_wrap_small.
  pose proof (bv_wrap_in_range 16 x) as H.
  change (0 <= bv_wrap 16 x < 65536)%Z in H.
  change (0 <= bv_wrap 16 x < 340282366920938463463374607431768211456)%Z. lia.
Qed.

Lemma pair_update16_0 acc src :
  neon_pair_update 0 (BV 128 340282366920938463463374607431768145920) (BV 128 0) acc src =
  put16 0 acc (pair_value16 0 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_1 acc src :
  neon_pair_update 16 (BV 128 340282366920938463463374607427473309695) (BV 128 16) acc src =
  put16 1 acc (pair_value16 1 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_2 acc src :
  neon_pair_update 32 (BV 128 340282366920938463463374325961086468095) (BV 128 32) acc src =
  put16 2 acc (pair_value16 2 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_3 acc src :
  neon_pair_update 48 (BV 128 340282366920938463444928144833035370495) (BV 128 48) acc src =
  put16 3 acc (pair_value16 3 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_4 acc src :
  neon_pair_update 64 (BV 128 340282366920937254556001736876303056895) (BV 128 64) acc src =
  put16 4 acc (pair_value16 4 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_5 acc src :
  neon_pair_update 80 (BV 128 340282366841711509874929884467398967295) (BV 128 80) acc src =
  put16 5 acc (pair_value16 5 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_6 acc src :
  neon_pair_update 96 (BV 128 340277174703308091150010414528982941695) (BV 128 96) acc src =
  put16 6 acc (pair_value16 6 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma pair_update16_7 acc src :
  neon_pair_update 112 (BV 128 5192296858534827628530496329220095) (BV 128 112) acc src =
  put16 7 acc (pair_value16 7 acc src).
Proof.
  unfold neon_pair_update, put16, pair_value16.
  rewrite !extract_extended_byte.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of16. reflexivity.
Qed.

Lemma neon_uadalp8_all_lanes (i : N) acc src :
  (i < 8)%N ->
  bv_extract (16*i) 16 (neon_uadalp8_result acc src) = pair_value16 i acc src.
Proof.
  intros Hi.
  assert (i=0 \/ i=1 \/ i=2 \/ i=3 \/ i=4 \/ i=5 \/ i=6 \/ i=7)%N as Hcases by lia.
  destruct Hcases as [H|[H|[H|[H|[H|[H|[H|H]]]]]]]; subst i.
  all: unfold neon_uadalp8_result.
  all: rewrite !pair_update16_0, !pair_update16_1, !pair_update16_2, !pair_update16_3,
    !pair_update16_4, !pair_update16_5, !pair_update16_6, !pair_update16_7.
  all: unfold pair_value16.
  all: repeat (rewrite get_put16 by lia; cbn [N.eqb]).
  all: reflexivity.
Qed.
Print Assumptions neon_uadalp8_all_lanes.

Lemma neon_uadalp8_lane_as_word (i : N) acc src :
  (i < 8)%N ->
  (bv_unsigned (bv_extract (16*i) 16 acc) +
   bv_unsigned (bv_extract (16*i) 8 src) +
   bv_unsigned (bv_extract (16*i+8) 8 src) < 65536)%Z ->
  bv_zero_extend 32 (bv_extract (16*i) 16 (neon_uadalp8_result acc src)) =
  bv_add (bv_zero_extend 32 (bv_extract (16*i) 16 acc))
    (bv_add (bv_zero_extend 32 (bv_extract (16*i) 8 src))
            (bv_zero_extend 32 (bv_extract (16*i+8) 8 src))).
Proof.
  intros Hi Hbound. rewrite neon_uadalp8_all_lanes by exact Hi.
  unfold pair_value16. apply widen_pair_without_overflow. exact Hbound.
Qed.

Definition neon_byte_lanes (src : bv 128) : list (bv 8) :=
  [bv_extract 0 8 src; bv_extract 8 8 src; bv_extract 16 8 src; bv_extract 24 8 src; bv_extract 32 8 src; bv_extract 40 8 src; bv_extract 48 8 src; bv_extract 56 8 src; bv_extract 64 8 src; bv_extract 72 8 src; bv_extract 80 8 src; bv_extract 88 8 src; bv_extract 96 8 src; bv_extract 104 8 src; bv_extract 112 8 src; bv_extract 120 8 src].

Lemma neon_uadalp8_sum_as_words acc src :
  (forall i : N, (i < 8)%N ->
   (bv_unsigned (bv_extract (16*i) 16 acc) +
    bv_unsigned (bv_extract (16*i) 8 src) +
    bv_unsigned (bv_extract (16*i+8) 8 src) < 65536)%Z) ->
  sum32 (map (bv_zero_extend 32) (neon_u16_lanes (neon_uadalp8_result acc src))) =
  bv_add (sum32 (map (bv_zero_extend 32) (neon_u16_lanes acc)))
         (sum32 (map (bv_zero_extend 32) (neon_byte_lanes src))).
Proof.
  intros Hbound. unfold neon_u16_lanes, neon_byte_lanes, sum32. cbn [map fold_left].
  rewrite (neon_uadalp8_lane_as_word 0) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 1) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 2) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 3) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 4) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 5) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 6) by (try lia; apply Hbound; lia).
  rewrite (neon_uadalp8_lane_as_word 7) by (try lia; apply Hbound; lia).
  bv_simplify.
  repeat first [rewrite bv_wrap_add_idemp_l | rewrite bv_wrap_add_idemp_r].
  f_equal.
  repeat match goal with |- context [Z.of_N ?n] =>
    let v := eval vm_compute in (Z.of_N n) in change (Z.of_N n) with v end.
  ring.
Qed.
Print Assumptions neon_uadalp8_sum_as_words.
