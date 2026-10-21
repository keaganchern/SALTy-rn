import Neon2LeanDemo.Generated

namespace Neon2LeanDemo

open Neon2LeanDemo.Generated

def clampParams (rawMin rawMax : BitVec 32) : String → BitVec 32 := fun name =>
  if name == "min" then rawMin else if name == "max" then rawMax else 0

def StoreImplementsClamp (store : Store 16 8) : Prop :=
  ∀ (input : Nat → BitVec 8) (rawMin rawMax : BitVec 32) (lane : Fin 16),
    store.value.denote input (clampParams rawMin rawMax) lane =
      unsignedClamp (BitVec.ofNat 8 rawMin.toNat) (BitVec.ofNat 8 rawMax.toNat)
        (input (store.outputOffset + lane.val))

def uMax8 (x y : BitVec 8) : BitVec 8 := if x.toNat ≥ y.toNat then x else y

def uMin8 (x y : BitVec 8) : BitVec 8 := if x.toNat ≤ y.toNat then x else y

def mainOrderClamp (lo hi x : BitVec 8) : BitVec 8 := uMin8 (uMax8 x lo) hi

def tailOrderClamp (lo hi x : BitVec 8) : BitVec 8 := uMax8 (uMin8 x hi) lo

/-- The 8-byte/tail order equals the main-loop order exactly when truncated bounds are ordered. -/
theorem clamp_orders_eq (lo hi x : BitVec 8) (hBounds : lo.toNat ≤ hi.toNat) :
    tailOrderClamp lo hi x = mainOrderClamp lo hi x := by
  by_cases hLow : x.toNat < lo.toNat
  · have hxhi : x.toNat ≤ hi.toNat := by omega
    have hMinXHi : uMin8 x hi = x := by simp [uMin8, hxhi]
    have hMaxXLo : uMax8 x lo = lo := by simp [uMax8]; omega
    have hMinLoHi : uMin8 lo hi = lo := by simp [uMin8, hBounds]
    simp [tailOrderClamp, mainOrderClamp, hMinXHi, hMaxXLo, hMinLoHi]
  · by_cases hHigh : hi.toNat < x.toNat
    · have hxlo : lo.toNat ≤ x.toNat := by omega
      have hMinXHi : uMin8 x hi = hi := by simp [uMin8]; omega
      have hMaxHiLo : uMax8 hi lo = hi := by simp [uMax8, hBounds]
      have hMaxXLo : uMax8 x lo = x := by simp [uMax8, hxlo]
      simp [tailOrderClamp, mainOrderClamp, hMinXHi, hMaxHiLo, hMaxXLo]
    · have hxlo : lo.toNat ≤ x.toNat := by omega
      have hxhi : x.toNat ≤ hi.toNat := by omega
      have hMinXHi : uMin8 x hi = x := by simp [uMin8, hxhi]
      have hMaxXLo : uMax8 x lo = x := by simp [uMax8, hxlo]
      simp [tailOrderClamp, mainOrderClamp, hMinXHi, hMaxXLo]

theorem main_order_eq_unsignedClamp (lo hi x : BitVec 8) :
    mainOrderClamp lo hi x = unsignedClamp lo hi x := by
  rfl

theorem block0_correct : StoreImplementsClamp u8VClampBlock0 := by
  intro input rawMin rawMax lane
  rfl

theorem block1_correct : StoreImplementsClamp u8VClampBlock1 := by
  intro input rawMin rawMax lane
  rfl

theorem block2_correct : StoreImplementsClamp u8VClampBlock2 := by
  intro input rawMin rawMax lane
  rfl

theorem block3_correct : StoreImplementsClamp u8VClampBlock3 := by
  intro input rawMin rawMax lane
  rfl

theorem generated_stores_correct :
    StoreImplementsClamp u8VClampBlock0 ∧
    StoreImplementsClamp u8VClampBlock1 ∧
    StoreImplementsClamp u8VClampBlock2 ∧
    StoreImplementsClamp u8VClampBlock3 :=
  ⟨block0_correct, block1_correct, block2_correct, block3_correct⟩

/-- The extracted main-loop body writes exactly byte offsets 0 through 63. -/
theorem exact_write_footprint : u8VClampMain.writeAddresses = List.range 64 := by
  decide

theorem extracted_loop_metadata :
    u8VClampMain.batchGuard = 64 ∧
    u8VClampMain.batchDecrement = 64 ∧
    u8VClampMain.inputAdvance = 64 ∧
    u8VClampMain.outputAdvance = 64 := by
  decide

end Neon2LeanDemo
