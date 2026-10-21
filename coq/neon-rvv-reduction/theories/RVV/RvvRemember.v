Require Import isla.riscv64.riscv64 Reduction.RVV.StructAssume.
From iris.proofmode Require Import environments.
(* Keep computed vector values as variables with checked equations, rather
   than transparent local definitions that repeatedly expand nested updates. *)
Ltac rememberVector :=
  lazymatch goal with
  | |- envs_entails ?D (let_bind_hint (Val_Bits (bv_to_bvn ?y)) ?f) =>
    lazymatch type of y with
    | bv 65536 =>
      let name := fresh "VEC" in
      let equation := fresh "HVEC" in
      remember y as name eqn:equation;
      unfold let_bind_hint; cbn beta
    end
  end.
Ltac rememberKernelAStep := first [rememberVector | kernelAStep].
