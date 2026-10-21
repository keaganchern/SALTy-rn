Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvPackingShared Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvBytePackingShared Reduction.RVV.RvvLaneMath Reduction.RVV.RvvReduce.

Definition added_words (vl : bv 64) (acc src : bv 65536) : bv 65536 :=
  Reduction.RVV.RvvSharedDefs.pack8 (fun i => if decide (Z.of_N i < bv_unsigned vl)%Z
    then bv_add (bv_extract (32*i) 32 acc) (bv_extract (32*i) 32 src)
    else bv_extract (32*i) 32 acc).
Definition step_words (vl : bv 64) (acc old src : bv 65536) (f : N -> bv 8) : bv 65536 :=
  added_words vl acc (Reduction.RVV.RvvSharedDefs.widened8 vl old (Reduction.RVV.RvvLoadSharedDefs.loaded8 vl src f)).

Lemma pack8_ext (f g : N -> bv 32) :
  (forall i, (i < 8)%N -> f i = g i) -> Reduction.RVV.RvvSharedDefs.pack8 f = Reduction.RVV.RvvSharedDefs.pack8 g.
Proof.
  intros Hfg. unfold Reduction.RVV.RvvSharedDefs.pack8.
  rewrite (Hfg 0%N ltac:(lia)) (Hfg 1%N ltac:(lia)) (Hfg 2%N ltac:(lia)) (Hfg 3%N ltac:(lia)).
  rewrite (Hfg 4%N ltac:(lia)) (Hfg 5%N ltac:(lia)) (Hfg 6%N ltac:(lia)) (Hfg 7%N ltac:(lia)).
  reflexivity.
Qed.

Lemma step_words_as_prefix k vl acc old src f :
  bv_unsigned vl = Z.of_nat k ->
  step_words vl acc old src f =
  Reduction.RVV.RvvSharedDefs.pack8 (accumulate_prefix k (fun i => bv_extract (32*i) 32 acc) f).
Proof.
  intros Hk. unfold step_words, added_words. apply pack8_ext. intros i Hi.
  unfold accumulate_prefix.
  destruct (decide (Z.of_N i < bv_unsigned vl)%Z) as [Hactive|Htail].
  - rewrite decide_True; [|lia].
    unfold Reduction.RVV.RvvSharedDefs.widened8. rewrite (Reduction.RVV.RvvPackingShared.pack8_lane _ i Hi).
    rewrite decide_True; [|exact Hactive].
    rewrite (Reduction.RVV.RvvBytePackingShared.loaded8_lane vl src f i Hi).
    rewrite decide_True; [reflexivity|exact Hactive].
  - rewrite decide_False; [reflexivity|lia].
Qed.

Lemma sum_zero_seed acc :
  rvv_sum8_seed (BV 65536 0) acc = word_sum8 (fun i => bv_extract (32*i) 32 acc).
Proof.
  unfold rvv_sum8_seed, word_sum8. cbn [N.mul].
  assert (Hzero : bv_extract 0 32 (BV 65536 0) = BV 32 0)
    by (apply bv_eq; vm_compute; reflexivity).
  rewrite Hzero (bv_add_0_l (BV 32 0) (bv_extract 0 32 acc) eq_refl).
  rewrite <- !bv_add_assoc. reflexivity.
Qed.

Lemma step_words_sum k vl acc old src f :
  (k <= 8)%nat -> bv_unsigned vl = Z.of_nat k ->
  rvv_sum8_seed (BV 65536 0) (step_words vl acc old src f) =
  bv_add (rvv_sum8_seed (BV 65536 0) acc) (byte_sum_list (take k (byte_lanes8 f))).
Proof.
  intros Hbound Hk. rewrite (step_words_as_prefix k vl acc old src f Hk).
  rewrite shared_pack8_exact.
  rewrite reduction_of_packed_lanes (accumulate_prefix_sum k _ _ Hbound).
  rewrite sum_zero_seed. reflexivity.
Qed.
Print Assumptions step_words_as_prefix.
Print Assumptions step_words_sum.
