namespace SALT.Kernel.ElementwiseLayout

/-- The scalar-lane logical view: physical stream coordinate `i` is logical element `i`. -/
def scalarLaneView {α : Type} (input : List α) : List α :=
  input

theorem scalarLaneView_eq_self {α : Type} (input : List α) :
    scalarLaneView input = input := by
  rfl

end SALT.Kernel.ElementwiseLayout
