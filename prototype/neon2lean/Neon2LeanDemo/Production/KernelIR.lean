import Neon2LeanDemo.Production.Artifact
import Neon2LeanDemo.Production.Types

namespace Neon2LeanDemo.Production

inductive ParameterOrigin where
  | function
  | structuredControlInput
  deriving BEq, DecidableEq, Repr

structure Parameter where
  nodeId : Nat
  name : String
  valueType : ValueTag
  origin : ParameterOrigin
  source : SourceRange
  deriving BEq, DecidableEq, Repr

/-- A flat, typed operation that retains its exact source spelling and source range. -/
structure Operation where
  nodeId : Nat
  operation : OperationTag
  operandNodes : List Nat
  operandTypes : List ValueTag
  resultType : Option ValueTag
  rvvConfig : Option RVVVectorConfig
  source : SourceRange
  deriving BEq, DecidableEq, Repr

structure BasicBlock where
  blockId : Nat
  operations : List Operation
  successors : List Nat
  source : SourceRange
  deriving BEq, DecidableEq, Repr

/-- Small control-flow IR. Memory effects remain explicit operations, not hidden evaluation. -/
structure KernelIR where
  name : String
  translationUnitSha256 : Sha256Claim
  functionSource : SourceRange
  parameters : List Parameter
  entryBlock : Nat
  blocks : List BasicBlock
  deriving BEq, DecidableEq, Repr

def findBlock? : List BasicBlock → Nat → Option BasicBlock
  | [], _ => none
  | block :: rest, id =>
      if block.blockId = id then some block else findBlock? rest id

def KernelIR.block? (ir : KernelIR) (id : Nat) : Option BasicBlock :=
  findBlock? ir.blocks id

private def idsUnique : List Nat → Bool
  | [] => true
  | nodeId :: rest => !rest.contains nodeId && idsUnique rest

def KernelIR.parameterNodeIds (ir : KernelIR) : List Nat :=
  ir.parameters.map Parameter.nodeId

def KernelIR.operationNodeIds (ir : KernelIR) : List Nat :=
  ir.blocks.flatMap fun block => block.operations.map Operation.nodeId

def KernelIR.blockIds (ir : KernelIR) : List Nat :=
  ir.blocks.map BasicBlock.blockId

def KernelIR.valueNodeIds (ir : KernelIR) : List Nat :=
  ir.parameterNodeIds ++ ir.blocks.flatMap fun block =>
    block.operations.filterMap fun operation => operation.resultType.map fun _ => operation.nodeId

private def findParameterType? : List Parameter → Nat → Option ValueTag
  | [], _ => none
  | parameter :: rest, nodeId =>
      if parameter.nodeId = nodeId then some parameter.valueType else findParameterType? rest nodeId

private def findOperationResultType? : List BasicBlock → Nat → Option ValueTag
  | [], _ => none
  | block :: rest, nodeId =>
      match block.operations.find? fun operation => operation.nodeId = nodeId with
      | some operation => operation.resultType
      | none => findOperationResultType? rest nodeId

def KernelIR.valueType? (ir : KernelIR) (nodeId : Nat) : Option ValueTag :=
  match findParameterType? ir.parameters nodeId with
  | some valueType => some valueType
  | none => findOperationResultType? ir.blocks nodeId

private def Operation.hasValidReferences (operation : Operation) (ir : KernelIR) : Bool :=
  operation.operandNodes.length == operation.operandTypes.length &&
    (operation.operandNodes.zip operation.operandTypes).all (fun pair =>
      ir.valueType? pair.1 == some pair.2) &&
    (match operation.rvvConfig with
    | none => true
    | some config =>
        match ir.valueType? config.activeVLNode with
        | some (.scalar (.int _ _)) => true
        | _ => false)

private def Operation.hasWellFormedTypes (operation : Operation) : Bool :=
  operation.operandTypes.all ValueTag.isWellFormed &&
    (match operation.resultType with
    | none => true
    | some valueType => valueType.isWellFormed) &&
    (match operation.rvvConfig with
    | none => true
    | some config => config.isWellFormed)

private def Operation.isWithin (operation : Operation) (artifact : SourceArtifact) : Bool :=
  operation.source.isWithin artifact

private def BasicBlock.isWithin (block : BasicBlock) (artifact : SourceArtifact) : Bool :=
  block.source.isWithin artifact &&
    block.operations.all fun operation => operation.isWithin artifact

private def KernelIR.hasDefinedSuccessors (ir : KernelIR) : Bool :=
  ir.blocks.all fun block => block.successors.all fun successor => ir.blockIds.contains successor

private def KernelIR.hasValidReferences (ir : KernelIR) : Bool :=
  ir.blocks.all fun block => block.operations.all fun operation =>
    operation.hasValidReferences ir

private def KernelIR.hasWellFormedTypes (ir : KernelIR) : Bool :=
  ir.parameters.all (fun parameter => parameter.valueType.isWellFormed) &&
    ir.blocks.all fun block => block.operations.all Operation.hasWellFormedTypes

def KernelIR.nodeRefs (ir : KernelIR) : List IRNodeRef :=
  ir.parameterNodeIds.map IRNodeRef.parameter ++
    ir.operationNodeIds.map IRNodeRef.operation ++
    ir.blockIds.map IRNodeRef.block

private def Operation.referencesAvailable (operation : Operation) (defined : List Nat) : Bool :=
  operation.operandNodes.all defined.contains &&
    match operation.rvvConfig with
    | none => true
    | some config => defined.contains config.activeVLNode

private def operationsHaveUseOrder : List Nat -> List Operation -> Bool
  | _, [] => true
  | defined, operation :: rest =>
      operation.referencesAvailable defined &&
        let nextDefined :=
          if operation.resultType.isSome then operation.nodeId :: defined else defined
        operationsHaveUseOrder nextDefined rest

/--
Strict local SSA discipline used by the first executable slice. The slice has one
block, so every operation result must be defined earlier in that block. General CFG
dominance and block arguments remain future schema work.
-/
def KernelIR.hasSingleBlockUseOrder (ir : KernelIR) : Bool :=
  match ir.blocks with
  | [block] =>
      block.blockId == ir.entryBlock && block.successors.isEmpty &&
        operationsHaveUseOrder ir.parameterNodeIds block.operations
  | _ => false

/--
Local graph and typed-reference checks independent of extractor classifications.
Dominance, use-before-definition, and loop-carried values remain executor obligations.
-/
def KernelIR.hasWellFormedReferenceShape (ir : KernelIR) : Bool :=
  idsUnique ir.blockIds &&
    idsUnique (ir.parameterNodeIds ++ ir.operationNodeIds) &&
    ir.blockIds.contains ir.entryBlock &&
    ir.hasDefinedSuccessors &&
    ir.hasValidReferences &&
    ir.hasWellFormedTypes &&
    ir.functionSource.isWellFormed &&
    ir.parameters.all (fun parameter => parameter.source.isWellFormed) &&
    ir.blocks.all fun block =>
      block.source.isWellFormed &&
        block.operations.all fun operation => operation.source.isWellFormed

private def KernelIR.rangesWithin (ir : KernelIR) (artifact : SourceArtifact) : Bool :=
  ir.functionSource.isWithin artifact &&
    ir.parameters.all (fun parameter => parameter.source.isWithin artifact) &&
    ir.blocks.all fun block => block.isWithin artifact

/--
Structural coverage consistency. Unlike `ArtifactEnvelope.claimsFullTranslation`, this
checks that every claimed reference exists in the IR and every IR node is covered. It
does not prove that lowering preserved C semantics. CI must also recompute file digests.
-/
def KernelIR.hasConsistentCoverageBinding (ir : KernelIR) (envelope : ArtifactEnvelope) : Bool :=
  let translatedRefs := envelope.coverage.translatedNodeRefs
  ir.translationUnitSha256 == envelope.translationUnit.sha256 &&
    ir.name == envelope.coverage.functionName &&
    ir.functionSource == envelope.coverage.functionSource &&
    envelope.isInternallyBound &&
    envelope.coverage.claimsFullTranslation &&
    ir.hasWellFormedReferenceShape &&
    ir.rangesWithin envelope.translationUnit &&
    translatedRefs.all ir.nodeRefs.contains &&
    ir.nodeRefs.all translatedRefs.contains

end Neon2LeanDemo.Production
