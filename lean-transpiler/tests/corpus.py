#!/usr/bin/env python3
"""Exercise every source kernel through the built Lean executable.

No parsing or lowering is implemented here. Optional C checks use real Clang
RVV builtins. --builtin-header accommodates Lean's stripped Clang distribution:
it declares compiler-provided __rvv_* types and enables its intrinsic pragma;
it does not stub or replace any intrinsic implementation/signature.
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / ".lake/build/bin/neon2rvv"


def run(args):
    result = subprocess.run(list(map(str, args)), text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{result.stderr}{result.stdout}")
    return result.stdout


def builtin_header(directory, generated):
    # Clang validates these builtin types; a misspelling is a compiler error.
    types = sorted(set(re.findall(r"\bv(?:u?int|float|bool)\w+_t\b", generated)))
    lines = ["#include <stddef.h>", "#include <stdint.h>", "#pragma clang riscv intrinsic vector"]
    lines += [f"typedef __rvv_{t[1:]} {t};" for t in types]
    lines += ["enum { __RISCV_VXRM_RNU=0, __RISCV_VXRM_RNE=1, __RISCV_VXRM_RDN=2, __RISCV_VXRM_ROD=3 };",
              "enum { __RISCV_FRM_RNE=0, __RISCV_FRM_RTZ=1, __RISCV_FRM_RDN=2, __RISCV_FRM_RUP=3, __RISCV_FRM_RMM=4 };"]
    (directory / "riscv_vector.h").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", type=Path, default=ROOT.parent / "kernels/source")
    ap.add_argument("--clang", help="Clang 19+ executable for RVV syntax/type checking")
    ap.add_argument("--builtin-header", action="store_true")
    ap.add_argument("--include", action="append", default=[], help="additional compiler include path")
    ap.add_argument("--objects", action="store_true", help="also generate object files; needs RVV backend")
    args = ap.parse_args()
    if args.objects and not args.clang:
        ap.error("--objects requires --clang")
    sources = sorted(args.sources.glob("*.c"))
    if not sources:
        ap.error("no source kernels found")
    with tempfile.TemporaryDirectory(prefix="salty-lean-corpus-") as temp:
        tmp = Path(temp)
        generated = []
        for source in sources:
            run([EXE, "check", source, "--kernel"])
            ast = run([EXE, "ast", source, "--kernel"])
            ast_path = tmp / "ast.json"
            ast_path.write_text(ast)
            # Persisted AST data must emit the same canonical C as direct parsing.
            assert run([EXE, "emit", ast_path]) == run([EXE, "roundtrip", source, "--kernel"])
            for arch in ["arm64", "arm"]:
                target = tmp / f"{source.stem}-{arch}.c"
                run([EXE, "transpile", source, "--kernel", "--arch", arch, "-o", target])
                run([EXE, "check", target])
                target_ast = json.loads(run([EXE, "ast", target]))
                # Inspect structured JSON tags, not just names in emitted text.
                def check_no_neon(value):
                    if isinstance(value, dict):
                        assert "neon" not in value, (source.name, "NEON intrinsic remains")
                        assert value.get("dialect") != "neon", (source.name, "NEON type remains")
                        for child in value.values():
                            check_no_neon(child)
                    elif isinstance(value, list):
                        for child in value:
                            check_no_neon(child)
                check_no_neon(target_ast)
                generated.append(target)
        print(f"PASS: {len(sources)} kernels parsed, C/JSON roundtrips; {len(generated)} RVV outputs parsed with no NEON nodes")
        # The 'lean' command must emit an actual Lean definition, not a debug dump.
        definition = tmp / "Generated.lean"
        run([EXE, "lean", sources[0], "--kernel", "-o", definition])
        run(["lake", "env", "lean", definition])
        print("PASS: generated Lean AST definition elaborates")
        if args.clang:
            if args.builtin_header:
                builtin_header(tmp, "\n".join(p.read_text() for p in generated))
            for vlen in [128, 256, 512]:
                for source in generated:
                    command = [args.clang, "--target=riscv64", f"-march=rv64gcv_zvl{vlen}b",
                               "-ffreestanding", "-ffp-contract=off", "-Werror=implicit-function-declaration",
                               "-I", ROOT / "include"]
                    if args.builtin_header:
                        command += ["-I", tmp]
                    for inc in args.include:
                        command += ["-isystem", inc]
                    if args.objects:
                        command += ["-O2", "-c", source, "-o", tmp / "kernel.o"]
                    else:
                        command += ["-fsyntax-only", source]
                    run(command)
            print(f"PASS: {len(generated) * 3} RVV compiler checks (minimum VLEN 128/256/512)")


if __name__ == "__main__":
    main()
