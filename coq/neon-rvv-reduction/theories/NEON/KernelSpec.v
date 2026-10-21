Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonKernel Reduction.NEON.NeonSequenceSpec Reduction.NEON.NeonTail Reduction.NEON.LanePacking Reduction.NEON.TypeBridge.

Definition flatten_blocks (bs : list (bv 64 * bv 64)) : list (bv 8) :=
  flat_map (fun b => neon_byte_lanes (bv_concat 128 (snd b) (fst b))) bs.
Definition byte_reduction_spec (initial : bv 32) (input : list (bv 8)) : bv 32 :=
  bv_add initial (byte_sum input).

Lemma flatten_blocks_length bs : length (flatten_blocks bs) = (16 * length bs)%nat.
Proof.
  induction bs as [|[lo hi] bs IH]; cbn [flatten_blocks flat_map length]; [reflexivity|].
  rewrite length_app. change (16 + length (flatten_blocks bs) = 16 * S (length bs))%nat.
  rewrite IH. lia.
Qed.

Lemma byte_sum_append xs ys : byte_sum (xs ++ ys) = bv_add (byte_sum xs) (byte_sum ys).
Proof.
  induction xs as [|x xs IH]; cbn [app byte_sum].
  - symmetry. apply bv_add_0_l. reflexivity.
  - rewrite IH. apply bv_add_assoc.
Qed.

Lemma byte_fold_acc xs acc :
  fold_left bv_add (map (bv_zero_extend 32) xs) acc = bv_add acc (byte_sum xs).
Proof.
  revert acc. induction xs as [|x xs IH]; intros acc; cbn [map fold_left byte_sum].
  - symmetry. apply bv_add_0_r. reflexivity.
  - rewrite IH. symmetry. apply bv_add_assoc.
Qed.

Lemma block_sum_flatten bs : block_sum bs = byte_sum (flatten_blocks bs).
Proof.
  induction bs as [|[lo hi] bs IH]; cbn [block_sum flatten_blocks flat_map fst snd].
  - reflexivity.
  - rewrite byte_sum_append. rewrite <- IH. f_equal.
    unfold byte_sum128, sum32. rewrite byte_fold_acc.
    apply bv_add_0_l. reflexivity.
Qed.

Lemma neon_kernel_output_is_byte_spec initial bs xs :
  bv_add initial (bv_add (block_sum bs) (byte_sum xs)) =
  byte_reduction_spec initial (flatten_blocks bs ++ xs).
Proof.
  unfold byte_reduction_spec. rewrite byte_sum_append. rewrite block_sum_flatten. reflexivity.
Qed.
Print Assumptions neon_kernel_output_is_byte_spec.
Print Assumptions flatten_blocks_length.
