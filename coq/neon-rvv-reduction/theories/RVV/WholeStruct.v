(* Checked convenience rules for traces mixing whole-register and field
   accesses. Derived from Islaris lifting rules; no semantic changes. *)
Require Import isla.riscv64.riscv64.
From iris.proofmode Require Import environments.

Section rules.
Context `{!islaG Σ} `{!threadG}.

Lemma read_field_whole r f v ann es :
  find_in_context (FindRegMapsTo r) (λ rk,
    match rk with
    | RKMapsTo actual => ∃ field,
        ⌜read_accessor [Field f] v = Some field⌝ ∗
        ⌜read_accessor [Field f] actual = Some field⌝ ∗
        (r ↦ᵣ actual -∗ WPasm es)
    | RKCol _ => False
    end) ⊢ WPasm (ReadReg r [Field f] v ann :t: es).
Proof.
  iDestruct 1 as (rk) "[Hr H]". destruct rk as [actual|regs]; simpl.
  - iDestruct "H" as (field Hread Hactual) "Hcont".
    iApply (wp_read_reg _ _ field); [exact Hread|].
    iApply (read_reg_acc with "Hr"); [exact Hactual|].
    iIntros "Hr _". by iApply "Hcont".
  - by iDestruct "H" as %[].
Qed.

Lemma write_field_whole r f v ann es :
  find_in_context (FindRegMapsTo r) (λ rk,
    match rk with
    | RKMapsTo actual => ∃ field updated,
        ⌜read_accessor [Field f] v = Some field⌝ ∗
        ⌜write_accessor [Field f] actual field = Some updated⌝ ∗
        (r ↦ᵣ updated -∗ WPasm es)
    | RKCol _ => False
    end) ⊢ WPasm (WriteReg r [Field f] v ann :t: es).
Proof.
  iDestruct 1 as (rk) "[Hr H]". destruct rk as [actual|regs]; simpl.
  - iDestruct "H" as (field updated Hread Hwrite) "Hcont".
    by iApply (wp_write_reg_acc with "Hr Hcont").
  - by iDestruct "H" as %[].
Qed.
End rules.

Ltac demoAStep := first [
  lazymatch goal with
  | |- envs_entails _ (WPasm (ReadReg _ [Field _] _ _ :t: _)) =>
      notypeclasses refine (tac_fast_apply (read_field_whole _ _ _ _ _) _)
  | |- envs_entails _ (WPasm (WriteReg _ [Field _] _ _ :t: _)) =>
      notypeclasses refine (tac_fast_apply (write_field_whole _ _ _ _ _) _)
  end | liAStep ].
