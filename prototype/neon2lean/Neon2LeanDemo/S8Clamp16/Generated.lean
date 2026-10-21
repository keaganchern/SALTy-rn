import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.S8Clamp16.Generated

open Neon2LeanDemo.Production

def sourceEnvelope : ArtifactEnvelope :=
  { schemaVersion := 1
    operationRegistryId := "saltyrn.s8-clamp16.integer.v1"
    translationUnit :=
      { role := .translationUnit
        path := "prototype/neon2lean/cases/s8-clamp16/neon.c"
        byteLength := 349
        sha256 := { hex := "5d318164e5aecb0791cecc5ac445e7cecf102606f237d86ca4815ea6b8ba51a2" } }
    preprocessedUnit :=
      { role := .preprocessedUnit
        path := "<generated:s8_clamp16_neon.i>"
        byteLength := 1064
        sha256 := { hex := "df7ca122e8b064b0a97426d288e4925ad993e0eb0aa6604f1476123957a4ba0a" } }
    headers := [{ role := .header, path := "prototype/neon2lean/cases/s8-clamp16/intrinsics_facade.h", byteLength := 848, sha256 := { hex := "e9dbc6937389a9b4401c43faeeecd81e93b3e3094ab51817b4f7f45401330e8b" } }]
    build := { frontendName := "clang", frontendVersion := "Apple clang version 17.0.0 (clang-1700.0.13.3)", targetTriple := "host-parse-facade-only", languageStandard := "c11", abi := "parse-facade-only", endianness := .little, defines := [], includePaths := ["prototype/neon2lean/cases/s8-clamp16"], compilerFlags := ["-Werror", "-fno-color-diagnostics"] }
    extractorName := "prototype/neon2lean/tools/extract_s8_clamp16.py"
    extractorVersion := "28211c292c23504e8e9993ffd23b661b2cbcdf81b428e2a9b21dba379bc52a8d"
    coverage :=
      { translationUnitSha256 := { hex := "5d318164e5aecb0791cecc5ac445e7cecf102606f237d86ca4815ea6b8ba51a2" }
        functionName := "s8_clamp16_neon"
        functionSource := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 129, endOffset := 348 }
        expectedNodeCount := 47
        entries := [
          { astNodeId := 0, kind := "CompoundStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 129, endOffset := 348 }, disposition := .translated [.block 100] },
                    { astNodeId := 1, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 133, endOffset := 172 }, disposition := .translated [.operation 10] },
                    { astNodeId := 2, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 133, endOffset := 171 }, disposition := .translated [.operation 10] },
                    { astNodeId := 3, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 157, endOffset := 171 }, disposition := .translated [.operation 10] },
                    { astNodeId := 4, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 157, endOffset := 167 }, disposition := .translated [.operation 10] },
                    { astNodeId := 5, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 157, endOffset := 167 }, disposition := .translated [.operation 10] },
                    { astNodeId := 6, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 168, endOffset := 170 }, disposition := .translated [.operation 10] },
                    { astNodeId := 7, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 168, endOffset := 170 }, disposition := .translated [.operation 10, .parameter 3] },
                    { astNodeId := 8, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 175, endOffset := 214 }, disposition := .translated [.operation 11] },
                    { astNodeId := 9, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 175, endOffset := 213 }, disposition := .translated [.operation 11] },
                    { astNodeId := 10, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 199, endOffset := 213 }, disposition := .translated [.operation 11] },
                    { astNodeId := 11, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 199, endOffset := 209 }, disposition := .translated [.operation 11] },
                    { astNodeId := 12, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 199, endOffset := 209 }, disposition := .translated [.operation 11] },
                    { astNodeId := 13, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 210, endOffset := 212 }, disposition := .translated [.operation 11] },
                    { astNodeId := 14, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 210, endOffset := 212 }, disposition := .translated [.operation 11, .parameter 4] },
                    { astNodeId := 15, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 217, endOffset := 251 }, disposition := .translated [.operation 12] },
                    { astNodeId := 16, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 217, endOffset := 250 }, disposition := .translated [.operation 12] },
                    { astNodeId := 17, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 235, endOffset := 250 }, disposition := .translated [.operation 12] },
                    { astNodeId := 18, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 235, endOffset := 243 }, disposition := .translated [.operation 12] },
                    { astNodeId := 19, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 235, endOffset := 243 }, disposition := .translated [.operation 12] },
                    { astNodeId := 20, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 244, endOffset := 249 }, disposition := .translated [.operation 12] },
                    { astNodeId := 21, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 244, endOffset := 249 }, disposition := .translated [.operation 12, .parameter 1] },
                    { astNodeId := 22, kind := "BinaryOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 254, endOffset := 284 }, disposition := .translated [.operation 13] },
                    { astNodeId := 23, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 254, endOffset := 259 }, disposition := .translated [.operation 13] },
                    { astNodeId := 24, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 262, endOffset := 284 }, disposition := .translated [.operation 13] },
                    { astNodeId := 25, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 262, endOffset := 270 }, disposition := .translated [.operation 13] },
                    { astNodeId := 26, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 262, endOffset := 270 }, disposition := .translated [.operation 13] },
                    { astNodeId := 27, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 271, endOffset := 276 }, disposition := .translated [.operation 13] },
                    { astNodeId := 28, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 271, endOffset := 276 }, disposition := .translated [.operation 13] },
                    { astNodeId := 29, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 278, endOffset := 283 }, disposition := .translated [.operation 13] },
                    { astNodeId := 30, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 278, endOffset := 283 }, disposition := .translated [.operation 13] },
                    { astNodeId := 31, kind := "BinaryOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 288, endOffset := 318 }, disposition := .translated [.operation 14] },
                    { astNodeId := 32, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 288, endOffset := 293 }, disposition := .translated [.operation 14] },
                    { astNodeId := 33, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 296, endOffset := 318 }, disposition := .translated [.operation 14] },
                    { astNodeId := 34, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 296, endOffset := 304 }, disposition := .translated [.operation 14] },
                    { astNodeId := 35, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 296, endOffset := 304 }, disposition := .translated [.operation 14] },
                    { astNodeId := 36, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 305, endOffset := 310 }, disposition := .translated [.operation 14] },
                    { astNodeId := 37, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 305, endOffset := 310 }, disposition := .translated [.operation 14] },
                    { astNodeId := 38, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 312, endOffset := 317 }, disposition := .translated [.operation 14] },
                    { astNodeId := 39, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 312, endOffset := 317 }, disposition := .translated [.operation 14] },
                    { astNodeId := 40, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 322, endOffset := 345 }, disposition := .translated [.operation 15] },
                    { astNodeId := 41, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 322, endOffset := 330 }, disposition := .translated [.operation 15] },
                    { astNodeId := 42, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 322, endOffset := 330 }, disposition := .translated [.operation 15] },
                    { astNodeId := 43, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 331, endOffset := 337 }, disposition := .translated [.operation 15] },
                    { astNodeId := 44, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 331, endOffset := 337 }, disposition := .translated [.operation 15, .parameter 2] },
                    { astNodeId := 45, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 339, endOffset := 344 }, disposition := .translated [.operation 15] },
                    { astNodeId := 46, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 339, endOffset := 344 }, disposition := .translated [.operation 15] }
        ] } }

def sourceIR : KernelIR :=
  { name := "s8_clamp16_neon"
    translationUnitSha256 := { hex := "5d318164e5aecb0791cecc5ac445e7cecf102606f237d86ca4815ea6b8ba51a2" }
    functionSource := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 129, endOffset := 348 }
    parameters := [
      { nodeId := 1, name := "input", valueType := .pointer, origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 58, endOffset := 77 } },
            { nodeId := 2, name := "output", valueType := .pointer, origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 83, endOffset := 97 } },
            { nodeId := 3, name := "lo", valueType := .scalar (.int 8 .signed), origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 103, endOffset := 112 } },
            { nodeId := 4, name := "hi", valueType := .scalar (.int 8 .signed), origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 118, endOffset := 127 } }
    ]
    entryBlock := 100
    blocks :=
      [{ blockId := 100
         operations := [
           { nodeId := 10, operation := { architecture := .neon, family := .integer, spelling := "vdupq_n_s8" }, operandNodes := [3], operandTypes := [.scalar (.int 8 .signed)], resultType := some (.vector (.fixed 16) (.int 8 .signed)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 157, endOffset := 171 } },
                      { nodeId := 11, operation := { architecture := .neon, family := .integer, spelling := "vdupq_n_s8" }, operandNodes := [4], operandTypes := [.scalar (.int 8 .signed)], resultType := some (.vector (.fixed 16) (.int 8 .signed)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 199, endOffset := 213 } },
                      { nodeId := 12, operation := { architecture := .neon, family := .memory, spelling := "vld1q_s8" }, operandNodes := [1], operandTypes := [.pointer], resultType := some (.vector (.fixed 16) (.int 8 .signed)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 235, endOffset := 250 } },
                      { nodeId := 13, operation := { architecture := .neon, family := .integer, spelling := "vmaxq_s8" }, operandNodes := [12, 10], operandTypes := [.vector (.fixed 16) (.int 8 .signed), .vector (.fixed 16) (.int 8 .signed)], resultType := some (.vector (.fixed 16) (.int 8 .signed)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 262, endOffset := 284 } },
                      { nodeId := 14, operation := { architecture := .neon, family := .integer, spelling := "vminq_s8" }, operandNodes := [13, 11], operandTypes := [.vector (.fixed 16) (.int 8 .signed), .vector (.fixed 16) (.int 8 .signed)], resultType := some (.vector (.fixed 16) (.int 8 .signed)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 296, endOffset := 318 } },
                      { nodeId := 15, operation := { architecture := .neon, family := .memory, spelling := "vst1q_s8" }, operandNodes := [2, 14], operandTypes := [.pointer, .vector (.fixed 16) (.int 8 .signed)], resultType := none, rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 322, endOffset := 345 } }
         ]
         successors := []
         source := { path := "prototype/neon2lean/cases/s8-clamp16/neon.c", beginOffset := 129, endOffset := 348 } }] }

def sourceControl : ControlMode := .fixed 16

def targetEnvelope : ArtifactEnvelope :=
  { schemaVersion := 1
    operationRegistryId := "saltyrn.s8-clamp16.integer.v1"
    translationUnit :=
      { role := .translationUnit
        path := "prototype/neon2lean/cases/s8-clamp16/rvv.c"
        byteLength := 494
        sha256 := { hex := "a928f87b00757a508249de130a1366a2abfd6c0dec5c4840d91d1ac1d88f56b0" } }
    preprocessedUnit :=
      { role := .preprocessedUnit
        path := "<generated:s8_clamp16_rvv.i>"
        byteLength := 1209
        sha256 := { hex := "065831d51ef6c37e11df61129ff4bca37a4744080ca54759f1e70767e998a16e" } }
    headers := [{ role := .header, path := "prototype/neon2lean/cases/s8-clamp16/intrinsics_facade.h", byteLength := 848, sha256 := { hex := "e9dbc6937389a9b4401c43faeeecd81e93b3e3094ab51817b4f7f45401330e8b" } }]
    build := { frontendName := "clang", frontendVersion := "Apple clang version 17.0.0 (clang-1700.0.13.3)", targetTriple := "host-parse-facade-only", languageStandard := "c11", abi := "parse-facade-only", endianness := .little, defines := [], includePaths := ["prototype/neon2lean/cases/s8-clamp16"], compilerFlags := ["-Werror", "-fno-color-diagnostics"] }
    extractorName := "prototype/neon2lean/tools/extract_s8_clamp16.py"
    extractorVersion := "28211c292c23504e8e9993ffd23b661b2cbcdf81b428e2a9b21dba379bc52a8d"
    coverage :=
      { translationUnitSha256 := { hex := "a928f87b00757a508249de130a1366a2abfd6c0dec5c4840d91d1ac1d88f56b0" }
        functionName := "s8_clamp16_rvv"
        functionSource := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 128, endOffset := 493 }
        expectedNodeCount := 71
        entries := [
          { astNodeId := 0, kind := "CompoundStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 128, endOffset := 493 }, disposition := .translated [.block 100] },
                    { astNodeId := 1, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 132, endOffset := 154 }, disposition := .translated [.parameter 5] },
                    { astNodeId := 2, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 132, endOffset := 153 }, disposition := .translated [.parameter 5] },
                    { astNodeId := 3, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 151, endOffset := 153 }, disposition := .translated [.parameter 5] },
                    { astNodeId := 4, kind := "IntegerLiteral", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 151, endOffset := 153 }, disposition := .translated [.parameter 5] },
                    { astNodeId := 5, kind := "WhileStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 157, endOffset := 491 }, disposition := .translated [.block 100] },
                    { astNodeId := 6, kind := "BinaryOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 164, endOffset := 178 }, disposition := .translated [.block 100] },
                    { astNodeId := 7, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 164, endOffset := 173 }, disposition := .translated [.block 100] },
                    { astNodeId := 8, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 164, endOffset := 173 }, disposition := .translated [.block 100, .parameter 5] },
                    { astNodeId := 9, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 177, endOffset := 178 }, disposition := .translated [.block 100] },
                    { astNodeId := 10, kind := "IntegerLiteral", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 177, endOffset := 178 }, disposition := .translated [.block 100] },
                    { astNodeId := 11, kind := "CompoundStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 180, endOffset := 491 }, disposition := .translated [.block 100] },
                    { astNodeId := 12, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 186, endOffset := 235 }, disposition := .translated [.operation 10] },
                    { astNodeId := 13, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 186, endOffset := 234 }, disposition := .translated [.operation 10] },
                    { astNodeId := 14, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 204, endOffset := 234 }, disposition := .translated [.operation 10] },
                    { astNodeId := 15, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 204, endOffset := 223 }, disposition := .translated [.operation 10] },
                    { astNodeId := 16, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 204, endOffset := 223 }, disposition := .translated [.operation 10] },
                    { astNodeId := 17, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 224, endOffset := 233 }, disposition := .translated [.operation 10] },
                    { astNodeId := 18, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 224, endOffset := 233 }, disposition := .translated [.operation 10, .parameter 5] },
                    { astNodeId := 19, kind := "DeclStmt", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 240, endOffset := 289 }, disposition := .translated [.operation 11] },
                    { astNodeId := 20, kind := "VarDecl", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 240, endOffset := 288 }, disposition := .translated [.operation 11] },
                    { astNodeId := 21, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 258, endOffset := 288 }, disposition := .translated [.operation 11] },
                    { astNodeId := 22, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 258, endOffset := 277 }, disposition := .translated [.operation 11] },
                    { astNodeId := 23, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 258, endOffset := 277 }, disposition := .translated [.operation 11] },
                    { astNodeId := 24, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 278, endOffset := 283 }, disposition := .translated [.operation 11] },
                    { astNodeId := 25, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 278, endOffset := 283 }, disposition := .translated [.operation 11, .parameter 1] },
                    { astNodeId := 26, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 285, endOffset := 287 }, disposition := .translated [.operation 11] },
                    { astNodeId := 27, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 285, endOffset := 287 }, disposition := .translated [.operation 11] },
                    { astNodeId := 28, kind := "BinaryOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 294, endOffset := 337 }, disposition := .translated [.operation 12] },
                    { astNodeId := 29, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 294, endOffset := 299 }, disposition := .translated [.operation 12] },
                    { astNodeId := 30, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 302, endOffset := 337 }, disposition := .translated [.operation 12] },
                    { astNodeId := 31, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 302, endOffset := 322 }, disposition := .translated [.operation 12] },
                    { astNodeId := 32, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 302, endOffset := 322 }, disposition := .translated [.operation 12] },
                    { astNodeId := 33, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 323, endOffset := 328 }, disposition := .translated [.operation 12] },
                    { astNodeId := 34, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 323, endOffset := 328 }, disposition := .translated [.operation 12] },
                    { astNodeId := 35, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 330, endOffset := 332 }, disposition := .translated [.operation 12] },
                    { astNodeId := 36, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 330, endOffset := 332 }, disposition := .translated [.operation 12, .parameter 3] },
                    { astNodeId := 37, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 334, endOffset := 336 }, disposition := .translated [.operation 12] },
                    { astNodeId := 38, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 334, endOffset := 336 }, disposition := .translated [.operation 12] },
                    { astNodeId := 39, kind := "BinaryOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 343, endOffset := 386 }, disposition := .translated [.operation 13] },
                    { astNodeId := 40, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 343, endOffset := 348 }, disposition := .translated [.operation 13] },
                    { astNodeId := 41, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 351, endOffset := 386 }, disposition := .translated [.operation 13] },
                    { astNodeId := 42, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 351, endOffset := 371 }, disposition := .translated [.operation 13] },
                    { astNodeId := 43, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 351, endOffset := 371 }, disposition := .translated [.operation 13] },
                    { astNodeId := 44, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 372, endOffset := 377 }, disposition := .translated [.operation 13] },
                    { astNodeId := 45, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 372, endOffset := 377 }, disposition := .translated [.operation 13] },
                    { astNodeId := 46, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 379, endOffset := 381 }, disposition := .translated [.operation 13] },
                    { astNodeId := 47, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 379, endOffset := 381 }, disposition := .translated [.operation 13, .parameter 4] },
                    { astNodeId := 48, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 383, endOffset := 385 }, disposition := .translated [.operation 13] },
                    { astNodeId := 49, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 383, endOffset := 385 }, disposition := .translated [.operation 13] },
                    { astNodeId := 50, kind := "CallExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 392, endOffset := 430 }, disposition := .translated [.operation 14] },
                    { astNodeId := 51, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 392, endOffset := 411 }, disposition := .translated [.operation 14] },
                    { astNodeId := 52, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 392, endOffset := 411 }, disposition := .translated [.operation 14] },
                    { astNodeId := 53, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 412, endOffset := 418 }, disposition := .translated [.operation 14] },
                    { astNodeId := 54, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 412, endOffset := 418 }, disposition := .translated [.operation 14, .parameter 2] },
                    { astNodeId := 55, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 420, endOffset := 425 }, disposition := .translated [.operation 14] },
                    { astNodeId := 56, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 420, endOffset := 425 }, disposition := .translated [.operation 14] },
                    { astNodeId := 57, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 427, endOffset := 429 }, disposition := .translated [.operation 14] },
                    { astNodeId := 58, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 427, endOffset := 429 }, disposition := .translated [.operation 14] },
                    { astNodeId := 59, kind := "CompoundAssignOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 436, endOffset := 447 }, disposition := .translated [.block 100] },
                    { astNodeId := 60, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 436, endOffset := 441 }, disposition := .translated [.block 100, .parameter 1] },
                    { astNodeId := 61, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 445, endOffset := 447 }, disposition := .translated [.block 100] },
                    { astNodeId := 62, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 445, endOffset := 447 }, disposition := .translated [.block 100] },
                    { astNodeId := 63, kind := "CompoundAssignOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 453, endOffset := 465 }, disposition := .translated [.block 100] },
                    { astNodeId := 64, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 453, endOffset := 459 }, disposition := .translated [.block 100, .parameter 2] },
                    { astNodeId := 65, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 463, endOffset := 465 }, disposition := .translated [.block 100] },
                    { astNodeId := 66, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 463, endOffset := 465 }, disposition := .translated [.block 100] },
                    { astNodeId := 67, kind := "CompoundAssignOperator", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 471, endOffset := 486 }, disposition := .translated [.block 100] },
                    { astNodeId := 68, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 471, endOffset := 480 }, disposition := .translated [.block 100, .parameter 5] },
                    { astNodeId := 69, kind := "ImplicitCastExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 484, endOffset := 486 }, disposition := .translated [.block 100] },
                    { astNodeId := 70, kind := "DeclRefExpr", source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 484, endOffset := 486 }, disposition := .translated [.block 100] }
        ] } }

def targetIR : KernelIR :=
  { name := "s8_clamp16_rvv"
    translationUnitSha256 := { hex := "a928f87b00757a508249de130a1366a2abfd6c0dec5c4840d91d1ac1d88f56b0" }
    functionSource := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 128, endOffset := 493 }
    parameters := [
      { nodeId := 1, name := "input", valueType := .pointer, origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 57, endOffset := 76 } },
            { nodeId := 2, name := "output", valueType := .pointer, origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 82, endOffset := 96 } },
            { nodeId := 3, name := "lo", valueType := .scalar (.int 8 .signed), origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 102, endOffset := 111 } },
            { nodeId := 4, name := "hi", valueType := .scalar (.int 8 .signed), origin := .function, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 117, endOffset := 126 } },
            { nodeId := 5, name := "remaining", valueType := .scalar (.int 64 .unsigned), origin := .structuredControlInput, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 132, endOffset := 153 } }
    ]
    entryBlock := 100
    blocks :=
      [{ blockId := 100
         operations := [
           { nodeId := 10, operation := { architecture := .rvv, family := .control, spelling := "__riscv_vsetvl_e8m1" }, operandNodes := [5], operandTypes := [.scalar (.int 64 .unsigned)], resultType := some (.scalar (.int 64 .unsigned)), rvvConfig := none, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 204, endOffset := 234 } },
                      { nodeId := 11, operation := { architecture := .rvv, family := .memory, spelling := "__riscv_vle8_v_i8m1" }, operandNodes := [1, 10], operandTypes := [.pointer, .scalar (.int 64 .unsigned)], resultType := some (.vector (.scalable .m1) (.int 8 .signed)), rvvConfig := some { sew := 8, lmul := .m1, activeVLNode := 10 }, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 258, endOffset := 288 } },
                      { nodeId := 12, operation := { architecture := .rvv, family := .integer, spelling := "__riscv_vmax_vx_i8m1" }, operandNodes := [11, 3, 10], operandTypes := [.vector (.scalable .m1) (.int 8 .signed), .scalar (.int 8 .signed), .scalar (.int 64 .unsigned)], resultType := some (.vector (.scalable .m1) (.int 8 .signed)), rvvConfig := some { sew := 8, lmul := .m1, activeVLNode := 10 }, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 302, endOffset := 337 } },
                      { nodeId := 13, operation := { architecture := .rvv, family := .integer, spelling := "__riscv_vmin_vx_i8m1" }, operandNodes := [12, 4, 10], operandTypes := [.vector (.scalable .m1) (.int 8 .signed), .scalar (.int 8 .signed), .scalar (.int 64 .unsigned)], resultType := some (.vector (.scalable .m1) (.int 8 .signed)), rvvConfig := some { sew := 8, lmul := .m1, activeVLNode := 10 }, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 351, endOffset := 386 } },
                      { nodeId := 14, operation := { architecture := .rvv, family := .memory, spelling := "__riscv_vse8_v_i8m1" }, operandNodes := [2, 13, 10], operandTypes := [.pointer, .vector (.scalable .m1) (.int 8 .signed), .scalar (.int 64 .unsigned)], resultType := none, rvvConfig := some { sew := 8, lmul := .m1, activeVLNode := 10 }, source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 392, endOffset := 430 } }
         ]
         successors := []
         source := { path := "prototype/neon2lean/cases/s8-clamp16/rvv.c", beginOffset := 128, endOffset := 493 } }] }

def targetControl : ControlMode := .positiveStripMine 16

end Neon2LeanDemo.S8Clamp16.Generated
