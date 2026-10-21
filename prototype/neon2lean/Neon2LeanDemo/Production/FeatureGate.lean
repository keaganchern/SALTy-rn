import Neon2LeanDemo.Production.KernelIR

namespace Neon2LeanDemo.Production

/-- The exact vector shape fixed by a reviewed RVV operation descriptor. -/
structure RVVConfigShape where
  sew : Nat
  lmul : LMUL
  deriving BEq, DecidableEq, Repr

def RVVConfigShape.matches (expected : RVVConfigShape) (actual : RVVVectorConfig) : Bool :=
  expected.sew == actual.sew && expected.lmul == actual.lmul

/--
Reviewed semantic operation selected by an exact C spelling. The frontend cannot
choose this field. `unavailable` keeps audit-only descriptors explicit and makes
the executable interpreter fail closed.
-/
inductive SemanticOpcode where
  | unavailable
  | return
  | neonLoad16S8
  | neonSplat16S8
  | neonSignedMaxS8
  | neonSignedMinS8
  | neonStore16S8
  | rvvSetVLE8M1
  | rvvLoadS8M1
  | rvvSignedMaxScalarS8M1
  | rvvSignedMinScalarS8M1
  | rvvStoreS8M1
  deriving BEq, DecidableEq, Repr

inductive EffectKind where
  | pure
  | read
  | write
  | control
  deriving BEq, DecidableEq, Repr

/-- Trusted metadata for one exact intrinsic or primitive spelling. -/
structure OperationDescriptor where
  architecture : Architecture
  family : OperationFamily
  operandTypes : List ValueTag
  resultType : Option ValueTag
  rvvConfigShape : Option RVVConfigShape
  opcode : SemanticOpcode
  effect : EffectKind
  deriving BEq, DecidableEq, Repr

/-- The registry is reviewed code, not data supplied by the untrusted extractor. -/
abbrev TrustedOperationRegistry := String → Option OperationDescriptor

inductive IntegerGateFailure where
  | malformedKernelIR
  | malformedType (site : String) (valueType : ValueTag)
  | floatingPointType (site : String) (valueType : ValueTag)
  | unknownOperation (nodeId : Nat) (spelling : String)
  | descriptorMismatch (nodeId : Nat) (spelling : String)
  | floatingPointOperation (nodeId : Nat) (spelling : String)
  | unsupportedOperation (nodeId : Nat) (spelling : String)
  | scalableVectorOutsideRVV (nodeId : Nat) (spelling : String)
  | missingRVVConfig (nodeId : Nat) (spelling : String)
  | unexpectedRVVConfig (nodeId : Nat) (spelling : String)
  | malformedRVVConfig (nodeId : Nat) (config : RVVVectorConfig)
  | rvvConfigMismatch (nodeId : Nat) (spelling : String)
      (expected : RVVConfigShape) (actual : RVVVectorConfig)
  deriving BEq, DecidableEq, Repr

private def checkIntegerType (site : String) (valueType : ValueTag) :
    Except IntegerGateFailure Unit :=
  if valueType.isWellFormed then
    if valueType.isFloating then
      .error (.floatingPointType site valueType)
    else
      .ok ()
  else
    .error (.malformedType site valueType)

private def checkIntegerTypes (site : String) : List ValueTag → Except IntegerGateFailure Unit
  | [] => .ok ()
  | valueType :: rest => do
      checkIntegerType site valueType
      checkIntegerTypes site rest

private def checkParameters : List Parameter → Except IntegerGateFailure Unit
  | [] => .ok ()
  | parameter :: rest => do
      checkIntegerType ("parameter:" ++ parameter.name) parameter.valueType
      checkParameters rest

private def descriptorMatches (operation : Operation) (descriptor : OperationDescriptor) : Bool :=
  operation.operation.architecture == descriptor.architecture &&
    operation.operation.family == descriptor.family &&
    operation.operandTypes == descriptor.operandTypes &&
    operation.resultType == descriptor.resultType

private def checkRVVConfig (operation : Operation) (descriptor : OperationDescriptor) :
    Except IntegerGateFailure Unit :=
  match descriptor.rvvConfigShape, operation.rvvConfig with
  | some _, none => throw (.missingRVVConfig operation.nodeId operation.operation.spelling)
  | none, some _ => throw (.unexpectedRVVConfig operation.nodeId operation.operation.spelling)
  | some expected, some config =>
      if config.isWellFormed then
        unless expected.matches config do
          throw (.rvvConfigMismatch operation.nodeId operation.operation.spelling expected config)
      else
        throw (.malformedRVVConfig operation.nodeId config)
  | none, none => pure ()

private def checkOperation (registry : TrustedOperationRegistry) (operation : Operation) :
    Except IntegerGateFailure Unit := do
  let descriptor ←
    match registry operation.operation.spelling with
    | none => throw (.unknownOperation operation.nodeId operation.operation.spelling)
    | some descriptor => pure descriptor
  unless descriptorMatches operation descriptor do
    throw (.descriptorMismatch operation.nodeId operation.operation.spelling)
  match descriptor.family with
  | .floatingPoint =>
      throw (.floatingPointOperation operation.nodeId operation.operation.spelling)
  | .unsupported =>
      throw (.unsupportedOperation operation.nodeId operation.operation.spelling)
  | .integer | .mask | .memory | .control | .conversion => pure ()
  checkIntegerTypes ("operand:" ++ toString operation.nodeId) operation.operandTypes
  match operation.resultType with
  | none => pure ()
  | some valueType => checkIntegerType ("result:" ++ toString operation.nodeId) valueType
  let resultIsScalable :=
    match operation.resultType with
    | none => false
    | some valueType => valueType.isScalableVector
  if operation.operandTypes.any ValueTag.isScalableVector || resultIsScalable then
    if descriptor.architecture != .rvv then
      throw (.scalableVectorOutsideRVV operation.nodeId operation.operation.spelling)
    match descriptor.rvvConfigShape with
    | none => throw (.descriptorMismatch operation.nodeId operation.operation.spelling)
    | some _ => pure ()
  checkRVVConfig operation descriptor

private def checkOperations (registry : TrustedOperationRegistry) :
    List Operation → Except IntegerGateFailure Unit
  | [] => .ok ()
  | operation :: rest => do
      checkOperation registry operation
      checkOperations registry rest

private def checkBlocks (registry : TrustedOperationRegistry) :
    List BasicBlock → Except IntegerGateFailure Unit
  | [] => .ok ()
  | block :: rest => do
      checkOperations registry block.operations
      checkBlocks registry rest

/--
Fail-closed gate for the integer-only stage. The IR must first pass local graph and typed-reference
checks; then every block and operation is checked against reviewed descriptor metadata.
Floating-point types and operations are rejected even if extractor-supplied tags misclassify them.
-/
def KernelIR.checkIntegerOnly (ir : KernelIR) (registry : TrustedOperationRegistry) :
    Except IntegerGateFailure Unit := do
  unless ir.hasWellFormedReferenceShape do
    throw .malformedKernelIR
  checkParameters ir.parameters
  checkBlocks registry ir.blocks

end Neon2LeanDemo.Production
