Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonLoop Reduction.NEON.NeonSequence Reduction.NEON.NeonEdges.

Lemma neon_loop_preserves_other_vectors bs q i :
  (3 <= i)%nat -> fold_neon bs q i = q i.
Proof.
  revert q. induction bs as [|[lo hi] bs IH]; intros q Hi; cbn [fold_neon]; [reflexivity|].
  rewrite (IH _ Hi). unfold after_load_pair.
  destruct i as [|[|[|i]]]; try lia; reflexivity.
Qed.

Lemma neon_kernel_preserves_other_vectors bs q i :
  (3 <= i)%nat -> q_reduced (fold_neon bs (q_init q)) i = q i.
Proof.
  intros Hi. unfold q_reduced.
  destruct i as [|i]; [lia|].
  rewrite (neon_loop_preserves_other_vectors bs (q_init q) (S i) Hi). reflexivity.
Qed.
Print Assumptions neon_kernel_preserves_other_vectors.
