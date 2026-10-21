Require Import isla.riscv64.riscv64 Reduction.RVV.RvvTaggedResume Reduction.RVV.RvvFreshGuard Reduction.RVV.RvvTaggedCache.
Ltac freshGuard ::=
  match goal with
  | HG : ?P |- _ =>
    let T := type of P in unify T Prop;
    lazymatch P with
    | guard_seen _ => fail
    | vector_value_eq _ _ => fail
    | _ =>
      tryif (match goal with _ : guard_seen P |- _ => idtac end)
      then fail
      else first [solve [exfalso;
        repeat match goal with v : bv 65536 |- _ => clear dependent v end;
        bv_solve]
      | let marker := fresh "GUARD" in pose proof (guard_seen_intro P) as marker]
    end
  end.
Goal forall x : bv 64, (bv_unsigned x < 0)%Z -> False.
Proof. intros x Hx. freshGuard. Qed.
Goal forall x : bv 64, (bv_unsigned x <= 8)%Z -> True.
Proof. intros x Hx. freshGuard. exact I. Qed.
