import Transpiler.Parser
import Transpiler.Rules

namespace Transpiler

abbrev RuleTable := List (String × Function)

/-- Parse the checked-in rule sources with the same C parser as user programs. -/
def loadRules : Except String RuleTable := ruleSources.mapM fun (name, source) => do
  let p ← (parseC source).mapError (fun e => s!"lowering rule {name}: {e}")
  match p.items with
  | [.function f] =>
    unless f.name == name do throw s!"rule name mismatch: {name}"
    return (name, f)
  | _ => throw s!"rule {name} is not one function"

private structure LowerState where
  env : List (String × CType) := []
  used : List String := []
  rules : RuleTable := []
  functions : List (String × CType) := []
  setters : List Function := []
  deriving Inhabited

private abbrev L := StateT LowerState (Except String)
private def helperName (n : String) := "salty_rvv_" ++ n

def lowerType (ty : CType) : Except String CType := do
  match ty.base with
  | .vector ⟨.neon, n⟩ =>
    match vectorAliases.lookup n with
    | some target => return { ty with base := .vector ⟨.rvv, target⟩ }
    | none => throw s!"unsupported NEON vector type: {n}"
  | .named "float32_t" => return { ty with base := .named "float" }
  | .named "float64_t" => return { ty with base := .named "double" }
  | _ => return ty

private def stem (s : String) : String :=
  ((s.replace "vuint" "u").replace "vint" "i").replace "vfloat" "f" |>.replace "_t" ""

private def rvvType (s : String) : CType :=
  let typePrefix := if s.startsWith "u" then "vuint" else if s.startsWith "i" then "vint" else "vfloat"
  { base := .vector ⟨.rvv, typePrefix ++ (s.drop 1).toString ++ "_t"⟩ }

private def tupleParts (ty : CType) : Option (String × String × Nat) := do
  if !ty.pointers.isEmpty then none else pure ()
  let .vector v := ty.base | none
  let rvv ← if v.dialect == .neon then vectorAliases.lookup v.spelling else some v.spelling
  let parts := (stem rvv).splitOn "x"
  if parts.length != 2 then none else do
    let count ← parts[1]!.toNat?
    pure (stem rvv, parts[0]!, count)

private def tupleAccess (base index : Expr) : L (String × String) := do
  let .ident name := base | throw "tuple .val[] access requires a local variable"
  let some ty := (← get).env.lookup name | throw s!"unknown tuple variable {name}"
  let some (tuple, elem, count) := tupleParts ty | throw s!"{name} has no supported vector tuple type"
  let .literal text := index | throw "RVV tuple indexes must be integer constants"
  let some i := text.toNat? | throw "RVV tuple indexes must be decimal integer constants"
  unless i < count do throw s!"tuple index {i} is out of bounds for {name}"
  return (tuple, elem)

private def requireRule (name : String) (arity : Nat) : L Unit := do
  let some f := (← get).rules.lookup name | throw s!"unsupported NEON intrinsic: {name}"
  unless f.params.length == arity do
    throw s!"{name}: expected {f.params.length} arguments, got {arity}"
  modify fun s => { s with used := if s.used.contains name then s.used else s.used ++ [name] }

private def lowerSizeofType (ty : CType) : Except String Expr := do
  if let .vector ⟨.neon, name⟩ := ty.base then
    if ty.pointers.isEmpty then
      unless (vectorAliases.lookup name).isSome do throw s!"unsupported sizeof vector type {name}"
      let pieces := (name.replace "_t" "").splitOn "x"
      let bitsText := String.ofList ((pieces.headD "").toList.filter Char.isDigit)
      let some bits := bitsText.toNat? | throw s!"invalid vector type {name}"
      let mut bytes := bits / 8
      for n in pieces.tail do
        let some count := n.toNat? | throw s!"invalid vector type {name}"
        bytes := bytes * count
      -- sizeof has type size_t, not int, even when its value is constant.
      return .cast { base := .named "size_t" } (.literal (toString bytes))
  return .sizeofType (← lowerType ty)

/-- Recover source vector types for sizeof without evaluating its operand.
    Scalar arithmetic conversions remain the target C compiler's responsibility. -/
private partial def sourceType : Expr → L (Option CType)
  | .ident n => return (← get).env.lookup n
  | .cast ty _ => return some ty
  | .intrinsic (.neon n) _ => return ((← get).rules.lookup n).map (·.result)
  | .call (.ident n) _ => return (← get).functions.lookup n
  | .index (.member base "val" false) idx => do
    let (_, elem) ← tupleAccess base idx
    let some ty ← sourceType base | return none
    let .vector v := ty.base | return none
    if v.dialect == .neon then
      let name := String.intercalate "x" ((v.spelling.splitOn "x").take 2) ++ "_t"
      return some { base := namedType name }
    return some (rvvType elem)
  | .unary "*" e | .index e _ => do
    let some ty ← sourceType e | return none
    if ty.pointers.isEmpty then return none
    return some { ty with pointers := ty.pointers.dropLast }
  | .unary "&" e => do
    return (← sourceType e).map fun ty => { ty with pointers := ty.pointers ++ [[]] }
  | .unary "sizeof" _ | .sizeofType _ => return some { base := .named "size_t" }
  | .unary "!" _ => return none
  | .unary _ e | .postfix _ e => sourceType e
  | .binary "," _ b => sourceType b
  | .binary "=" a _ => sourceType a
  | .binary _ a b | .conditional _ a b => do
    -- Only vector operands need replacement; do not guess scalar result types.
    for e in [a, b] do
      if let some ty ← sourceType e then
        if ty.pointers.isEmpty then
          if let .vector _ := ty.base then return some ty
    return none
  | _ => return none

private def tupleSetter (tuple elem : String) (idx : Expr) : L String := do
  let .literal index := idx | throw "tuple setter requires a constant index"
  let name := helperName s!"set_{tuple}_{index}"
  unless (← get).setters.any (·.name == name) do
    let tupleTy := rvvType tuple
    let elemTy := rvvType elem
    let target := Expr.unary "*" (.ident "target")
    let setter : Function := ⟨{ elemTy with qualifiers := ["static", "inline"] }, name,
      [{ type := { tupleTy with pointers := [[]] }, name := "target" },
       { type := elemTy, name := "value" }], [],
      some (.block [
        .expr (.binary "=" target (.intrinsic (.rvv s!"__riscv_vset_v_{elem}_{tuple}")
          [target, idx, .ident "value"])),
        .returnStmt (some (.ident "value"))])⟩
    modify fun s => { s with setters := s.setters ++ [setter] }
  return name

private partial def lowerExpr : Expr → L Expr
  | .ident n => do
    if n.startsWith "salty_rvv_" then throw "salty_rvv_ is reserved for generated identifiers"
    return .ident (if n == "test_neon" then "test_rvv" else n)
  | .intrinsic (.neon n) args => do
    requireRule n args.length
    return .call (.ident (helperName n)) (← args.mapM lowerExpr)
  | .intrinsic (.rvv n) args => return .intrinsic (.rvv n) (← args.mapM lowerExpr)
  | .binary "=" (.index (.member base "val" false) idx) rhs => do
    let (tuple, elem) ← tupleAccess base idx
    let value ← lowerExpr rhs
    let setter ← tupleSetter tuple elem idx
    -- Read/update the tuple inside the helper, after the RHS is evaluated.
    -- This also preserves nested writes to different elements of the same tuple.
    return .call (.ident setter) [.unary "&" (← lowerExpr base), value]
  | .index (.member base "val" false) idx => do
    let (tuple, elem) ← tupleAccess base idx
    return .intrinsic (.rvv s!"__riscv_vget_v_{tuple}_{elem}") [base, idx]
  | .unary "sizeof" e => do
    if let some ty ← sourceType e then
      if let .vector _ := ty.base then
        if ty.pointers.isEmpty then return ← lowerSizeofType ty
    return .unary "sizeof" (← lowerExpr e)
  | .unary op e => return .unary op (← lowerExpr e)
  | .postfix op e => return .postfix op (← lowerExpr e)
  | .binary op a b => return .binary op (← lowerExpr a) (← lowerExpr b)
  | .conditional c y n => return .conditional (← lowerExpr c) (← lowerExpr y) (← lowerExpr n)
  | .call f args => return .call (← lowerExpr f) (← args.mapM lowerExpr)
  | .index b i => return .index (← lowerExpr b) (← lowerExpr i)
  | .member b f a => return .member (← lowerExpr b) f a
  | .cast ty e => return .cast (← lowerType ty) (← lowerExpr e)
  | .sizeofType ty => lowerSizeofType ty
  | .initList es => return .initList (← es.mapM lowerExpr)
  | e => pure e

private def lowerVar (v : VarDecl) : L VarDecl := do
  if v.name.startsWith "salty_rvv_" then throw "salty_rvv_ is reserved for generated identifiers"
  if !v.dimensions.isEmpty then
    if let .vector _ := v.type.base then throw "arrays of sizeless RVV vectors are unsupported"
  let ty ← lowerType v.type
  let dimensions ← v.dimensions.mapM (fun d => d.mapM lowerExpr)
  -- The declared name is in scope in its own initializer (including sizeof).
  modify fun s => { s with env := (v.name, v.type) :: s.env }
  let mut value ← v.value.mapM lowerExpr
  -- A partial tuple assignment must not pass an uninitialized C value to vset.
  if value.isNone then
    if let some (tuple, elem, count) := tupleParts ty then
      let bitsText := String.ofList ((elem.splitOn "m").headD "" |>.toList.filter Char.isDigit)
      let bits := bitsText.toNat?.getD 32
      let name := if elem.startsWith "f" then s!"__riscv_vfmv_v_f_{elem}" else s!"__riscv_vmv_v_x_{elem}"
      let zero : Expr := .intrinsic (.rvv name) [.literal "0", .literal (toString (128 / bits))]
      value := some (.intrinsic (.rvv s!"__riscv_vcreate_v_{tuple}") (List.replicate count zero))
  return { v with type := ty, value, dimensions }

private partial def lowerStmt : Stmt → L Stmt
  | .block ss => do
    let env := (← get).env
    let result ← ss.mapM lowerStmt
    modify fun s => { s with env }
    return .block result
  | .decl vs => return .decl (← vs.mapM lowerVar)
  | .expr e => return .expr (← lowerExpr e)
  | .ifThen c y n => do
    let cond ← lowerExpr c
    let env := (← get).env
    let yes ← lowerStmt y
    modify fun s => { s with env }
    let no ← n.mapM lowerStmt
    modify fun s => { s with env }
    return .ifThen cond yes no
  | .whileLoop c b => return .whileLoop (← lowerExpr c) (← lowerStmt b)
  | .doWhile b c => return .doWhile (← lowerStmt b) (← lowerExpr c)
  | .forLoop i c s b => do
    let env := (← get).env
    let init ← match i with
      | .empty => pure ForInit.empty
      | .expr e => ForInit.expr <$> lowerExpr e
      | .decl vs => ForInit.decl <$> vs.mapM lowerVar
    let result := Stmt.forLoop init (← c.mapM lowerExpr) (← s.mapM lowerExpr) (← lowerStmt b)
    modify fun s => { s with env }
    return result
  | .returnStmt e => return .returnStmt (← e.mapM lowerExpr)
  | .directive t => throw s!"preprocessing directive in function: {t}; select/preprocess source first"
  | s => pure s

private def lowerFunction (f : Function) (isRule : Bool := false) : L Function := do
  unless isRule do
    if f.name.startsWith "salty_rvv_" then throw "salty_rvv_ is reserved for generated functions"
  let env := (← get).env
  -- Parameters must not receive the default initialization used for tuple locals.
  let params ← f.params.mapM fun v => do
    if v.name.startsWith "salty_rvv_" then throw "salty_rvv_ is reserved for generated identifiers"
    modify fun s => { s with env := (v.name, v.type) :: s.env }
    pure { v with type := ← lowerType v.type }
  let body ← f.body.mapM lowerStmt
  modify fun s => { s with env }
  let result ← lowerType f.result
  let name := if isRule then helperName f.name else if f.name == "test_neon" then "test_rvv" else f.name
  return ⟨result, name, params, f.attributes, body⟩

private partial def lowerFields (fields : List RecordField) : L (List RecordField) :=
  fields.mapM fun field => match field with
    | .vars vs => do
      for v in vs do
        if let .vector _ := v.type.base then throw "vector fields in C records are unsupported"
      pure (.vars vs)
    | .nested k t fs n => return .nested k t (← lowerFields fs) n
    | .directive t => throw s!"unresolved record directive: {t}"

private def lowerItem : TopLevel → L TopLevel
  | .function f => return .function (← lowerFunction f)
  | .globals vs => return .globals (← vs.mapM lowerVar)
  | .record k t fs => return .record k t (← lowerFields fs)
  | .directive t => do
    if t.startsWith "#include" && (t.contains '"' || t.contains '<') then
      if (t.splitOn "arm_neon.h").length > 1 then return .directive "#include <riscv_vector.h>"
      return .directive t
    throw s!"unsupported top-level directive: {t}; preprocess first"

/-- Pure syntactic lowering. Helpers contain parsed RVV ASTs, not opaque C text.
    Only helpers transitively used by this program are emitted. -/
def transpile (rules : RuleTable) (program : Program) : Except String Program := do
  let action : L Program := do
    let items ← program.items.mapM lowerItem
    let mut helpers := []
    let mut doneNames := []
    let mut cursor := 0
    while cursor < (← get).used.length do
      let name := (← get).used[cursor]!
      cursor := cursor + 1
      unless doneNames.contains name do
        let some f := rules.lookup name | throw s!"missing dependency {name}"
        helpers := helpers ++ [← lowerFunction f true]
        doneNames := doneNames ++ [name]
    -- Prototypes make helper order independent of dependency order.
    helpers := (← get).setters ++ helpers
    let prototypes := helpers.map fun f => TopLevel.function { f with body := none }
    let includes := items.filter fun x => match x with | .directive _ => true | _ => false
    let body := items.filter fun x => match x with | .directive _ => false | _ => true
    return ⟨[.directive "#include <stddef.h>", .directive "#include <riscv_vector.h>", .directive "#pragma STDC FP_CONTRACT OFF"] ++
      includes ++ prototypes ++ helpers.map TopLevel.function ++ body⟩
  let functions := program.items.filterMap fun item => match item with
    | .function f => some (f.name, f.result)
    | _ => none
  return (← action.run { rules, functions }).1

end Transpiler
