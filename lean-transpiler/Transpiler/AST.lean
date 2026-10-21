import Lean

namespace Transpiler

/- Syntax only. No interpretation, equivalence axioms, or proof claims.
   Scalar/control-flow syntax is shared by both vector dialects. -/
inductive Dialect where
  | neon | rvv
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

structure VectorType where
  dialect : Dialect
  spelling : String
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

inductive TypeBase where
  | named (name : String)
  | record (kind name : String)
  | vector (type : VectorType)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

structure CType where
  base : TypeBase
  qualifiers : List String := []
  /-- Each element describes qualifiers on one pointer level, inner first. -/
  pointers : List (List String) := []
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

inductive Intrinsic where
  | neon (name : String)
  | rvv (name : String)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

inductive Expr where
  | ident (name : String)
  /-- Literal spelling is retained exactly, including FP hex and integer suffixes. -/
  | literal (text : String)
  | unary (op : String) (arg : Expr)
  | postfix (op : String) (arg : Expr)
  | binary (op : String) (lhs rhs : Expr)
  | conditional (cond yes no : Expr)
  | call (callee : Expr) (args : List Expr)
  | intrinsic (op : Intrinsic) (args : List Expr)
  | index (base idx : Expr)
  | member (base : Expr) (field : String) (arrow : Bool)
  | cast (type : CType) (arg : Expr)
  | sizeofType (type : CType)
  | initList (values : List Expr)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

structure VarDecl where
  type : CType
  name : String
  /-- none is an unsized array dimension. -/
  dimensions : List (Option Expr) := []
  value : Option Expr := none
  alignment : Option Expr := none
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

inductive ForInit where
  | empty
  | expr (value : Expr)
  | decl (vars : List VarDecl)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

inductive Stmt where
  | block (body : List Stmt)
  | decl (vars : List VarDecl)
  | expr (value : Expr)
  | ifThen (cond : Expr) (yes : Stmt) (no : Option Stmt)
  | whileLoop (cond : Expr) (body : Stmt)
  | doWhile (body : Stmt) (cond : Expr)
  | forLoop (init : ForInit) (cond step : Option Expr) (body : Stmt)
  | returnStmt (value : Option Expr)
  | breakStmt | continueStmt | empty
  | directive (text : String)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

structure Function where
  result : CType
  name : String
  params : List VarDecl
  attributes : List String := []
  body : Option Stmt
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

mutual
inductive RecordField where
  | vars (decls : List VarDecl)
  | nested (kind tag : String) (fields : List RecordField) (name : String)
  | directive (text : String)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson
end

inductive TopLevel where
  | function (value : Function)
  | globals (vars : List VarDecl)
  | record (kind tag : String) (fields : List RecordField)
  | directive (text : String)
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

structure Program where
  items : List TopLevel
  deriving Repr, BEq, Inhabited, Lean.ToJson, Lean.FromJson

def isNeonName (s : String) : Bool :=
  s.startsWith "v" && !s.startsWith "__" &&
    ((s.splitOn "_").getLast!).toList.any Char.isDigit

def isVectorType (s : String) : Bool :=
  (s.startsWith "v" && s.endsWith "_t") ||
    ((s.startsWith "int" || s.startsWith "uint" || s.startsWith "float") &&
      s.contains 'x' && s.endsWith "_t")

def namedType (s : String) : TypeBase :=
  if isVectorType s then .vector ⟨if s.startsWith "v" then .rvv else .neon, s⟩
  else .named s

def makeCall (callee : Expr) (args : List Expr) : Expr :=
  match callee with
  | .ident n =>
    if n.startsWith "__riscv_" then .intrinsic (.rvv n) args
    else if isNeonName n then .intrinsic (.neon n) args
    else .call callee args
  | _ => .call callee args

end Transpiler
