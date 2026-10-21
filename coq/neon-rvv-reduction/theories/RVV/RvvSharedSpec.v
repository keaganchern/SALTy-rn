Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvLaneMath Reduction.NEON.KernelSpec Reduction.NEON.NeonTail.

(* The ISA-specific proofs can use different state representations while
   observing exactly the same mathematical result, including wraparound. *)
Lemma rvv_byte_sum_is_neon_byte_sum xs : byte_sum_list xs = byte_sum xs.
Proof.
  induction xs as [|x xs IH]; cbn [byte_sum_list byte_sum fold_right].
  - reflexivity.
  - unfold byte_sum_list in IH. rewrite IH. reflexivity.
Qed.

Lemma rvv_result_is_shared_spec initial xs :
  bv_add (byte_sum_list xs) initial = byte_reduction_spec initial xs.
Proof.
  rewrite rvv_byte_sum_is_neon_byte_sum. unfold byte_reduction_spec.
  bv_solve.
Qed.
Print Assumptions rvv_result_is_shared_spec.
