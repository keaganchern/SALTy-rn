import Lean
import Lean.Util.CollectAxioms

open Lean

private def frame (value : String) : String :=
  s!"{value.utf8ByteSize}:{value}"

private partial def encodeName : Name → String
  | .anonymous => "N"
  | .str parent suffix => "S" ++ frame (encodeName parent) ++ frame suffix
  | .num parent suffix => "U" ++ frame (encodeName parent) ++ frame (toString suffix)

private partial def encodeLevel : Level → Except String String
  | .zero => pure "z"
  | .succ level => return "s" ++ frame (← encodeLevel level)
  | .max left right =>
      return "m" ++ frame (← encodeLevel left) ++ frame (← encodeLevel right)
  | .imax left right =>
      return "i" ++ frame (← encodeLevel left) ++ frame (← encodeLevel right)
  | .param name => pure <| "p" ++ frame (encodeName name)
  | .mvar _ => throw "unresolved universe metavariable"

private def encodeBinderInfo : BinderInfo → String
  | .default => "d"
  | .implicit => "i"
  | .strictImplicit => "s"
  | .instImplicit => "c"

private partial def encodeExpr : Expr → Except String String
  | .bvar index => pure <| "b" ++ frame (toString index)
  | .fvar _ => throw "free variable in checked theorem type"
  | .mvar _ => throw "metavariable in checked theorem type"
  | .sort level => return "s" ++ frame (← encodeLevel level)
  | .const name levels => do
      let encodedLevels ← levels.mapM encodeLevel
      return "c" ++ frame (encodeName name) ++ frame (String.join encodedLevels)
  | .app fn arg => return "a" ++ frame (← encodeExpr fn) ++ frame (← encodeExpr arg)
  | .lam _ type body binderInfo =>
      return "l" ++ frame (encodeBinderInfo binderInfo) ++
        frame (← encodeExpr type) ++ frame (← encodeExpr body)
  | .forallE _ type body binderInfo =>
      return "f" ++ frame (encodeBinderInfo binderInfo) ++
        frame (← encodeExpr type) ++ frame (← encodeExpr body)
  | .letE _ type value body nondep =>
      return "e" ++ frame (toString nondep) ++ frame (← encodeExpr type) ++
        frame (← encodeExpr value) ++ frame (← encodeExpr body)
  | .lit (.natVal value) => pure <| "n" ++ frame (toString value)
  | .lit (.strVal value) => pure <| "t" ++ frame value
  | .mdata _ expr => encodeExpr expr
  | .proj typeName index struct =>
      return "j" ++ frame (encodeName typeName) ++ frame (toString index) ++
        frame (← encodeExpr struct)

private def auditJson
    (env : Environment) (moduleName theoremName : Name) : Except String Json := do
  let some moduleIdx := env.getModuleIdx? moduleName
    | throw s!"module not present in checked environment: {moduleName}"
  if env.getModuleIdxFor? theoremName != some moduleIdx then
    throw s!"theorem is not owned by requested module: {theoremName}"
  let some info := env.checked.get.find? theoremName
    | throw s!"theorem not found in checked environment: {theoremName}"
  let .thmInfo declaration := info
    | throw s!"declaration is not a theorem: {theoremName}"
  let typeEncoding ← encodeExpr declaration.type
  let (_, state) := ((CollectAxioms.collect theoremName).run env).run {}
  let axioms := state.axioms.toList.map toString |>.mergeSort
  pure <| Json.mkObj [
    ("schema_version", toJson 1),
    ("module", toJson (toString moduleName)),
    ("theorem", toJson (toString theoremName)),
    ("level_parameters", toJson (declaration.levelParams.map toString)),
    ("type_encoding", toJson typeEncoding),
    ("axioms", toJson axioms)
  ]

def main (args : List String) : IO UInt32 := do
  let [moduleText, theoremText] := args
    | throw <| IO.userError "usage: ProofAudit MODULE THEOREM"
  initSearchPath (← findSysroot)
  let moduleName := moduleText.toName
  let theoremName := theoremText.toName
  if moduleName.isAnonymous || theoremName.isAnonymous then
    throw <| IO.userError "module and theorem names must be non-anonymous"
  let env ← importModules #[{ module := moduleName }] {} 0
  match auditJson env moduleName theoremName with
  | .ok result =>
      IO.println <| "SALTYRN_PROOF_AUDIT_V1\t" ++ result.compress
      pure 0
  | .error message => throw <| IO.userError message
