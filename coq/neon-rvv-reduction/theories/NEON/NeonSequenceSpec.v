Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonSequence Reduction.NEON.NeonBlockSpec Reduction.NEON.NeonProof Reduction.NEON.NeonPairProof Reduction.NEON.NeonWordProof Reduction.NEON.TypeBridge.
Require Import Reduction.NEON.NeonLaneBridge Reduction.NEON.LanePacking Reduction.NEON.WordPacking.

Definition byte_sum128 (bytes : bv 128) : bv 32 :=
  sum32 (map (bv_zero_extend 32) (neon_byte_lanes bytes)).

(* Numerical interpretation of the exact state transition proved in
   Reduction.NEON.NeonSequence.v. The halfword accumulator is reset on every block. *)
Lemma neon_sequence_sum q low high :
  neon_sum4 (after_load_pair q low high 0%nat) =
  bv_add (neon_sum4 (q 0%nat)) (byte_sum128 (bv_concat 128 high low)).
Proof.
  change (neon_arithmetic_result (q 0%nat) (BV 128 0) (bv_concat 128 high low) = bv_add (neon_sum4 (q 0%nat)) (byte_sum128 (bv_concat 128 high low))).
  rewrite neon_arithmetic_refines_block_spec.
  - unfold reduction_block_spec, byte_sum128.
    rewrite <- neon_sum4_view.
    change (bv_add (neon_sum4 (q 0%nat))
      (bv_add (BV 32 0) (sum32 (map (bv_zero_extend 32)
        (neon_byte_lanes (bv_concat 128 high low))))) = bv_add (neon_sum4 (q 0%nat)) (sum32 (map (bv_zero_extend 32) (neon_byte_lanes (bv_concat 128 high low))))).
    bv_solve.
  - intros i Hi.
    assert (Hz : bv_extract (16*i) 16 (BV 128 0) = BV 16 0).
    { apply bv_eq. rewrite bv_extract_unsigned. cbn [bv_unsigned].
      rewrite Z.shiftr_0_l. reflexivity. }
    rewrite Hz.
    change (0 + bv_unsigned (bv_extract (16*i) 8 (bv_concat 128 high low)) +
      bv_unsigned (bv_extract (16*i+8) 8 (bv_concat 128 high low)) < 65536)%Z.
    pose proof (bv_unsigned_in_range 8 (bv_extract (16*i) 8 (bv_concat 128 high low))).
    pose proof (bv_unsigned_in_range 8 (bv_extract (16*i+8) 8 (bv_concat 128 high low))).
    change (0 <= bv_unsigned (bv_extract (16*i) 8 (bv_concat 128 high low)) < 256)%Z in H.
    change (0 <= bv_unsigned (bv_extract (16*i+8) 8 (bv_concat 128 high low)) < 256)%Z in H0.
    lia.
Qed.

(* This recursion composes the ISA-proved block transformer. The separate
   machine-branch/loop refinement in Reduction.NEON.NeonLoop.v is still required. *)
Fixpoint structured_neon_blocks (bs : list (bv 64 * bv 64)) (q : nat -> bv 128) :=
  match bs with
  | [] => q
  | (low,high)::bs => structured_neon_blocks bs (after_load_pair q low high)
  end.
Fixpoint block_sum (bs : list (bv 64 * bv 64)) : bv 32 :=
  match bs with
  | [] => BV 32 0
  | (low,high)::bs => bv_add (byte_sum128 (bv_concat 128 high low)) (block_sum bs)
  end.
Lemma structured_neon_blocks_sum bs q :
  neon_sum4 (structured_neon_blocks bs q 0%nat) =
  bv_add (neon_sum4 (q 0%nat)) (block_sum bs).
Proof.
  revert q. induction bs as [|[low high] bs IH]; intros q; cbn [structured_neon_blocks block_sum].
  - symmetry. apply bv_add_0_r. reflexivity.
  - rewrite IH neon_sequence_sum. symmetry. apply bv_add_assoc.
Qed.
Print Assumptions neon_sequence_sum.
Print Assumptions structured_neon_blocks_sum.
