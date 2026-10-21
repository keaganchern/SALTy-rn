import SALT.Generated.S8VClamp.Models

namespace SALT.Generated.S8VClamp

theorem generated_block_equal
    (p : S8ClampParams)
    (input : List (BitVec 8))
    (hLength : input.length = 64) :
    neonBlock64FromIntrinsics p input = rvvChunkFromIntrinsics p input := by
  have chunk_eq (xs : List (BitVec 8)) (hxs : xs.length = 16) :
      List.zipWith SALT.bvSignedMin
        (List.zipWith SALT.bvSignedMax xs
          (List.replicate 16 (p.min.truncate 8)))
        (List.replicate 16 (p.max.truncate 8)) =
      xs.map (fun x =>
        SALT.bvSignedMin (SALT.bvSignedMax x (p.min.truncate 8))
          (p.max.truncate 8)) := by
    rw [SALT.zipWith_replicate_right SALT.bvSignedMax
      (p.min.truncate 8) xs 16 (by omega)]
    rw [SALT.zipWith_replicate_right SALT.bvSignedMin
      (p.max.truncate 8)
      (xs.map (fun x => SALT.bvSignedMax x (p.min.truncate 8))) 16
      (by simp [hxs])]
    simp only [List.map_map, Function.comp_def]
  have h0 : (input.take 16).length = 16 := by
    simp [List.length_take, hLength]
  have h1 : ((input.drop 16).take 16).length = 16 := by
    simp [List.length_take, List.length_drop, hLength]
  have h2 : ((input.drop 32).take 16).length = 16 := by
    simp [List.length_take, List.length_drop, hLength]
  have h3 : ((input.drop 48).take 16).length = 16 := by
    simp [List.length_take, List.length_drop, hLength]
  have split_input :
      input.take 16 ++ (input.drop 16).take 16 ++
        (input.drop 32).take 16 ++ (input.drop 48).take 16 = input := by
    calc
      _ = input.take 64 := by
        rw [show 64 = 16 + 48 by decide, List.take_add]
        rw [show 48 = 16 + 32 by decide, List.take_add]
        rw [show 32 = 16 + 16 by decide, List.take_add]
        simp only [List.drop_drop, Nat.reduceAdd, List.append_assoc]
      _ = input := by
        simpa only [hLength] using (List.take_length (l := input))
  simp only [neonBlock64FromIntrinsics, rvvChunkFromIntrinsics,
    SALT.Intrinsics.Neon.vmaxq_s8, SALT.Intrinsics.Neon.vminq_s8,
    SALT.Intrinsics.RVV.vmax_vx, SALT.Intrinsics.RVV.vmin_vx]
  rw [chunk_eq (input.take 16) h0]
  rw [chunk_eq ((input.drop 16).take 16) h1]
  rw [chunk_eq ((input.drop 32).take 16) h2]
  rw [chunk_eq ((input.drop 48).take 16) h3]
  rw [List.map_map]
  simp only [Function.comp_def]
  rw [← List.map_append, ← List.map_append, ← List.map_append]
  exact congrArg
    (List.map (fun x =>
      SALT.bvSignedMin (SALT.bvSignedMax x (p.min.truncate 8))
        (p.max.truncate 8)))
    split_input

end SALT.Generated.S8VClamp
