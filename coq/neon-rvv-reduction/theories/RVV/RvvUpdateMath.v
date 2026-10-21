Require Import isla.riscv64.riscv64 Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvUpdateExpressions Reduction.RVV.RvvBytePackingAll.
Lemma byte_zext_self (x : bv 8) : bv_zero_extend 8 x = x.
Proof. apply bv_zero_extend_idemp. Qed.
Lemma pack32bytes_ext (f g : N -> bv 8) :
  (forall i, (i < 32)%N -> f i = g i) -> pack32bytes f = pack32bytes g.
Proof.
  intros Hfg. unfold pack32bytes.
  rewrite (Hfg 0%N ltac:(lia)) (Hfg 1%N ltac:(lia)) (Hfg 2%N ltac:(lia)) (Hfg 3%N ltac:(lia)) (Hfg 4%N ltac:(lia)) (Hfg 5%N ltac:(lia)) (Hfg 6%N ltac:(lia)) (Hfg 7%N ltac:(lia)) (Hfg 8%N ltac:(lia)) (Hfg 9%N ltac:(lia)) (Hfg 10%N ltac:(lia)) (Hfg 11%N ltac:(lia)) (Hfg 12%N ltac:(lia)) (Hfg 13%N ltac:(lia)) (Hfg 14%N ltac:(lia)) (Hfg 15%N ltac:(lia)) (Hfg 16%N ltac:(lia)) (Hfg 17%N ltac:(lia)) (Hfg 18%N ltac:(lia)) (Hfg 19%N ltac:(lia)) (Hfg 20%N ltac:(lia)) (Hfg 21%N ltac:(lia)) (Hfg 22%N ltac:(lia)) (Hfg 23%N ltac:(lia)) (Hfg 24%N ltac:(lia)) (Hfg 25%N ltac:(lia)) (Hfg 26%N ltac:(lia)) (Hfg 27%N ltac:(lia)) (Hfg 28%N ltac:(lia)) (Hfg 29%N ltac:(lia)) (Hfg 30%N ltac:(lia)) (Hfg 31%N ltac:(lia)).
  reflexivity.
Qed.
Lemma load_update_lane_0 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_0 old byte) =
  if decide (j = 0%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_0. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_1 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_1 old byte) =
  if decide (j = 1%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_1. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_2 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_2 old byte) =
  if decide (j = 2%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_2. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_3 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_3 old byte) =
  if decide (j = 3%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_3. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_4 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_4 old byte) =
  if decide (j = 4%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_4. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_5 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_5 old byte) =
  if decide (j = 5%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_5. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_6 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_6 old byte) =
  if decide (j = 6%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_6. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_7 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_7 old byte) =
  if decide (j = 7%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_7. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_8 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_8 old byte) =
  if decide (j = 8%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_8. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_9 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_9 old byte) =
  if decide (j = 9%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_9. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_10 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_10 old byte) =
  if decide (j = 10%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_10. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_11 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_11 old byte) =
  if decide (j = 11%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_11. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_12 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_12 old byte) =
  if decide (j = 12%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_12. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_13 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_13 old byte) =
  if decide (j = 13%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_13. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_14 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_14 old byte) =
  if decide (j = 14%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_14. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_15 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_15 old byte) =
  if decide (j = 15%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_15. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_16 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_16 old byte) =
  if decide (j = 16%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_16. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_17 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_17 old byte) =
  if decide (j = 17%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_17. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_18 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_18 old byte) =
  if decide (j = 18%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_18. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_19 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_19 old byte) =
  if decide (j = 19%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_19. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_20 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_20 old byte) =
  if decide (j = 20%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_20. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_21 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_21 old byte) =
  if decide (j = 21%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_21. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_22 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_22 old byte) =
  if decide (j = 22%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_22. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_23 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_23 old byte) =
  if decide (j = 23%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_23. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_24 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_24 old byte) =
  if decide (j = 24%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_24. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_25 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_25 old byte) =
  if decide (j = 25%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_25. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_26 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_26 old byte) =
  if decide (j = 26%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_26. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_27 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_27 old byte) =
  if decide (j = 27%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_27. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_28 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_28 old byte) =
  if decide (j = 28%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_28. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_29 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_29 old byte) =
  if decide (j = 29%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_29. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_30 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_30 old byte) =
  if decide (j = 30%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_30. apply pack32bytes_lane_all. exact Hj. Qed.
Lemma load_update_lane_31 j old byte : (j < 32)%N ->
  bv_extract (8*j) 8 (load_update_value_31 old byte) =
  if decide (j = 31%N) then byte else bv_extract (8*j) 8 old.
Proof. intros Hj. unfold load_update_value_31. apply pack32bytes_lane_all. exact Hj. Qed.
Print Assumptions pack32bytes_ext.
Print Assumptions load_update_lane_31.
