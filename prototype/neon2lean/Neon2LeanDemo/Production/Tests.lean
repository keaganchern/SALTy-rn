import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.Production.Tests

def emptyDigest : Sha256Claim := ⟨"00"⟩

def sampleRange : SourceRange :=
  { path := "sample.c"
    beginOffset := 0
    endOffset := 1 }

def emptyCoverage : CoverageManifest :=
  { translationUnitSha256 := emptyDigest
    functionName := "empty"
    functionSource := sampleRange
    expectedNodeCount := 0
    entries := [] }

example : emptyCoverage.isComplete = true := by
  rfl

def readableAllocation : Allocation :=
  { name := "input"
    range := { base := 16, length := 8 }
    readable := true
    writable := false }

def sampleMemory : ByteMemory :=
  { bytes := fun address => BitVec.ofNat 8 address
    allocations := [readableAllocation] }

example : sampleMemory.canReadRange 16 8 = true := by
  decide

example : sampleMemory.canReadRange 23 2 = false := by
  decide

def fpParameter : Parameter :=
  { nodeId := 1
    name := "x"
    valueType := .scalar (.fp .binary32)
    origin := .function
    source := sampleRange }

def fpKernel : KernelIR :=
  { name := "rejected-fp-kernel"
    translationUnitSha256 := emptyDigest
    functionSource := sampleRange
    parameters := [fpParameter]
    entryBlock := 0
    blocks :=
      [{ blockId := 0
         operations := []
         successors := []
         source := sampleRange }] }

example :
    fpKernel.checkIntegerOnly (fun _ => none) =
      .error (.floatingPointType "parameter:x" (.scalar (.fp .binary32))) := by
  rfl

def i8 : ValueTag := .scalar (.int 8 .signed)

def mislabeledFloatOperation : Operation :=
  { nodeId := 2
    operation :=
      { architecture := .rvv
        family := .integer
        spelling := "__riscv_vfadd_vv_f32m1" }
    operandNodes := [1]
    operandTypes := [i8]
    resultType := some i8
    rvvConfig := none
    source := sampleRange }

def mislabeledFloatKernel : KernelIR :=
  { name := "mislabeled-float"
    translationUnitSha256 := emptyDigest
    functionSource := sampleRange
    parameters :=
      [{ nodeId := 1
         name := "x"
         valueType := i8
         origin := .function
         source := sampleRange }]
    entryBlock := 0
    blocks :=
      [{ blockId := 0
         operations := [mislabeledFloatOperation]
         successors := []
         source := sampleRange }] }

def fpDescriptorRegistry : TrustedOperationRegistry
  | "__riscv_vfadd_vv_f32m1" =>
      some
        { architecture := .rvv
          family := .floatingPoint
          operandTypes := [i8]
          resultType := some i8
          rvvConfigShape := none
          opcode := .unavailable
          effect := .pure }
  | _ => none

example :
    mislabeledFloatKernel.checkIntegerOnly fpDescriptorRegistry =
      .error (.descriptorMismatch 2 "__riscv_vfadd_vv_f32m1") := by
  rfl

example :
    mislabeledFloatKernel.checkIntegerOnly (fun _ => none) =
      .error (.unknownOperation 2 "__riscv_vfadd_vv_f32m1") := by
  rfl

def sampleTranslationUnit : SourceArtifact :=
  { role := .translationUnit
    path := "sample.c"
    byteLength := 10
    sha256 := emptyDigest }

def samplePreprocessedUnit : SourceArtifact :=
  { role := .preprocessedUnit
    path := "sample.i"
    byteLength := 10
    sha256 := emptyDigest }

def sampleBuild : BuildProvenance :=
  { frontendName := "clang"
    frontendVersion := "pinned"
    targetTriple := "test"
    languageStandard := "c11"
    abi := "test"
    endianness := .little
    defines := []
    includePaths := []
    compilerFlags := [] }

def falselyClaimedCoverage : CoverageManifest :=
  { translationUnitSha256 := emptyDigest
    functionName := "one-operation"
    functionSource := sampleRange
    expectedNodeCount := 2
    entries :=
      [{ astNodeId := 0
         kind := "CompoundStmt"
         source := sampleRange
         disposition := .translated [.block 0] },
       { astNodeId := 1
         kind := "CallExpr"
         source := sampleRange
         disposition := .translated [.operation 99] }] }

def falselyClaimedEnvelope : ArtifactEnvelope :=
  { schemaVersion := 1
    operationRegistryId := "test-registry-v1"
    translationUnit := sampleTranslationUnit
    preprocessedUnit := samplePreprocessedUnit
    headers := []
    build := sampleBuild
    extractorName := "test"
    extractorVersion := "1"
    coverage := falselyClaimedCoverage }

def correctlyClaimedEnvelope : ArtifactEnvelope :=
  { falselyClaimedEnvelope with
    coverage :=
      { falselyClaimedCoverage with
        entries :=
          [{ astNodeId := 0
             kind := "CompoundStmt"
             source := sampleRange
             disposition := .translated [.block 0] },
           { astNodeId := 1
             kind := "CallExpr"
             source := sampleRange
             disposition := .translated [.operation 2] }] } }

def oneOperationKernel : KernelIR :=
  { name := "one-operation"
    translationUnitSha256 := emptyDigest
    functionSource := sampleRange
    parameters := []
    entryBlock := 0
    blocks :=
      [{ blockId := 0
         operations :=
           [{ nodeId := 2
              operation :=
                { architecture := .neutral
                  family := .control
                  spelling := "return" }
              operandNodes := []
              operandTypes := []
              resultType := none
              rvvConfig := none
              source := sampleRange }]
         successors := []
         source := sampleRange }] }

def returnDescriptorRegistry : TrustedOperationRegistry
  | "return" =>
      some
        { architecture := .neutral
          family := .control
          operandTypes := []
          resultType := none
          rvvConfigShape := none
          opcode := .return
          effect := .control }
  | _ => none

example : oneOperationKernel.checkIntegerOnly returnDescriptorRegistry = .ok () := by
  rfl

example : falselyClaimedEnvelope.claimsFullTranslation = true := by
  decide

example : oneOperationKernel.hasConsistentCoverageBinding falselyClaimedEnvelope = false := by
  decide

example : oneOperationKernel.hasConsistentCoverageBinding correctlyClaimedEnvelope = true := by
  decide

def duplicateBlockKernel : KernelIR :=
  { oneOperationKernel with
    blocks := oneOperationKernel.blocks ++ oneOperationKernel.blocks }

example : duplicateBlockKernel.hasWellFormedReferenceShape = false := by
  decide

def forwardReferenceKernel : KernelIR :=
  { oneOperationKernel with
    name := "forward-reference"
    blocks :=
      [{ blockId := 0
         operations :=
           [{ nodeId := 2
              operation :=
                { architecture := .neutral, family := .integer, spelling := "forward-use" }
              operandNodes := [3]
              operandTypes := [i8]
              resultType := some i8
              rvvConfig := none
              source := sampleRange },
            { nodeId := 3
              operation :=
                { architecture := .neutral, family := .integer, spelling := "later-def" }
              operandNodes := []
              operandTypes := []
              resultType := some i8
              rvvConfig := none
              source := sampleRange }]
         successors := []
         source := sampleRange }] }

example : forwardReferenceKernel.hasWellFormedReferenceShape = true := by
  decide

example : forwardReferenceKernel.hasSingleBlockUseOrder = false := by
  decide

def selfReferenceKernel : KernelIR :=
  { forwardReferenceKernel with
    name := "self-reference"
    blocks :=
      [{ blockId := 0
         operations :=
           [{ nodeId := 2
              operation :=
                { architecture := .neutral, family := .integer, spelling := "self-use" }
              operandNodes := [2]
              operandTypes := [i8]
              resultType := some i8
              rvvConfig := none
              source := sampleRange }]
         successors := []
         source := sampleRange }] }

example : selfReferenceKernel.hasWellFormedReferenceShape = true := by
  decide

example : selfReferenceKernel.hasSingleBlockUseOrder = false := by
  decide

def u64 : ValueTag := .scalar (.int 64 .unsigned)

def i8m8 : ValueTag := .vector (.scalable .m8) (.int 8 .signed)

def rvvI8M8Parameters : List Parameter :=
  [{ nodeId := 1, name := "vl", valueType := u64,
     origin := .function, source := sampleRange },
   { nodeId := 2, name := "vector", valueType := i8m8,
     origin := .function, source := sampleRange },
   { nodeId := 3, name := "scalar", valueType := i8,
     origin := .function, source := sampleRange }]

def mismatchedRVVOperation : Operation :=
  { nodeId := 4
    operation :=
      { architecture := .rvv
        family := .integer
        spelling := "__riscv_vmax_vx_i8m8" }
    operandNodes := [2, 3]
    operandTypes := [i8m8, i8]
    resultType := some i8m8
    rvvConfig := some { sew := 64, lmul := .mf8, activeVLNode := 1 }
    source := sampleRange }

def mismatchedRVVKernel : KernelIR :=
  { name := "mismatched-rvv-config"
    translationUnitSha256 := emptyDigest
    functionSource := sampleRange
    parameters := rvvI8M8Parameters
    entryBlock := 0
    blocks :=
      [{ blockId := 0
         operations := [mismatchedRVVOperation]
         successors := []
         source := sampleRange }] }

def rvvI8M8DescriptorRegistry : TrustedOperationRegistry
  | "__riscv_vmax_vx_i8m8" =>
      some
        { architecture := .rvv
          family := .integer
          operandTypes := [i8m8, i8]
          resultType := some i8m8
          rvvConfigShape := some { sew := 8, lmul := .m8 }
          opcode := .unavailable
          effect := .pure }
  | _ => none

example :
    mismatchedRVVKernel.checkIntegerOnly rvvI8M8DescriptorRegistry =
      .error
        (.rvvConfigMismatch 4 "__riscv_vmax_vx_i8m8"
          { sew := 8, lmul := .m8 }
          { sew := 64, lmul := .mf8, activeVLNode := 1 }) := by
  rfl

def matchingRVVKernel : KernelIR :=
  { mismatchedRVVKernel with
    name := "matching-rvv-config"
    blocks :=
      [{ blockId := 0
         operations :=
           [{ mismatchedRVVOperation with
              rvvConfig := some { sew := 8, lmul := .m8, activeVLNode := 1 } }]
         successors := []
         source := sampleRange }] }

example : matchingRVVKernel.checkIntegerOnly rvvI8M8DescriptorRegistry = .ok () := by
  rfl

end Neon2LeanDemo.Production.Tests
