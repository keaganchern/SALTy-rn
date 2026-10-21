Require Import isla.riscv64.riscv64 Reduction.RVV.RvvCachedSteps.
(* A bookkeeping marker: it carries no proof of P and adds no assumption. *)
Inductive guard_seen (P : Prop) : Prop := guard_seen_intro : guard_seen P.
Ltac freshGuard :=
  match goal with
  | HG : context [bv_signed _] |- _ =>
    let P := type of HG in
    lazymatch P with
    | guard_seen _ => fail
    | _ =>
      assert_fails (match goal with _ : guard_seen P |- _ => idtac end);
      first [solve [exfalso;
        repeat match goal with v : bv 65536 |- _ => clear dependent v end;
        bv_solve]
      | let marker := fresh "GUARD" in pose proof (guard_seen_intro P) as marker]
    end
  end.
Ltac freshCachedAStep := first [freshGuard | directCachedAStep].
