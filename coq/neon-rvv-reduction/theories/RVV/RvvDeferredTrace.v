Require Import isla.riscv64.riscv64 Reduction.RVV.RvvCompactLoad.
From iris.proofmode Require Import environments.
Arguments subst_trace : simpl never.
Ltac oneTraceHead es :=
 lazymatch es with
 | tnil => constr:(tnil)
 | ?e :t: ?tail => constr:(e :t: tail)
 | tcases ?ts => constr:(tcases ts)
 | TRACE_LET ?x => oneTraceHead x
 | subst_trace ?v ?n ?tail =>
   let body := oneTraceHead tail in
   lazymatch body with
   | ?e :t: ?rest => constr:(subst_val_event v n e :t: subst_trace v n rest)
   | tcases ?ts => constr:(tcases (subst_trace v n <$> ts))
   | tnil => constr:(tnil)
   end
 | _ => let body := eval unfold es in es in oneTraceHead body
 end.
Ltac deferredTraceHead :=
 lazymatch goal with |- envs_entails ?D (WPasm (subst_trace ?v ?n ?tail)) =>
   let body := oneTraceHead (subst_trace v n tail) in
   lazymatch body with
   | ?e :t: ?rest =>
     let head := eval simpl in e in
     change (envs_entails D (WPasm (head :t: rest)))
   | _ => change (envs_entails D (WPasm body))
   end
 end.
Goal forall n : bv 64, True.
Proof. intros n. pose (TRACE := TRACE_LET a800001ca_shared).
let es := constr:(subst_trace (Val_Bits n) 0 TRACE) in
let head := oneTraceHead es in
lazymatch head with ?e :t: ?tail => idtac "ONE_HEAD_OK" end.
exact I. Qed.
