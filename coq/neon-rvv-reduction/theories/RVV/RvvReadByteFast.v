Require Import isla.riscv64.riscv64 Reduction.RVV.RvvLoadSharedDefs.
From iris.proofmode Require Import environments.
Lemma input8_lookup f i : (i < 8)%nat -> input8 f !! i = Some (f (N.of_nat i)).
Proof.
 intros Hi. assert (i=0 \/ i=1 \/ i=2 \/ i=3 \/ i=4 \/ i=5 \/ i=6 \/ i=7)%nat as Hcases by lia.
 repeat destruct Hcases as [Hcases|Hcases]; subst i; reflexivity.
Qed.
Lemma read_input8_fast `{!islaG Σ} `{!threadG}
 (p a : bv 64) (f : N -> bv 8) (v : bv 8) (i : nat) es ann kind tag :
 (i < 8)%nat -> bv_unsigned a = (bv_unsigned p + Z.of_nat i)%Z ->
 (bv_unsigned p ↦ₘ∗ input8 f ∗
  (⌜v = f (N.of_nat i)⌝ -∗ bv_unsigned p ↦ₘ∗ input8 f -∗ WPasm es)) ⊢
 WPasm (ReadMem (RVal_Bits (bv_to_bvn v)) kind (RVal_Bits (bv_to_bvn a)) 1 tag ann :t: es).
Proof.
 intros Hi Ha. iIntros "[Hm Hcont]".
 iApply (wp_read_mem_array 8 1 a (bv_unsigned p) v (f (N.of_nat i)) i (input8 f) with "Hm Hcont");
 [reflexivity|lia|apply input8_lookup; exact Hi|lia].
Qed.
Print Assumptions read_input8_fast.
Ltac readInputByte p f range := 
 lazymatch goal with
 | |- envs_entails _ (WPasm (ReadMem (RVal_Bits (bv_to_bvn ?v)) ?kind (RVal_Bits (bv_to_bvn ?a)) 1 ?tag ?ann :t: ?es)) =>
  let raw := eval cbv delta [a] in a in
  let base := lazymatch raw with bv_add ?base _ => base | _ => raw end in
  let off := lazymatch raw with bv_add _ ?off => off | _ => constr:(BV 64 0) end in
  unify base p;
  let kZ := eval vm_compute in (bv_unsigned off) in
  let k := eval vm_compute in (Z.to_nat kZ) in
  let hi := fresh "MEM_INDEX" in assert (hi : (k < 8)%nat) by lia;
  let ha := fresh "MEM_ADDRESS" in
  assert (ha : bv_unsigned a = (bv_unsigned p + Z.of_nat k)%Z) by
    (clear -range a; try unfold a; bv_solve);
  notypeclasses refine (tac_fast_apply (read_input8_fast p a f v k es ann kind tag hi ha) _);
  iFrame;
  let hv := fresh "MEM_VALUE" in iIntros (hv) "Hmem";
  try subst v; liSimpl;
  idtac "direct byte read" k
 end.
