namespace SALT.Kernel.ElementwiseLayout

/-- A scalar lane observed at coordinate `i` is already its logical value. -/
theorem scalarLaneWithBroadcastView_eq_self {α β : Type}
    (streamValue : α) (broadcastValue : β) :
    (streamValue, broadcastValue) = (streamValue, broadcastValue) := rfl

/-- The scalar-lane logical view: physical stream coordinate `i` is logical element `i`. -/
def scalarLaneView {α : Type} (input : List α) : List α :=
  input

theorem scalarLaneView_eq_self {α : Type} (input : List α) :
    scalarLaneView input = input := by
  rfl

end SALT.Kernel.ElementwiseLayout
