namespace Neon2LeanDemo.Production

abbrev Address := Nat
abbrev Byte := BitVec 8

structure ByteRange where
  base : Address
  length : Nat
  deriving BEq, DecidableEq, Repr

def ByteRange.endAddress (range : ByteRange) : Address :=
  range.base + range.length

def ByteRange.contains (range : ByteRange) (address : Address) : Prop :=
  range.base ≤ address ∧ address < range.endAddress

def ByteRange.disjoint (left right : ByteRange) : Prop :=
  left.endAddress ≤ right.base ∨ right.endAddress ≤ left.base

/-- One allocated byte range and its independent read/write permissions. -/
structure Allocation where
  name : String
  range : ByteRange
  readable : Bool
  writable : Bool
  deriving BEq, DecidableEq, Repr

def Allocation.containsRange (allocation : Allocation) (address : Address)
    (count : Nat) : Bool :=
  decide (allocation.range.base ≤ address) &&
    decide (address + count ≤ allocation.range.endAddress)

/-- A total byte map plus the allocation metadata that makes access partial. -/
structure ByteMemory where
  bytes : Address → Byte
  allocations : List Allocation

def ByteMemory.canReadRange (memory : ByteMemory) (address : Address) (count : Nat) : Bool :=
  if count == 0 then
    true
  else
    memory.allocations.any fun allocation =>
      allocation.readable && allocation.containsRange address count

def ByteMemory.canWriteRange (memory : ByteMemory) (address : Address) (count : Nat) : Bool :=
  if count == 0 then
    true
  else
    memory.allocations.any fun allocation =>
      allocation.writable && allocation.containsRange address count

/-- Checked partial read; failure represents an access outside readable allocations. -/
def ByteMemory.readBytes (memory : ByteMemory) (address : Address)
    (count : Nat) : Option (List Byte) :=
  if memory.canReadRange address count then
    some (List.ofFn fun offset : Fin count => memory.bytes (address + offset.val))
  else
    none

theorem ByteMemory.readBytes_length {memory : ByteMemory} {address count : Nat}
    {values : List Byte} (hRead : memory.readBytes address count = some values) :
    values.length = count := by
  unfold ByteMemory.readBytes at hRead
  split at hRead
  · simpa using congrArg List.length (Option.some.inj hRead.symm)
  · contradiction

/-- Logical observation of bytes; unlike a program read, this does not require read permission. -/
def ByteMemory.snapshot (memory : ByteMemory) (range : ByteRange) : List Byte :=
  List.ofFn fun offset : Fin range.length => memory.bytes (range.base + offset.val)

private def ByteMemory.writeByteUnchecked (memory : ByteMemory) (address : Address)
    (value : Byte) : ByteMemory :=
  { memory with
    bytes := fun current => if current = address then value else memory.bytes current }

private def ByteMemory.writeBytesUnchecked (memory : ByteMemory) (address : Address) :
    List Byte → ByteMemory
  | [] => memory
  | value :: rest =>
      ByteMemory.writeBytesUnchecked (memory.writeByteUnchecked address value) (address + 1) rest

private theorem ByteMemory.writeByteUnchecked_unchanged (memory : ByteMemory)
    (written current : Address) (value : Byte) (hDifferent : current ≠ written) :
    (memory.writeByteUnchecked written value).bytes current = memory.bytes current := by
  simp [ByteMemory.writeByteUnchecked, hDifferent]

private theorem ByteMemory.writeBytesUnchecked_unchanged (memory : ByteMemory)
    (address current : Address) (values : List Byte)
    (hOutside : current < address ∨ address + values.length <= current) :
    (memory.writeBytesUnchecked address values).bytes current = memory.bytes current := by
  induction values generalizing memory address with
  | nil => rfl
  | cons value rest ih =>
      rw [ByteMemory.writeBytesUnchecked]
      rcases hOutside with hBefore | hAfter
      · rw [ih (memory := memory.writeByteUnchecked address value)
          (address := address + 1) (Or.inl (by exact Nat.lt_succ_of_lt hBefore))]
        apply ByteMemory.writeByteUnchecked_unchanged
        exact Nat.ne_of_lt hBefore
      · rw [ih (memory := memory.writeByteUnchecked address value)
          (address := address + 1)
          (Or.inr (by
            simpa [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm] using hAfter))]
        apply ByteMemory.writeByteUnchecked_unchanged
        have hAddressLt : address < current := by
          exact Nat.lt_of_lt_of_le (by simp : address < address + (value :: rest).length) hAfter
        exact (Nat.ne_of_lt hAddressLt).symm

private theorem ByteMemory.writeBytesUnchecked_allocations (memory : ByteMemory)
    (address : Address) (values : List Byte) :
    (memory.writeBytesUnchecked address values).allocations = memory.allocations := by
  induction values generalizing memory address with
  | nil => rfl
  | cons value rest ih =>
      rw [ByteMemory.writeBytesUnchecked, ih]
      rfl

/-- Checked partial write; allocation metadata is preserved on success. -/
def ByteMemory.writeBytes (memory : ByteMemory) (address : Address)
    (values : List Byte) : Option ByteMemory :=
  if memory.canWriteRange address values.length then
    some (memory.writeBytesUnchecked address values)
  else
    none

/-- Exact frame condition outside a designated write range. -/
def ByteMemory.frameOutside (before after : ByteMemory) (written : ByteRange) : Prop :=
  before.allocations = after.allocations ∧
    ∀ address, ¬written.contains address → before.bytes address = after.bytes address

theorem ByteMemory.writeBytes_frameOutside {before after : ByteMemory}
    {address : Address} {values : List Byte}
    (hWrite : before.writeBytes address values = some after) :
    before.frameOutside after { base := address, length := values.length } := by
  unfold ByteMemory.writeBytes at hWrite
  split at hWrite
  · cases hWrite
    constructor
    · exact (ByteMemory.writeBytesUnchecked_allocations before address values).symm
    · intro current hOutside
      apply Eq.symm
      apply ByteMemory.writeBytesUnchecked_unchanged
      simp only [ByteRange.contains, ByteRange.endAddress] at hOutside
      by_cases hBefore : current < address
      · exact Or.inl hBefore
      · apply Or.inr
        have hAtOrAfter : address <= current := Nat.le_of_not_gt hBefore
        exact Nat.le_of_not_gt fun hBeforeEnd => hOutside ⟨hAtOrAfter, hBeforeEnd⟩
  · simp at hWrite

end Neon2LeanDemo.Production
