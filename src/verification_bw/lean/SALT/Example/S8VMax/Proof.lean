import SALT.Example.S8VMax.Models

namespace SALT.Example.S8VMax

/-- The architecture-neutral value operation exposed only after independently
    translating the Neon and RVV blocks. -/
def element (p : S8VMaxParams) (x : BitVec 8) : BitVec 8 :=
  SALT.bvSignedMax x (p.threshold.truncate 8)

theorem neonBlock16_eq_map (p : S8VMaxParams)
    (input : List (BitVec 8)) (hLength : input.length = 16) :
    neonBlock16FromIntrinsics p input = input.map (element p) := by
  simp only [neonBlock16FromIntrinsics, SALT.Intrinsics.Neon.vmaxq_s8]
  rw [SALT.zipWith_replicate_right SALT.bvSignedMax
    (p.threshold.truncate 8) (input.take 16) 16 (h := by simp [hLength])]
  have hTake : input.take 16 = input := by
    simpa only [hLength] using (List.take_length (l := input))
  rw [hTake]
  rfl

theorem rvvChunk_eq_map (p : S8VMaxParams) (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (element p) := by
  rfl

/-- Equality at the generated local-block boundary. This is not yet a theorem
    about the complete C loops or machine instructions. -/
theorem block_equal (p : S8VMaxParams)
    (input : List (BitVec 8)) (hLength : input.length = 16) :
    neonBlock16FromIntrinsics p input = rvvChunkFromIntrinsics p input := by
  rw [neonBlock16_eq_map p input hLength, rvvChunk_eq_map]

end SALT.Example.S8VMax
