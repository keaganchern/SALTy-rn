namespace Neon2LeanDemo.Production

/-- A recorded digest claim. CI/extraction must recompute it from the named artifact. -/
structure Sha256Claim where
  hex : String
  deriving BEq, DecidableEq, Repr

inductive ArtifactRole where
  | translationUnit
  | preprocessedUnit
  | header
  deriving BEq, DecidableEq, Repr

structure SourceArtifact where
  role : ArtifactRole
  path : String
  byteLength : Nat
  sha256 : Sha256Claim
  deriving BEq, DecidableEq, Repr

structure SourceRange where
  path : String
  beginOffset : Nat
  endOffset : Nat
  deriving BEq, DecidableEq, Repr

def SourceRange.WellFormed (range : SourceRange) : Prop :=
  range.beginOffset ≤ range.endOffset

def SourceRange.isWellFormed (range : SourceRange) : Bool :=
  range.beginOffset ≤ range.endOffset

def SourceRange.isWithin (range : SourceRange) (artifact : SourceArtifact) : Bool :=
  range.path == artifact.path && range.isWellFormed && range.endOffset ≤ artifact.byteLength

inductive Endianness where
  | little
  | big
  deriving BEq, DecidableEq, Repr

/-- Build inputs that can change the Clang AST or the C abstract-machine interpretation. -/
structure BuildProvenance where
  frontendName : String
  frontendVersion : String
  targetTriple : String
  languageStandard : String
  abi : String
  endianness : Endianness
  defines : List String
  includePaths : List String
  compilerFlags : List String
  deriving BEq, DecidableEq, Repr

inductive IRNodeRef where
  | parameter (nodeId : Nat)
  | operation (nodeId : Nat)
  | block (blockId : Nat)
  deriving BEq, DecidableEq, Repr

inductive CoverageDisposition where
  | translated (irNodes : List IRNodeRef)
  | justifiedExclusion (ruleId : String) (reason : String)
  | rejected (reason : String)
  deriving BEq, DecidableEq, Repr

def CoverageDisposition.accepted : CoverageDisposition → Bool
  | .translated nodeIds => !nodeIds.isEmpty
  | .justifiedExclusion _ _ => true
  | .rejected _ => false

def CoverageDisposition.translatedNodeRefs : CoverageDisposition → List IRNodeRef
  | .translated nodeRefs => nodeRefs
  | .justifiedExclusion _ _ | .rejected _ => []

/-- One normalized AST node and its explicit extraction disposition. -/
structure CoverageEntry where
  astNodeId : Nat
  kind : String
  source : SourceRange
  disposition : CoverageDisposition
  deriving BEq, DecidableEq, Repr

private def coverageIdsUnique : List CoverageEntry → Bool
  | [] => true
  | entry :: rest =>
      !(rest.any fun other => other.astNodeId == entry.astNodeId) && coverageIdsUnique rest

/--
The frontend numbers normalized AST nodes densely from zero. Completeness is checkable once
the frontend has supplied `expectedNodeCount`; correspondence with Clang remains a frontend
trust obligation.
-/
structure CoverageManifest where
  translationUnitSha256 : Sha256Claim
  functionName : String
  functionSource : SourceRange
  expectedNodeCount : Nat
  entries : List CoverageEntry
  deriving BEq, DecidableEq, Repr

def CoverageManifest.isComplete (manifest : CoverageManifest) : Bool :=
  !manifest.functionName.isEmpty && manifest.functionSource.isWellFormed &&
    manifest.entries.length == manifest.expectedNodeCount &&
    coverageIdsUnique manifest.entries &&
    manifest.entries.all fun entry =>
      entry.astNodeId < manifest.expectedNodeCount && entry.disposition.accepted

def CoverageDisposition.claimsTranslation : CoverageDisposition → Bool
  | .translated nodeIds => !nodeIds.isEmpty
  | .justifiedExclusion _ _ | .rejected _ => false

def CoverageManifest.translatedNodeRefs (manifest : CoverageManifest) : List IRNodeRef :=
  manifest.entries.flatMap fun entry => entry.disposition.translatedNodeRefs

/-- This checks emitter claims only; the concrete IR relation validates their references. -/
def CoverageManifest.claimsFullTranslation (manifest : CoverageManifest) : Bool :=
  manifest.isComplete && manifest.entries.all fun entry => entry.disposition.claimsTranslation

/-- Everything needed to identify the C artifact and extraction configuration. -/
structure ArtifactEnvelope where
  schemaVersion : Nat
  operationRegistryId : String
  translationUnit : SourceArtifact
  preprocessedUnit : SourceArtifact
  headers : List SourceArtifact
  build : BuildProvenance
  extractorName : String
  extractorVersion : String
  coverage : CoverageManifest
  deriving BEq, DecidableEq, Repr

def ArtifactEnvelope.isInternallyBound (envelope : ArtifactEnvelope) : Bool :=
  envelope.schemaVersion > 0 && !envelope.operationRegistryId.isEmpty &&
    envelope.translationUnit.role == .translationUnit &&
    envelope.preprocessedUnit.role == .preprocessedUnit &&
    envelope.headers.all (fun header => header.role == .header) &&
    envelope.coverage.translationUnitSha256 == envelope.translationUnit.sha256 &&
    envelope.coverage.functionSource.isWithin envelope.translationUnit &&
    envelope.coverage.isComplete &&
    envelope.coverage.entries.all fun entry => entry.source.isWithin envelope.translationUnit

/-- An untrusted emitter claim, deliberately not named or exposed as translation completeness. -/
def ArtifactEnvelope.claimsFullTranslation (envelope : ArtifactEnvelope) : Bool :=
  envelope.isInternallyBound && envelope.coverage.claimsFullTranslation

end Neon2LeanDemo.Production
