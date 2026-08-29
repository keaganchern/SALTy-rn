-- This is the only agent-written file in the example.
import SALT.Example.S8VMaxV2.Spec

namespace SALT.Example.S8VMaxV2

open SALT.Example.S8VMax

private theorem neonBlock16_eq_map_fNeon (p : S8VMaxParams)
    (input : List (BitVec 8)) (hLength : input.length = 16) :
    neonBlock16FromIntrinsics p input = input.map (fNeon p) := by
  simp only [neonBlock16FromIntrinsics, SALT.Intrinsics.Neon.vmaxq_s8]
  rw [SALT.zipWith_replicate_right SALT.bvSignedMax
    (p.threshold.truncate 8) (input.take 16) 16 (h := by simp [hLength])]
  have hTake : input.take 16 = input := by
    simpa only [hLength] using (List.take_length (l := input))
  rw [hTake]
  simp [fNeon, SALT.Intrinsics.Neon.vmaxq_s8]

private theorem rvvChunk_eq_map_fRvv (p : S8VMaxParams)
    (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (fRvv p) := by
  simp [rvvChunkFromIntrinsics, fRvv, SALT.Intrinsics.RVV.vmax_vx]

theorem f_neon_eq_f_rvv : elementFunctionsEqualClaim := by
  intro p x
  simp [fNeon, fRvv, SALT.Intrinsics.Neon.vmaxq_s8,
    SALT.Intrinsics.RVV.vmax_vx]

theorem neon_loop_eq_map : neonLoopEqualsMapClaim := by
  intro p batch input hLength hAsserts
  apply SALT.Kernel.ElementwiseFamily.runFixedNoTail_eq_map
    16 (by omega) (neonBlock16FromIntrinsics p) (fNeon p)
    (neonBlock16_eq_map_fNeon p) input
  apply Nat.dvd_iff_mod_eq_zero.mpr
  simpa only [hLength] using hAsserts.2

theorem rvv_loop_eq_map : rvvLoopEqualsMapClaim := by
  intro p batch input schedule _hLength _hAsserts
  exact SALT.Kernel.Schedule.processBlocks_eq_map
    (rvvChunkFromIntrinsics p) (fRvv p) (rvvChunk_eq_map_fRvv p) input schedule

theorem maps_equal (p : S8VMaxParams) (input : List (BitVec 8)) :
    input.map (fNeon p) = input.map (fRvv p) := by
  have hFunctions : fNeon p = fRvv p := by
    funext x
    exact f_neon_eq_f_rvv p x
  rw [hFunctions]

theorem complete_value_equivalence : completeValueEquivalenceClaim := by
  intro p batch input schedule hLength hNeon hRvv
  rw [neon_loop_eq_map p batch input hLength hNeon]
  rw [rvv_loop_eq_map p batch input schedule hLength hRvv]
  exact maps_equal p input

end SALT.Example.S8VMaxV2
