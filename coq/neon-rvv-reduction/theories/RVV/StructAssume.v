Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.WholeStruct.
From iris.proofmode Require Import environments.

Section rules.
Context `{!islaG Σ} `{!threadG}.
Lemma assume_field_whole r f Φ ann :
  (find_in_context (FindRegMapsTo r) (λ rk,
    match rk with
    | RKMapsTo actual => ∃ value,
        ⌜read_accessor [Field f] actual = Some (RegVal_Base value)⌝ ∗
        (r ↦ᵣ actual -∗ Φ value)
    | RKCol _ => False
    end)) ⊢ WPaexp (AExp_Val (AVal_Var r [Field f]) ann) {{ Φ }}.
Proof.
  iDestruct 1 as (rk) "[Hr H]". destruct rk as [actual|regs]; simpl.
  - iDestruct "H" as (value Hread) "Hcont".
    iApply wpae_var_reg. iApply (read_reg_acc with "Hr"); [exact Hread|].
    iIntros "Hr". by iApply "Hcont".
  - by iDestruct "H" as %[].
Qed.
End rules.

Ltac kernelAStep := first [
  lazymatch goal with
  | |- envs_entails _ (wp_a_exp (AExp_Val (AVal_Var _ [Field _]) _) _) =>
      notypeclasses refine (tac_fast_apply (assume_field_whole _ _ _ _) _)
  end | demoAStep ].
Print Assumptions assume_field_whole.
