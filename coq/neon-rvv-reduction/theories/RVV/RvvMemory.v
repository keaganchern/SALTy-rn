Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvLaneMath.

Lemma byte_array_append `{!islaG Σ} (p : Z) (xs ys : list (bv 8)) :
  p ↦ₘ∗ (xs ++ ys) ⊣⊢ p ↦ₘ∗ xs ∗ (p + Z.of_nat (length xs)) ↦ₘ∗ ys.
Proof.
  rewrite !mem_mapsto_array_eq. iSplit.
  - iDestruct 1 as (len Hlen Hrange) "Hmem".
    assert (len = 1)%N by lia. subst len.
    rewrite big_sepL_app. iDestruct "Hmem" as "[Hx Hy]".
    iSplitL "Hx".
    + iExists 1%N. iSplit; [done|]. iSplit; [iPureIntro; rewrite length_app in Hrange; lia|]. iExact "Hx".
    + iExists 1%N. iSplit; [done|]. iSplit; [iPureIntro; rewrite length_app in Hrange; lia|].
      iApply (big_sepL_mono with "Hy"). intros i x Hx. rewrite Nat2Z.inj_add.
      replace (p + (Z.of_nat (length xs) + Z.of_nat i) * Z.of_N 1)%Z
        with (p + Z.of_nat (length xs) + Z.of_nat i * Z.of_N 1)%Z by lia.
      done.
  - iIntros "[Hx Hy]". iDestruct "Hx" as (lx Hlx Hrx) "Hx".
    iDestruct "Hy" as (ly Hly Hry) "Hy".
    assert (lx=1)%N by lia. assert (ly=1)%N by lia. subst lx ly.
    iExists 1%N. iSplit; [done|]. iSplit; [iPureIntro; rewrite length_app; lia|].
    rewrite big_sepL_app. iFrame "Hx".
    iApply (big_sepL_mono with "Hy"). intros i x Hx. rewrite Nat2Z.inj_add.
    replace (p + (Z.of_nat (length xs) + Z.of_nat i) * Z.of_N 1)%Z
      with (p + Z.of_nat (length xs) + Z.of_nat i * Z.of_N 1)%Z by lia.
    done.
Qed.

Lemma byte_array_take_drop `{!islaG Σ} p (xs : list (bv 8)) k :
  (k <= length xs)%nat ->
  p ↦ₘ∗ xs ⊣⊢ p ↦ₘ∗ take k xs ∗ (p + Z.of_nat k) ↦ₘ∗ drop k xs.
Proof.
  intros Hk. rewrite <- (take_drop k xs) at 1.
  rewrite byte_array_append length_take Nat.min_l; done.
Qed.
Print Assumptions byte_array_append.
Print Assumptions byte_array_take_drop.
