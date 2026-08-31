import SALT.Kernel.Schedule

namespace SALT.Kernel.Schedule

universe u v w

/-- Execute a large fixed-width phase, then a smaller fixed-width phase, then a
    final short-tail model. Both widths are parameters of one reusable family. -/
def runTwoPhaseTail {α : Type u} {β : Type v}
    (largeWidth smallWidth : Nat)
    (largePositive : 0 < largeWidth) (smallPositive : 0 < smallWidth)
    (largeBody smallBody tail : List α → List β) (input : List α) : List β :=
  runFixedChunkTail largeWidth largePositive largeBody
    (runFixedChunkTail smallWidth smallPositive smallBody tail) input

theorem runTwoPhaseTail_eq_map {α : Type u} {β : Type v}
    (largeWidth smallWidth : Nat)
    (largePositive : 0 < largeWidth) (smallPositive : 0 < smallWidth)
    (largeBody smallBody tail : List α → List β) (f : α → β)
    (largeRefines : ∀ input, input.length = largeWidth →
      largeBody input = input.map f)
    (smallRefines : ∀ input, input.length = smallWidth →
      smallBody input = input.map f)
    (tailRefines : ∀ input, 0 < input.length → input.length < smallWidth →
      tail input = input.map f)
    (input : List α) :
    runTwoPhaseTail largeWidth smallWidth largePositive smallPositive
      largeBody smallBody tail input = input.map f := by
  unfold runTwoPhaseTail
  apply runFixedChunkTail_eq_map largeWidth largePositive largeBody
    (runFixedChunkTail smallWidth smallPositive smallBody tail) f largeRefines
  · intro remainder _ _
    exact runFixedChunkTail_eq_map smallWidth smallPositive smallBody tail f
      smallRefines tailRefines remainder

/-- Apply a synchronized fixed-tail executor when the two runtime list lengths
    agree. The unequal branch is unreachable in the two-phase family theorem. -/
def runFixedChunkTail2IfSame {α : Type u} {β : Type v} {γ : Type w}
    (width : Nat) (widthPositive : 0 < width)
    (body tail : List α → List β → List γ)
    (inputA : List α) (inputB : List β) : List γ :=
  if sameLength : inputA.length = inputB.length then
    runFixedChunkTail2 width widthPositive body tail inputA inputB sameLength
  else
    []

/-- Synchronized binary form of `runTwoPhaseTail`. -/
def runTwoPhaseTail2 {α : Type u} {β : Type v} {γ : Type w}
    (largeWidth smallWidth : Nat)
    (largePositive : 0 < largeWidth) (smallPositive : 0 < smallWidth)
    (largeBody smallBody tail : List α → List β → List γ)
    (inputA : List α) (inputB : List β)
    (sameLength : inputA.length = inputB.length) : List γ :=
  runFixedChunkTail2 largeWidth largePositive largeBody
    (runFixedChunkTail2IfSame smallWidth smallPositive smallBody tail) inputA inputB
    sameLength

theorem runTwoPhaseTail2_eq_zipWith {α : Type u} {β : Type v} {γ : Type w}
    (largeWidth smallWidth : Nat)
    (largePositive : 0 < largeWidth) (smallPositive : 0 < smallWidth)
    (largeBody smallBody tail : List α → List β → List γ) (f : α → β → γ)
    (largeRefines : ∀ inputA inputB, inputA.length = inputB.length →
      inputA.length = largeWidth →
      largeBody inputA inputB = List.zipWith f inputA inputB)
    (smallRefines : ∀ inputA inputB, inputA.length = inputB.length →
      inputA.length = smallWidth →
      smallBody inputA inputB = List.zipWith f inputA inputB)
    (tailRefines : ∀ inputA inputB, inputA.length = inputB.length →
      0 < inputA.length → inputA.length < smallWidth →
      tail inputA inputB = List.zipWith f inputA inputB)
    (inputA : List α) (inputB : List β)
    (sameLength : inputA.length = inputB.length) :
    runTwoPhaseTail2 largeWidth smallWidth largePositive smallPositive
      largeBody smallBody tail inputA inputB sameLength =
        List.zipWith f inputA inputB := by
  unfold runTwoPhaseTail2
  apply runFixedChunkTail2_eq_zipWith largeWidth largePositive largeBody
    (runFixedChunkTail2IfSame smallWidth smallPositive smallBody tail) f largeRefines
  · intro remainderA remainderB sameRemainder _ _
    simp only [runFixedChunkTail2IfSame, dif_pos sameRemainder]
    exact runFixedChunkTail2_eq_zipWith smallWidth smallPositive smallBody tail f
      smallRefines tailRefines remainderA remainderB sameRemainder

end SALT.Kernel.Schedule
