(* Full lane interpretation of the NEON halfword-pair to word update. *)
From stdpp.bitvector Require Import bitvector.
Require Import Reduction.NEON.NeonWordProof Reduction.NEON.TypeBridge Reduction.NEON.NeonLaneBridge.

Definition put32 (j : N) (acc : bv 128) (value : bv 32) : bv 128 :=
  bv_or (bv_and acc (bv_not (bv_shiftl (bv_zero_extend 128 (BV 32 4294967295)) (Z_to_bv 128 (32 * Z.of_N j)))))
        (bv_shiftl (bv_zero_extend 128 value) (Z_to_bv 128 (32 * Z.of_N j))).

Lemma get_put32 i j acc value :
  (i < 4)%N -> (j < 4)%N ->
  bv_extract (32*i) 32 (put32 j acc value) =
  if N.eqb i j then value else bv_extract (32*i) 32 acc.
Proof.
  intros Hi Hj. unfold put32.
  destruct (N.eqb_spec i j) as [->|Hne].
  all: apply bv_eq.
  all: rewrite !bv_extract_unsigned, bv_or_unsigned, bv_and_unsigned,
    bv_not_unsigned, !bv_shiftl_unsigned, !bv_zero_extend_unsigned by lia.
  all: rewrite !Z_to_bv_unsigned.
  all: rewrite (bv_wrap_small 128 (32 * Z.of_N j)) by (change (0 <= 32 * Z.of_N j < 340282366920938463463374607431768211456)%Z; lia).
  all: rewrite !bv_wrap_land.
  all: apply Z.bits_inj_iff'; intros k Hk.
  all: rewrite !Z.land_spec, !Z.shiftr_spec, !Z.lor_spec by lia.
  all: try rewrite !Z.lnot_spec by lia.
  all: try rewrite !Z.ones_spec by lia.
  all: destruct (decide (k < 32)%Z) as [Hlow|Hhigh].
  all: rewrite ?bool_decide_true by lia.
  all: rewrite ?bool_decide_false by lia.
  all: rewrite ?andb_false_r, ?andb_true_r.
  2: rewrite <-(bv_wrap_bv_unsigned _ value), bv_wrap_spec_high by lia; reflexivity.
  3: reflexivity.
  all: change (bv_unsigned (BV 32 4294967295)) with (Z.ones 32).
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
    + rewrite (Z.testbit_neg_r (Z.ones 32)) by lia.
      rewrite (Z.testbit_neg_r (bv_unsigned value)) by lia. cbn. rewrite andb_true_r, orb_false_r. reflexivity.
    + rewrite Z.ones_spec by lia. rewrite bool_decide_false by lia.
      rewrite <-(bv_wrap_bv_unsigned _ value), bv_wrap_spec_high by lia.
      cbn. rewrite andb_true_r, orb_false_r. reflexivity.
Qed.
Print Assumptions get_put32.

Lemma extract_extended_halfword (b : bv 16) :
  bv_extract 0 32 (bv_zero_extend 128 b) = bv_zero_extend 32 b.
Proof. apply bv_eq. rewrite bv_extract_0_unsigned, !bv_zero_extend_unsigned by lia.
  apply Z.mod_small. pose proof (bv_unsigned_in_range 16 b) as H.
  change (0 <= bv_unsigned b < 65536)%Z in H.
  change (0 <= bv_unsigned b < 4294967296)%Z. lia.
Qed.

Definition pair_value32 (j : N) (acc src : bv 128) : bv 32 :=
  bv_add (bv_extract (32*j) 32 acc)
    (bv_add (bv_zero_extend 32 (bv_extract (32*j) 16 src))
            (bv_zero_extend 32 (bv_extract (32*j+16) 16 src))).

Lemma wrap128_of32 x : bv_wrap 128 (bv_wrap 32 x) = bv_wrap 32 x.
Proof.
  apply bv_wrap_small. pose proof (bv_wrap_in_range 32 x) as H.
  change (0 <= bv_wrap 32 x < 4294967296)%Z in H.
  change (0 <= bv_wrap 32 x < 340282366920938463463374607431768211456)%Z. lia.
Qed.

Lemma pair_update32_0 acc src :
  neon_pair32_update 0 (BV 128 340282366920938463463374607427473244160) (BV 128 0) acc src =
  put32 0 acc (pair_value32 0 acc src).
Proof.
  unfold neon_pair32_update, put32, pair_value32.
  rewrite !extract_extended_halfword.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of32. reflexivity.
Qed.

Lemma pair_update32_1 acc src :
  neon_pair32_update 32 (BV 128 340282366920938463444927863362353627135) (BV 128 32) acc src =
  put32 1 acc (pair_value32 1 acc src).
Proof.
  unfold neon_pair32_update, put32, pair_value32.
  rewrite !extract_extended_halfword.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of32. reflexivity.
Qed.

Lemma pair_update32_2 acc src :
  neon_pair32_update 64 (BV 128 340282366841710300967557013911933812735) (BV 128 64) acc src =
  put32 2 acc (pair_value32 2 acc src).
Proof.
  unfold neon_pair32_update, put32, pair_value32.
  rewrite !extract_extended_halfword.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of32. reflexivity.
Qed.

Lemma pair_update32_3 acc src :
  neon_pair32_update 96 (BV 128 79228162514264337593543950335) (BV 128 96) acc src =
  put32 3 acc (pair_value32 3 acc src).
Proof.
  unfold neon_pair32_update, put32, pair_value32.
  rewrite !extract_extended_halfword.
  cbn [N.eqb]. bv_simplify. rewrite ?Z.shiftl_0_r, ?wrap128_of32. reflexivity.
Qed.

Lemma neon_uadalp16_all_lanes (i : N) acc src :
  (i < 4)%N ->
  bv_extract (32*i) 32 (neon_uadalp16_result acc src) = pair_value32 i acc src.
Proof.
  intros Hi. assert (i=0 \/ i=1 \/ i=2 \/ i=3)%N as Hcases by lia.
  destruct Hcases as [H|[H|[H|H]]]; subst i.
  all: unfold neon_uadalp16_result.
  all: rewrite !pair_update32_0, !pair_update32_1, !pair_update32_2, !pair_update32_3.
  all: unfold pair_value32.
  all: repeat (rewrite get_put32 by lia; cbn [N.eqb]).
  all: reflexivity.
Qed.

Lemma neon_uadalp16_sum_as_words acc src :
  sum32 (neon_u32_lanes (neon_uadalp16_result acc src)) =
  bv_add (sum32 (neon_u32_lanes acc))
         (sum32 (map (bv_zero_extend 32) (neon_u16_lanes src))).
Proof.
  unfold neon_u32_lanes, neon_u16_lanes, sum32. cbn [map fold_left].
  rewrite (neon_uadalp16_all_lanes 0) by lia.
  rewrite (neon_uadalp16_all_lanes 1) by lia.
  rewrite (neon_uadalp16_all_lanes 2) by lia.
  rewrite (neon_uadalp16_all_lanes 3) by lia.
  unfold pair_value32. bv_simplify.
  repeat first [rewrite bv_wrap_add_idemp_l | rewrite bv_wrap_add_idemp_r].
  f_equal.
  repeat match goal with |- context [Z.of_N ?n] =>
    let v := eval vm_compute in (Z.of_N n) in change (Z.of_N n) with v end.
  ring.
Qed.
Print Assumptions neon_uadalp16_sum_as_words.
