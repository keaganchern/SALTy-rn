Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvDefs Reduction.RVV.RvvPacking Reduction.RVV.RvvReduce.

Definition word_sum8 (f : N -> bv 32) : bv 32 :=
  bv_add (f 0%N) (bv_add (f 1%N) (bv_add (f 2%N) (bv_add (f 3%N)
    (bv_add (f 4%N) (bv_add (f 5%N) (bv_add (f 6%N) (f 7%N))))))).
Definition byte_sum_list (xs : list (bv 8)) : bv 32 :=
  fold_right (fun x acc => bv_add (bv_zero_extend 32 x) acc) (BV 32 0) xs.
Definition byte_lanes8 (f : N -> bv 8) : list (bv 8) :=
  [f 0%N; f 1%N; f 2%N; f 3%N; f 4%N; f 5%N; f 6%N; f 7%N].
Definition accumulate_prefix (k : nat) (acc : N -> bv 32) (bytes : N -> bv 8)
    (i : N) : bv 32 :=
  if decide (N.to_nat i < k)%nat then bv_add (acc i) (bv_zero_extend 32 (bytes i))
  else acc i.

Lemma reduction_of_packed_lanes (f : N -> bv 32) :
  rvv_sum8_seed (BV 65536 0) (pack8 f) = word_sum8 f.
Proof.
  unfold rvv_sum8_seed, word_sum8.
  assert (Hzero : bv_extract 0 32 (BV 65536 0) = BV 32 0) by (apply bv_eq; vm_compute; reflexivity).
  rewrite Hzero.
  rewrite (pack8_lane f 0 ltac:(lia)).
  rewrite (pack8_lane f 1 ltac:(lia)).
  rewrite (pack8_lane f 2 ltac:(lia)).
  rewrite (pack8_lane f 3 ltac:(lia)).
  rewrite (pack8_lane f 4 ltac:(lia)).
  rewrite (pack8_lane f 5 ltac:(lia)).
  rewrite (pack8_lane f 6 ltac:(lia)).
  rewrite (pack8_lane f 7 ltac:(lia)).
  bv_solve.
Qed.

Lemma accumulate_prefix_sum k acc bytes :
  (k <= 8)%nat ->
  word_sum8 (accumulate_prefix k acc bytes) =
  bv_add (word_sum8 acc) (byte_sum_list (take k (byte_lanes8 bytes))).
Proof.
  intros Hk.
  assert (k=0 \/ k=1 \/ k=2 \/ k=3 \/ k=4 \/ k=5 \/ k=6 \/ k=7 \/ k=8)%nat
    as Hcases by lia.
  destruct Hcases as [Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|Hcase]]]]]]]]; subst k.
  all: unfold word_sum8, accumulate_prefix, byte_sum_list, byte_lanes8.
  all: cbn [N.to_nat take fold_right].
  all: repeat case_decide; try lia.
  all: bv_solve.
Qed.

Lemma byte_sum_list_append xs ys :
  byte_sum_list (xs ++ ys) = bv_add (byte_sum_list xs) (byte_sum_list ys).
Proof.
  induction xs as [|x xs IH]; cbn [byte_sum_list fold_right app].
  - symmetry. apply bv_add_0_l. reflexivity.
  - unfold byte_sum_list in IH. rewrite IH. apply bv_add_assoc.
Qed.

Lemma byte_sum_list_split k xs :
  byte_sum_list xs = bv_add (byte_sum_list (take k xs)) (byte_sum_list (drop k xs)).
Proof.
  rewrite <- byte_sum_list_append. rewrite take_drop. reflexivity.
Qed.

Print Assumptions reduction_of_packed_lanes.
Print Assumptions accumulate_prefix_sum.
Print Assumptions byte_sum_list_split.
