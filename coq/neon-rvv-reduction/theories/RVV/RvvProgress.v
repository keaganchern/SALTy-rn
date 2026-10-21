Require Import isla.riscv64.riscv64 Reduction.RVV.RvvSimpleVset.

Lemma selected_vl8_progress n :
  (0 < n)%Z -> (0 < selected_vl8 n <= n /\ selected_vl8 n <= 8)%Z.
Proof.
  intros Hn. unfold selected_vl8. repeat case_decide; try lia.
Qed.

Lemma rvv_remaining_strictly_decreases n :
  (0 < n)%Z -> (0 <= n - selected_vl8 n < n)%Z.
Proof. intros Hn. pose proof (selected_vl8_progress n Hn). lia. Qed.
Print Assumptions rvv_remaining_strictly_decreases.
