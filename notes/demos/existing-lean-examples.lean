/-
Tested against lean-verification@dd1c0ab12dedccc8d1e0296c82cbc3b72c32249f.
The imported modules are not present on the main-based research branch. From a
separate checkout of that revision's src/verification/lean directory, run:

  lake env lean /path/to/research-worktree/notes/demos/existing-lean-examples.lean

These evaluations exercise the historical Lean models. They are not C/ISA executions.
-/
import SALT.Kernel.QS8ClampEmit.Equivalence
import SALT.Kernel.QS8VAddC.Equivalence

open SALT.Kernel.QS8

def clampParams : QS8AddMinmaxParams :=
  { a_zero_point := BitVec.ofInt 8 0
    b_zero_point := BitVec.ofInt 8 0
    bias := BitVec.ofInt 32 0
    a_multiplier := BitVec.ofInt 32 1
    b_multiplier := BitVec.ofInt 32 1
    shift := BitVec.ofInt 32 0
    output_zero_point := BitVec.ofInt 16 0
    output_min := BitVec.ofInt 8 (-10)
    output_max := BitVec.ofInt 8 20 }

def clampInput : List (BitVec 8) :=
  [-30, -10, -4, 0, 20, 21, 100].map (BitVec.ofInt 8)

-- Neon pads one short 8-lane chunk; RVV uses chunks 3, 3, 1.
#eval (SALT.Kernel.QS8ClampEmit.Neon.neonLoop clampParams clampInput).map BitVec.toInt
#eval (SALT.Kernel.QS8ClampEmit.RVV.rvvLoop clampParams clampInput 3).map BitVec.toInt

def addParams : QS8AddMinmaxParams :=
  { clampParams with
    output_min := BitVec.ofInt 8 (-128)
    output_max := BitVec.ofInt 8 127 }

def addInputA : List (BitVec 8) := [-3, 0, 5].map (BitVec.ofInt 8)
def addInputB : BitVec 8 := BitVec.ofInt 8 2

-- With zero points 0, multipliers 1, and shift 0, this computes input_a + input_b.
#eval
  (SALT.Kernel.QS8VAddC.Neon.neonLoop addParams
    (SALT.Kernel.QS8VAddC.Neon.computeBias addParams addInputB) addInputA).map BitVec.toInt
#eval
  (SALT.Kernel.QS8VAddC.RVV.rvvLoop addParams
    (SALT.Kernel.QS8VAddC.RVV.computeBias addParams addInputB) addInputA 2).map BitVec.toInt

#check SALT.Kernel.QS8ClampEmit.Equivalence.qs8clampemit_equiv
#check SALT.Kernel.QS8VAddC.Equivalence.qs8_vaddc_equiv

#print axioms SALT.Kernel.QS8ClampEmit.Equivalence.qs8clampemit_equiv
#print axioms SALT.Kernel.QS8VAddC.Equivalence.qs8_vaddc_equiv
