import Transpiler.Lexer

namespace Transpiler

private structure ParseState where
  tokens : Array Token
  pos : Nat := 0
  typedefs : List String := []
  deriving Inhabited

private abbrev P := StateT ParseState (Except String)
private def peek : P String := do return (← get).tokens[(← get).pos]!.text
private def look (n : Nat) : P String := do
  return ((← get).tokens[(← get).pos+n]?).map Token.text |>.getD "<eof>"
private def pop : P String := do
  let t ← peek
  modify fun s => { s with pos := s.pos + 1 }
  return t
private def fail {α : Type} (msg : String) : P α := do
  let s ← get
  let t := s.tokens[s.pos]!
  throw s!"{t.line}:{t.column}: {msg} (found '{t.text}')"
private def accept (s : String) : P Bool := do
  if (← peek) == s then let _ ← pop; return true
  return false
private def expect (s : String) : P Unit := do
  unless ← accept s do fail s!"expected '{s}'"
private def identifier : P String := do
  let t ← peek
  unless t.toList.head?.any (fun c => c.isAlpha || c == '_') do fail "expected identifier"
  pop

private def qualifiers := ["const", "volatile", "restrict", "__restrict", "__restrict__",
  "static", "extern", "inline", "typedef", "register", "auto"]
private def scalars := ["void", "char", "short", "int", "long", "signed", "unsigned",
  "float", "double", "_Bool", "bool", "__int128"]
private def typeStart (s : String) : P Bool := do
  return qualifiers.contains s || scalars.contains s || ["struct", "union"].contains s ||
    s.endsWith "_t" || (← get).typedefs.contains s

private def parseType : P CType := do
  let mut qs := []
  while qualifiers.contains (← peek) do qs := qs ++ [← pop]
  let n ← pop
  let base ← if n == "struct" || n == "union" then do
      pure (.record n (← identifier))
    else if scalars.contains n then do
      let mut words := [n]
      while scalars.contains (← peek) do words := words ++ [← pop]
      pure (.named (String.intercalate " " words))
    else if n.endsWith "_t" || (← get).typedefs.contains n then pure (namedType n)
    else fail s!"unsupported type '{n}'"
  while ["const", "volatile"].contains (← peek) do qs := qs ++ [← pop]
  let mut ptrs := []
  while ← accept "*" do
    let mut pq := []
    while qualifiers.contains (← peek) do pq := pq ++ [← pop]
    ptrs := ptrs ++ [pq]
  return ⟨base, qs, ptrs⟩

private def precedence (s : String) : Nat :=
  if s == "," then 1
  else if ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="].contains s then 2
  else if s == "?" then 3
  else if s == "||" then 4 else if s == "&&" then 5
  else if s == "|" then 6 else if s == "^" then 7 else if s == "&" then 8
  else if ["==", "!="].contains s then 9
  else if ["<", ">", "<=", ">="].contains s then 10
  else if ["<<", ">>"].contains s then 11
  else if ["+", "-"].contains s then 12
  else if ["*", "/", "%"].contains s then 13 else 0

mutual
private partial def expression (minPrec : Nat := 1) : P Expr := do
  let mut lhs ← parsePrefix
  let mut go := true
  while go do
    let op ← peek
    let prec := precedence op
    if prec < minPrec || prec == 0 then go := false
    else
      let _ ← pop
      if op == "?" then
        let yes ← expression
        expect ":"
        lhs := .conditional lhs yes (← expression 3)
      else
        let rhs ← expression (if prec == 2 then prec else prec + 1)
        lhs := .binary op lhs rhs
  return lhs

private partial def parsePrefix : P Expr := do
  let t ← peek
  if ["+", "-", "!", "~", "*", "&", "++", "--"].contains t then
    let _ ← pop
    return .unary t (← parsePrefix)
  if t == "sizeof" then
    let _ ← pop
    if (← peek) == "(" && (← typeStart (← look 1)) then
      expect "("
      let ty ← parseType
      expect ")"
      return .sizeofType ty
    return .unary "sizeof" (← parsePrefix)
  if t == "(" && (← typeStart (← look 1)) then
    expect "("
    let ty ← parseType
    expect ")"
    return .cast ty (← parsePrefix)
  let atom ← if ← accept "(" then do
      let e ← expression
      expect ")"
      pure e
    else if ← accept "{" then do
      let mut es := []
      unless ← accept "}" do
        es := [← expression 2]
        while ← accept "," do
          if (← peek) == "}" then break
          es := es ++ [← expression 2]
        expect "}"
      pure (.initList es)
    else if t.toList.head?.any (fun c => c.isDigit || c == '"' || c == '\'' || c == '.') then do
      let _ ← pop
      pure (.literal t)
    else do pure (.ident (← identifier))
  parsePostfix atom

private partial def parsePostfix (base : Expr) : P Expr := do
  if ← accept "(" then
    let mut args := []
    unless ← accept ")" do
      args := [← expression 2]
      while ← accept "," do args := args ++ [← expression 2]
      expect ")"
    parsePostfix (makeCall base args)
  else if ← accept "[" then
    let idx ← expression
    expect "]"
    parsePostfix (.index base idx)
  else if (← peek) == "." || (← peek) == "->" then
    let arrow := (← pop) == "->"
    let field ← identifier
    parsePostfix (.member base field arrow)
  else if (← peek) == "++" || (← peek) == "--" then
    return .postfix (← pop) base
  else pure base
end

private def condition : P Expr := do
  -- Consume the delimiters here so a prefix operator in the following statement
  -- cannot become a postfix/binary operator on the condition.
  let macroName ← if ["XNN_LIKELY", "XNN_UNLIKELY", "XNN_UNPREDICTABLE"].contains (← peek) then
      some <$> pop
    else pure none
  expect "("
  let e ← expression
  expect ")"
  return match macroName with
    | some n => .call (.ident n) [e]
    | none => e

private def declarator (ty : CType) (name : String) : P VarDecl := do
  let mut dims := []
  while ← accept "[" do
    let dim ← if (← peek) == "]" then pure none else some <$> expression 2
    expect "]"
    dims := dims ++ [dim]
  let init ← if ← accept "=" then some <$> expression 2 else pure none
  return ⟨ty, name, dims, init, none⟩

private def declRest (ty : CType) (name : String) : P (List VarDecl) := do
  let mut vars := [← declarator ty name]
  while ← accept "," do
    let mut pointers := []
    while ← accept "*" do
      let mut qs := []
      while qualifiers.contains (← peek) do qs := qs ++ [← pop]
      pointers := pointers ++ [qs]
    vars := vars ++ [← declarator { ty with pointers } (← identifier)]
  expect ";"
  if ty.qualifiers.contains "typedef" then
    modify fun s => { s with typedefs := vars.map (·.name) ++ s.typedefs }
  return vars

mutual
private partial def statement : P Stmt := do
  let t ← peek
  if ← accept "XNN_ALIGN" then
    expect "("
    let alignment ← expression
    expect ")"
    let .decl vars ← statement | fail "XNN_ALIGN must precede a declaration"
    return .decl (vars.map fun v => { v with alignment := some alignment })
  if t.startsWith "#" then return .directive (← pop)
  if ← accept "{" then
    let mut body := []
    while (← peek) != "}" do
      if (← peek) == "<eof>" then fail "unterminated block"
      body := body ++ [← statement]
    expect "}"
    return .block body
  if ← accept ";" then return .empty
  if ← accept "if" then
    let cond ← condition
    let yes ← statement
    let no ← if ← accept "else" then some <$> statement else pure none
    return .ifThen cond yes no
  if ← accept "while" then
    let cond ← condition
    return .whileLoop cond (← statement)
  if ← accept "do" then
    let body ← statement
    expect "while"
    let cond ← condition
    expect ";"
    return .doWhile body cond
  if ← accept "for" then
    expect "("
    let initStmt ← statement
    let init : ForInit ← match initStmt with
      | .empty => pure .empty
      | .expr e => pure (.expr e)
      | .decl vs => pure (.decl vs)
      | _ => fail "for initializer must be an expression or declaration"
    let cond ← if (← peek) == ";" then pure none else some <$> expression
    expect ";"
    let step ← if (← peek) == ")" then pure none else some <$> expression
    expect ")"
    return .forLoop init cond step (← statement)
  if ← accept "return" then
    let value ← if (← peek) == ";" then pure none else some <$> expression
    expect ";"
    return .returnStmt value
  if ← accept "break" then expect ";"; return .breakStmt
  if ← accept "continue" then expect ";"; return .continueStmt
  if ["switch", "case", "default", "goto", "asm", "__asm__"].contains t then
    fail s!"unsupported statement '{t}'"
  if ← typeStart t then
    let ty ← parseType
    return .decl (← declRest ty (← identifier))
  let e ← expression
  expect ";"
  return .expr e
end

private partial def recordFields : P (List RecordField) := do
  expect "{"
  let mut fields := []
  while (← peek) != "}" do
    if (← peek).startsWith "#" then fields := fields ++ [.directive (← pop)]
    else if ["struct", "union"].contains (← peek) && ((← look 1) == "{" || (← look 2) == "{") then
      let kind ← pop
      let tag ← if (← peek) == "{" then pure "" else identifier
      let nested ← recordFields
      let name ← identifier
      expect ";"
      fields := fields ++ [.nested kind tag nested name]
    else
      let ty ← parseType
      fields := fields ++ [.vars (← declRest ty (← identifier))]
  expect "}"
  return fields

private def topLevel : P TopLevel := do
  if (← peek).startsWith "#" then return .directive (← pop)
  if ["struct", "union"].contains (← peek) && (← look 2) == "{" then
    let kind ← pop
    let tag ← identifier
    let fields ← recordFields
    expect ";"
    return .record kind tag fields
  let ty ← parseType
  let name ← identifier
  unless ← accept "(" do return .globals (← declRest ty name)
  let mut params := []
  unless ← accept ")" do
    if (← peek) == "void" && (← look 1) == ")" then let _ ← pop
    else
      let pt ← parseType
      params := [← declarator pt (← identifier)]
      while ← accept "," do
        let pt ← parseType
        params := params ++ [← declarator pt (← identifier)]
    expect ")"
  let mut attrs := []
  while (← peek) == "XNN_OOB_READS" do attrs := attrs ++ [← pop]
  let body ← if ← accept ";" then pure none else some <$> statement
  match body with
  | some (.block _) | none => pure ()
  | _ => fail "function body must be a block"
  return .function ⟨ty, name, params, attrs, body⟩

/-- Parse the documented C subset into data. There are no opaque statement bodies. -/
def parseC (source : String) : Except String Program := do
  let tokens ← lex source
  let parser : P Program := do
    let mut items := []
    while (← peek) != "<eof>" do items := items ++ [← topLevel]
    return ⟨items⟩
  return (← parser.run ⟨tokens, 0, []⟩).1

end Transpiler
