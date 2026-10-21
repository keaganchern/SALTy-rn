import Neon2LeanDemo.Production.Contract
import Neon2LeanDemo.Production.FeatureGate

namespace Neon2LeanDemo.Production

abbrev S8Byte := BitVec 8

def signedMaxS8 (left right : S8Byte) : S8Byte :=
  if right.toInt <= left.toInt then left else right

def signedMinS8 (left right : S8Byte) : S8Byte :=
  if left.toInt <= right.toInt then left else right

def signedClampS8 (lo hi value : S8Byte) : S8Byte :=
  signedMinS8 (signedMaxS8 value lo) hi

inductive RuntimeValue where
  | pointer (address : Address)
  | scalarS8 (value : S8Byte)
  | natural (value : Nat)
  | vectorS8 (values : List S8Byte)
  | splatS8 (value : S8Byte) (lanes : Nat)
  deriving BEq, DecidableEq, Repr

abbrev RuntimeEnv := List (Nat × RuntimeValue)

def RuntimeEnv.lookup? : RuntimeEnv -> Nat -> Option RuntimeValue
  | [], _ => none
  | (nodeId, value) :: rest, wanted =>
      if nodeId = wanted then some value else RuntimeEnv.lookup? rest wanted

def RuntimeEnv.insert (env : RuntimeEnv) (nodeId : Nat)
    (value : RuntimeValue) : RuntimeEnv :=
  (nodeId, value) :: env

structure ChunkContext where
  inputBase : Address
  outputBase : Address
  input : List S8Byte
  lo : S8Byte
  hi : S8Byte
  remaining : Nat

structure ChunkState where
  env : RuntimeEnv
  stored : Option (List S8Byte)

def seedParameter (context : ChunkContext) (parameter : Parameter) : Option RuntimeValue :=
  match parameter.name, parameter.valueType with
  | "input", .pointer => some (.pointer context.inputBase)
  | "output", .pointer => some (.pointer context.outputBase)
  | "lo", .scalar (.int 8 .signed) => some (.scalarS8 context.lo)
  | "hi", .scalar (.int 8 .signed) => some (.scalarS8 context.hi)
  | "remaining", .scalar (.int _ .unsigned) => some (.natural context.remaining)
  | _, _ => none

def seedEnvironment (context : ChunkContext) : List Parameter -> Option RuntimeEnv
  | [] => some []
  | parameter :: rest => do
      let value <- seedParameter context parameter
      let env <- seedEnvironment context rest
      pure (env.insert parameter.nodeId value)

def operands (state : ChunkState) (operation : Operation) : Option (List RuntimeValue) :=
  operation.operandNodes.mapM state.env.lookup?

def vectorLength? : RuntimeValue -> Option Nat
  | .vectorS8 values => some values.length
  | .splatS8 _ lanes => some lanes
  | _ => none

def mapVector (function : S8Byte -> S8Byte) : RuntimeValue -> Option RuntimeValue
  | .vectorS8 values => some (.vectorS8 (values.map function))
  | .splatS8 value lanes => some (.splatS8 (function value) lanes)
  | _ => none

def zipVector (function : S8Byte -> S8Byte -> S8Byte) :
    RuntimeValue -> RuntimeValue -> Option RuntimeValue
  | .vectorS8 values, .splatS8 value lanes =>
      if values.length = lanes then some (.vectorS8 (values.map fun item => function item value))
      else none
  | .splatS8 value lanes, .vectorS8 values =>
      if values.length = lanes then some (.vectorS8 (values.map fun item => function value item))
      else none
  | .splatS8 left leftLanes, .splatS8 right rightLanes =>
      if leftLanes = rightLanes then some (.splatS8 (function left right) leftLanes) else none
  | .vectorS8 left, .vectorS8 right =>
      if left.length = right.length then some (.vectorS8 (List.zipWith function left right)) else none
  | _, _ => none

def checkedVector (value : RuntimeValue) (expectedLength : Nat) : Option (List S8Byte) :=
  match value with
  | .vectorS8 values => if values.length = expectedLength then some values else none
  | .splatS8 item lanes => if lanes = expectedLength then some (List.replicate lanes item) else none
  | _ => none

def withResult (operation : Operation) (state : ChunkState)
    (value : RuntimeValue) : Option ChunkState :=
  match operation.resultType with
  | none => none
  | some _ => some { state with env := state.env.insert operation.nodeId value }

def interpretOpcode (opcode : SemanticOpcode) (context : ChunkContext)
    (operation : Operation) (state : ChunkState) : Option ChunkState := do
  let values <- operands state operation
  match opcode, values with
  | .neonLoad16S8, [.pointer address] =>
      if address = context.inputBase && context.input.length = 16 then
        withResult operation state (.vectorS8 context.input)
      else none
  | .neonSplat16S8, [.scalarS8 value] =>
      withResult operation state (.splatS8 value 16)
  | .neonSignedMaxS8, [left, right] => do
      let result <- zipVector signedMaxS8 left right
      withResult operation state result
  | .neonSignedMinS8, [left, right] => do
      let result <- zipVector signedMinS8 left right
      withResult operation state result
  | .neonStore16S8, [.pointer address, value] => do
      if state.stored.isSome || address != context.outputBase then none
      let output <- checkedVector value 16
      if operation.resultType.isSome then none else some { state with stored := some output }
  | .rvvSetVLE8M1, [.natural remaining] =>
      let chosen := context.input.length
      if 0 < chosen && chosen <= remaining && remaining = context.remaining then
        withResult operation state (.natural chosen)
      else none
  | .rvvLoadS8M1, [.pointer address, .natural vl] =>
      if address = context.inputBase && vl = context.input.length then
        withResult operation state (.vectorS8 context.input)
      else none
  | .rvvSignedMaxScalarS8M1, [value, .scalarS8 bound, .natural vl] => do
      if vectorLength? value != some vl then none
      let result <- mapVector (fun item => signedMaxS8 item bound) value
      withResult operation state result
  | .rvvSignedMinScalarS8M1, [value, .scalarS8 bound, .natural vl] => do
      if vectorLength? value != some vl then none
      let result <- mapVector (fun item => signedMinS8 item bound) value
      withResult operation state result
  | .rvvStoreS8M1, [.pointer address, value, .natural vl] => do
      if state.stored.isSome || address != context.outputBase then none
      let output <- checkedVector value vl
      if operation.resultType.isSome then none else some { state with stored := some output }
  | .return, [] =>
      if operation.resultType.isSome then none else some state
  | _, _ => none

def interpretOperation (registry : TrustedOperationRegistry) (context : ChunkContext)
    (operation : Operation) (state : ChunkState) : Option ChunkState := do
  let descriptor <- registry operation.operation.spelling
  interpretOpcode descriptor.opcode context operation state

def interpretOperations (registry : TrustedOperationRegistry) (context : ChunkContext) :
    List Operation -> ChunkState -> Option ChunkState
  | [], state => some state
  | operation :: rest, state => do
      let next <- interpretOperation registry context operation state
      interpretOperations registry context rest next

/-- Execute one generated straight-line chunk directly from its `KernelIR` operations. -/
def executeChunk (registry : TrustedOperationRegistry) (ir : KernelIR)
    (context : ChunkContext) : Option (List S8Byte) := do
  match ir.checkIntegerOnly registry with
  | .error _ => none
  | .ok () => pure ()
  if !ir.hasSingleBlockUseOrder then none
  let block <- ir.block? ir.entryBlock
  if ir.blocks.length != 1 || !block.successors.isEmpty then none
  let env <- seedEnvironment context ir.parameters
  let final <- interpretOperations registry context block.operations { env := env, stored := none }
  final.stored

inductive ControlMode where
  | fixed (width : Nat)
  | positiveStripMine (total : Nat)
  deriving BEq, DecidableEq, Repr

def ControlMode.totalBytes : ControlMode -> Nat
  | .fixed width | .positiveStripMine width => width

def executeStripMine (registry : TrustedOperationRegistry) (ir : KernelIR)
    (inputBase outputBase : Address) (lo hi : S8Byte) :
    Nat -> List Nat -> List S8Byte -> Option (List S8Byte)
  | remaining, [], input =>
      if remaining = 0 && input.isEmpty then some [] else none
  | remaining, chunk :: chunks, input => do
      if !(0 < chunk && chunk <= remaining && chunk <= input.length) then none
      let currentInput := input.take chunk
      if currentInput.length != chunk then none
      let currentOutput <- executeChunk registry ir
        { inputBase := inputBase
          outputBase := outputBase
          input := currentInput
          lo := lo
          hi := hi
          remaining := remaining }
      if currentOutput.length != chunk then none
      let rest <- executeStripMine registry ir (inputBase + chunk) (outputBase + chunk) lo hi
        (remaining - chunk) chunks (input.drop chunk)
      pure (currentOutput ++ rest)

/--
Execute the supported structured control layer. `positiveStripMine` quantifies over
positive progress schedules; a separate ISA bridge must characterize actual `vsetvl` results.
-/
def executeValues (registry : TrustedOperationRegistry) (mode : ControlMode) (ir : KernelIR)
    (inputBase outputBase : Address) (lo hi : S8Byte) (chunks : List Nat)
    (input : List S8Byte) : Option (List S8Byte) :=
  match mode with
  | .fixed width =>
      if chunks.isEmpty && input.length = width then
        executeChunk registry ir
          { inputBase := inputBase
            outputBase := outputBase
            input := input
            lo := lo
            hi := hi
            remaining := width }
      else none
  | .positiveStripMine total =>
      if input.length = total then
        executeStripMine registry ir inputBase outputBase lo hi total chunks input
      else none

structure EffectTrace where
  writeAddresses : List Address
  deriving BEq, DecidableEq, Repr

structure KernelResult where
  memory : ByteMemory
  output : List S8Byte
  effects : EffectTrace

def contiguousAddresses (base : Address) (count : Nat) : List Address :=
  (List.range count).map fun offset => base + offset

/-- Transactional final-state wrapper around operation-level chunk execution. -/
def executeMemory (registry : TrustedOperationRegistry) (mode : ControlMode) (ir : KernelIR)
    (args : KernelArgs) (before : ByteMemory) (chunks : List Nat) : Option KernelResult := do
  let lo <- args.scalar? "lo"
  let hi <- args.scalar? "hi"
  let input <- before.readBytes args.inputBase mode.totalBytes
  let output <- executeValues registry mode ir args.inputBase args.outputBase
    (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input
  let after <- before.writeBytes args.outputBase output
  pure
    { memory := after
      output := output
      effects := { writeAddresses := contiguousAddresses args.outputBase output.length } }

theorem executeMemory_frame {registry : TrustedOperationRegistry} {mode : ControlMode}
    {ir : KernelIR} {args : KernelArgs} {before : ByteMemory} {chunks : List Nat}
    {result : KernelResult}
    (hRun : executeMemory registry mode ir args before chunks = some result) :
    before.frameOutside result.memory
      { base := args.outputBase, length := result.output.length } := by
  cases hLo : args.scalar? "lo" with
  | none => simp [executeMemory, hLo] at hRun
  | some lo =>
      cases hHi : args.scalar? "hi" with
      | none => simp [executeMemory, hLo, hHi] at hRun
      | some hi =>
          cases hRead : before.readBytes args.inputBase mode.totalBytes with
          | none => simp [executeMemory, hLo, hHi, hRead] at hRun
          | some input =>
              cases hValues : executeValues registry mode ir args.inputBase args.outputBase
                  (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input with
              | none => simp [executeMemory, hLo, hHi, hRead, hValues] at hRun
              | some output =>
                  cases hWrite : before.writeBytes args.outputBase output with
                  | none => simp [executeMemory, hLo, hHi, hRead, hValues, hWrite] at hRun
                  | some after =>
                      simp [executeMemory, hLo, hHi, hRead, hValues, hWrite] at hRun
                      cases hRun
                      exact ByteMemory.writeBytes_frameOutside hWrite

theorem executeMemory_effects {registry : TrustedOperationRegistry} {mode : ControlMode}
    {ir : KernelIR} {args : KernelArgs} {before : ByteMemory} {chunks : List Nat}
    {result : KernelResult}
    (hRun : executeMemory registry mode ir args before chunks = some result) :
    result.effects.writeAddresses = contiguousAddresses args.outputBase result.output.length := by
  cases hLo : args.scalar? "lo" with
  | none => simp [executeMemory, hLo] at hRun
  | some lo =>
      cases hHi : args.scalar? "hi" with
      | none => simp [executeMemory, hLo, hHi] at hRun
      | some hi =>
          cases hRead : before.readBytes args.inputBase mode.totalBytes with
          | none => simp [executeMemory, hLo, hHi, hRead] at hRun
          | some input =>
              cases hValues : executeValues registry mode ir args.inputBase args.outputBase
                  (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input with
              | none => simp [executeMemory, hLo, hHi, hRead, hValues] at hRun
              | some output =>
                  cases hWrite : before.writeBytes args.outputBase output with
                  | none => simp [executeMemory, hLo, hHi, hRead, hValues, hWrite] at hRun
                  | some after =>
                      simp [executeMemory, hLo, hHi, hRead, hValues, hWrite] at hRun
                      cases hRun
                      rfl

end Neon2LeanDemo.Production
