import Neon2LeanDemo.Production.Memory

namespace Neon2LeanDemo.Production

structure ScalarArgument where
  name : String
  value : Int
  deriving BEq, DecidableEq, Repr

structure KernelArgs where
  inputBase : Address
  outputBase : Address
  batch : Nat
  scalars : List ScalarArgument
  deriving BEq, DecidableEq, Repr

private def findScalar? : List ScalarArgument → String → Option Int
  | [], _ => none
  | argument :: rest, name =>
      if argument.name = name then some argument.value else findScalar? rest name

def KernelArgs.scalar? (args : KernelArgs) (name : String) : Option Int :=
  findScalar? args.scalars name

inductive AliasPolicy where
  | disjoint
  | disjointOrExactInPlace
  deriving BEq, DecidableEq, Repr

def AliasPolicy.holds (policy : AliasPolicy) (input output : ByteRange) : Prop :=
  match policy with
  | .disjoint => input.disjoint output
  | .disjointOrExactInPlace => input.disjoint output ∨ input.base = output.base

/-- Structured kernel precondition over byte extents, aliases, and scalar parameters. -/
structure Contract where
  inputReadableBytes : KernelArgs → Nat
  outputWritableBytes : KernelArgs → Nat
  aliasPolicy : AliasPolicy
  parametersValid : KernelArgs → Prop

def Contract.inputRange (contract : Contract) (args : KernelArgs) : ByteRange :=
  { base := args.inputBase, length := contract.inputReadableBytes args }

def Contract.outputRange (contract : Contract) (args : KernelArgs) : ByteRange :=
  { base := args.outputBase, length := contract.outputWritableBytes args }

def Contract.holds (contract : Contract) (args : KernelArgs) (memory : ByteMemory) : Prop :=
  contract.parametersValid args ∧
    memory.canReadRange args.inputBase (contract.inputReadableBytes args) = true ∧
    memory.canWriteRange args.outputBase (contract.outputWritableBytes args) = true ∧
    contract.aliasPolicy.holds (contract.inputRange args) (contract.outputRange args)

structure ExecState (ArchState : Type) where
  memory : ByteMemory
  arch : ArchState

/-- Heterogeneous source/target observation with an explicit architecture-state quotient. -/
structure Observe (SourceArch TargetArch : Type) where
  sourceOutput : KernelArgs → ByteRange
  targetOutput : KernelArgs → ByteRange
  architectureEquivalent : SourceArch → TargetArch → Prop

def Observe.outputPrefix {SourceArch TargetArch : Type}
    (length : KernelArgs → Nat) : Observe SourceArch TargetArch :=
  { sourceOutput := fun args => { base := args.outputBase, length := length args }
    targetOutput := fun args => { base := args.outputBase, length := length args }
    architectureEquivalent := fun _ _ => True }

def Observe.equivalent {SourceArch TargetArch : Type}
    (observe : Observe SourceArch TargetArch) (args : KernelArgs)
    (source : ExecState SourceArch) (target : ExecState TargetArch) : Prop :=
  source.memory.snapshot (observe.sourceOutput args) =
      target.memory.snapshot (observe.targetOutput args) ∧
    observe.architectureEquivalent source.arch target.arch

def Observe.sourceFrame {SourceArch TargetArch : Type}
    (observe : Observe SourceArch TargetArch) (args : KernelArgs)
    (before after : ExecState SourceArch) : Prop :=
  before.memory.frameOutside after.memory (observe.sourceOutput args)

def Observe.targetFrame {SourceArch TargetArch : Type}
    (observe : Observe SourceArch TargetArch) (args : KernelArgs)
    (before after : ExecState TargetArch) : Prop :=
  before.memory.frameOutside after.memory (observe.targetOutput args)

end Neon2LeanDemo.Production
