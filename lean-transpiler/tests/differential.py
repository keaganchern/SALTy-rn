#!/usr/bin/env python3
"""Compare original AArch64 NEON kernels against freshly transpiled RVV kernels.

Requires real cross compilers and QEMU user emulators; no intrinsic substitutes.
Missing tools, compiler errors, crashes, timeouts, and differences are failures.
See tests/differential/README.md for setup, scope, replay, and extension instructions.
"""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import struct
import subprocess
import sys
import time
import fp_cases
import kernel_cases

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / ".lake/build/bin/neon2rvv"
SOURCES = ROOT.parent / "kernels/source"
DRIVER = Path(__file__).with_suffix("") / "driver.c"
PAD = 32
LENGTHS = [1, 2, 3, 4, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65,
           127, 128, 129, 255, 256, 257, 2047, 2048, 2049]


@dataclass(frozen=True)
class Adapter:
    kind: str
    input_type: str
    output_type: str
    params_type: str
    binary: bool = False
    reduction: bool = False

    @property
    def input_size(self):
        return 4 if self.input_type == "float" else 1

    def output_size(self, n):
        return (1 if self.reduction else n) * (1 if self.output_type in ("int8_t", "uint8_t") else 4)

    def header(self):
        init = "(void)(p); (void)(c);"
        if self.kind == "clamp":
            init = "(p).scalar.min = (c)[0]; (p).scalar.max = (c)[1];"
        elif self.kind == "qadd":
            fields = ["a_zero_point", "b_zero_point", "a_multiplier", "b_multiplier",
                      "shift", "output_zero_point", "output_min", "output_max", "bias"]
            init = " ".join(f"(p).scalar.{field} = (c)[{i}];" for i, field in enumerate(fields))
        call = "TEST_ENTRY((n) * sizeof(INPUT_T), (a), "
        call += "(b), " if self.binary else ""
        call += "(out), (p))"
        return f"""#define INPUT_T {self.input_type}
#define OUTPUT_T {self.output_type}
#define PARAMS_T struct {self.params_type}
#define OUTPUT_COUNT(n) {'1' if self.reduction else '(n)'}
#define INIT_PARAMS(p,c) do {{ {init} }} while (0)
#define INVOKE(n,a,b,out,p) {call}
"""


ADAPTERS = {
    **{f"f32-v{op}": Adapter("float", "float", "float", "xnn_f32_default_params", True)
       for op in ["add", "sub", "mul", "div", "min", "max"]},
    **{f"f32-v{op}": Adapter("float", "float", "float", "xnn_f32_default_params")
       for op in ["sqrt", "rndne"]},
    "s8-vclamp": Adapter("clamp", "int8_t", "int8_t", "xnn_s8_minmax_params"),
    "u8-vclamp": Adapter("clamp", "uint8_t", "uint8_t", "xnn_u8_minmax_params"),
    "qs8-vadd-minmax": Adapter("qadd", "int8_t", "int8_t", "xnn_qs8_add_minmax_params", True),
    "qu8-vadd-minmax": Adapter("qadd", "uint8_t", "uint8_t", "xnn_qu8_add_minmax_params", True),
    "qs8-rsum": Adapter("sum", "int8_t", "int32_t", "xnn_qs8_rsum_params", reduction=True),
    "qu8-rsum": Adapter("sum", "uint8_t", "uint32_t", "xnn_qs8_rsum_params", reduction=True),
}
ADAPTERS.update(kernel_cases.ADAPTERS)
KERNEL_NAMES = sorted(ADAPTERS)
ADAPTERS.update({name: Adapter("float", "float", "float", "xnn_f32_default_params", True, op.scalar)
                 for name, op in fp_cases.OPERATIONS.items()})


def parameters(adapter, rng):
    lo, hi = (-128, 127) if adapter.input_type == "int8_t" else (0, 255)
    cfg = [0] * 10
    if adapter.kind == "clamp":
        cfg[:2] = sorted([rng.randint(lo, hi), rng.randint(lo, hi)])
    elif adapter.kind == "qadd":
        az, bz = rng.randint(lo, hi), rng.randint(lo, hi)
        am, bm = rng.randint(1, 4096), rng.randint(1, 4096)
        shift = rng.choice([0, 1, 2, 7, 15, 31])
        out_min, out_max = sorted([rng.randint(lo, hi), rng.randint(lo, hi)])
        cfg[:9] = [az, bz, am, bm, shift, rng.randint(lo, hi), out_min, out_max,
                   (1 << (shift - 1) if shift else 0) - az * am - bz * bm]
    return cfg


def input_array(name, adapter, rng, n, pattern, domain, second):
    count = n + PAD
    if adapter.kind != "float":
        if pattern == "zero": return bytes(count)
        if pattern == "edges":
            edges = [0, 127, 128, 255, 1, 254]
            return bytes(edges[(i + 3 * second) % len(edges)] for i in range(count))
        return bytes(rng.getrandbits(8) for _ in range(count))
    edges = [0, 0x80000000, 1, 0x80000001, 0x007FFFFF, 0x00800000,
             0x3F000000, 0x3F800000, 0xBF800000, 0x7F7FFFFF, 0xFF7FFFFF]
    if domain == "ieee":
        edges += [0x7F800000, 0xFF800000, 0x7FC12345, 0xFFC23456, 0x7F812345]
    words = []
    for i in range(count):
        if pattern == "zero": word = 0x80000000 if i % 2 else 0
        elif pattern == "edges": word = edges[(i + 3 * second) % len(edges)]
        else:
            word = rng.getrandbits(32)
            if domain == "finite" and (word & 0x7F800000) == 0x7F800000:
                word ^= 0x00800000
        if domain == "finite":
            if name == "f32-vdiv" and second and (word & 0x7FFFFFFF) == 0:
                word = 0x3F800000
            if name == "f32-vsqrt" and (word & 0x7FFFFFFF) != 0:
                word &= 0x7FFFFFFF
        words.append(word)
    return struct.pack(f"<{count}I", *words)


def make_cases(name, seed, random_cases, domain):
    if name in fp_cases.OPERATIONS:
        return fp_cases.make_cases(name, seed, random_cases, domain, PAD)
    if name in kernel_cases.ADAPTERS:
        return kernel_cases.make_cases(name, seed, random_cases, domain)
    adapter = ADAPTERS[name]
    # Per-kernel stream remains unchanged when the selected kernel list changes.
    rng = random.Random(f"salty-differential-v1:{name}:{seed}")
    specs = [(n, pattern) for n in LENGTHS for pattern in ["zero", "edges"]]
    specs += [(rng.randint(1, 4096), "random") for _ in range(random_cases)]
    cases = []
    for index, (n, pattern) in enumerate(specs):
        cfg = parameters(adapter, rng)
        payload = struct.pack("<I10i", n, *cfg)
        payload += input_array(name, adapter, rng, n, pattern, domain, False)
        payload += input_array(name, adapter, rng, n, pattern, domain, True)
        cases.append(dict(kernel=name, seed=seed, index=index, n=n, pattern=pattern,
                          float_domain=domain, parameters=cfg, input_hex=payload.hex()))
    return cases


def validate_case(case):
    if case["kernel"] in kernel_cases.ADAPTERS:
        return kernel_cases.validate_case(case)
    adapter = ADAPTERS[case["kernel"]]
    n = case["n"]
    if not isinstance(n, int) or not 1 <= n <= 1048576:
        raise ValueError("invalid replay length")
    payload = bytes.fromhex(case["input_hex"])
    if len(payload) != 44 + 2 * (n + PAD) * adapter.input_size:
        raise ValueError("invalid replay input byte count")
    if struct.unpack_from("<I", payload)[0] != n:
        raise ValueError("replay header disagrees with case length")
    if list(struct.unpack_from("<10i", payload, 4)) != case["parameters"]:
        raise ValueError("replay parameters disagree with input bytes")
    return payload


def case_output_size(case):
    if case["kernel"] in kernel_cases.ADAPTERS:
        return kernel_cases.output_size(case)
    return ADAPTERS[case["kernel"]].output_size(case["n"])


def compare(cases, reference, target):
    """Return (case position, reason) for the first difference, or None."""
    offset = 0
    for i, case in enumerate(cases):
        size = case_output_size(case)
        a, b = reference[offset:offset + size], target[offset:offset + size]
        if len(a) != size or len(b) != size:
            return i, f"truncated output: expected {size} bytes, source={len(a)}, target={len(b)}"
        if a != b:
            j = next(j for j in range(size) if a[j] != b[j])
            return i, f"output byte {j}: source=0x{a[j]:02x}, target=0x{b[j]:02x}"
        offset += size
    if len(reference) != offset or len(target) != offset:
        return len(cases) - 1, f"extra output: expected {offset} bytes, source={len(reference)}, target={len(target)}"
    return None


def incomplete_case(cases, output):
    """The driver flushes after each case, so a crash leaves a completed prefix."""
    offset = 0
    for i, case in enumerate(cases):
        offset += case_output_size(case)
        if len(output) < offset:
            return i
    return len(cases) - 1


def original_source(path, pin_fma=False):
    # Preserve the original kernel body: using the Lean roundtrip for the oracle
    # would allow a shared parser bug to corrupt both sides identically.
    text = path.read_text().lstrip()
    if text.startswith("/*") and "*/" in text:
        params, body = text[2:].split("*/", 1)
        if params.lstrip().startswith(("struct ", "union ")):
            text = params + body
    prelude = '#include "salty_compat.h"\n#include <arm_neon.h>\n'
    if pin_fma:
        prelude += '#include "fp_instruction_reference.h"\n'
    return prelude + text


class Runner:
    def __init__(self, directory, timeout):
        self.directory, self.timeout = directory, timeout
        self.log = directory / "commands.jsonl"

    def run(self, command, data=None):
        command = list(map(str, command))
        entry = dict(argv=command)
        try:
            result = subprocess.run(command, input=data, capture_output=True, timeout=self.timeout)
            entry.update(returncode=result.returncode, stderr=result.stderr.decode(errors="replace"))
        except subprocess.TimeoutExpired as e:
            result = subprocess.CompletedProcess(command, 124, e.stdout or b"",
                (e.stderr or b"") + b"\nrunner/compiler timed out\n")
            entry.update(returncode=124, timeout=True)
        except OSError as e:
            entry.update(error=str(e))
            raise RuntimeError(f"could not run {shlex.join(command)}: {e}") from e
        finally:
            with self.log.open("a") as log:
                log.write(json.dumps(entry) + "\n")
        return result

    def checked(self, command):
        result = self.run(command)
        if result.returncode:
            raise RuntimeError(f"command failed: {shlex.join(list(map(str, command)))}\n"
                               + result.stderr.decode(errors="replace"))
        return result.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="list supported kernel adapters")
    ap.add_argument("--suite", choices=["kernels", "fp"], default="kernels",
                    help="repository kernels or focused floating-point intrinsic operand grids")
    ap.add_argument("--fp-reference", choices=["instruction", "compiler"],
                    help="FP suite only: pin non-lane FMA to ACLE operand order, or use compiler-generated intrinsics")
    ap.add_argument("--kernels", nargs="+", choices=sorted(ADAPTERS))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--random-cases", type=int, default=32, help="in addition to 50 boundary cases per kernel")
    ap.add_argument("--float-domain", choices=["finite", "ieee"], default="finite")
    ap.add_argument("--vlen", type=int, nargs="+", choices=[128, 256, 512], default=[128, 256, 512])
    ap.add_argument("--opt", nargs="+", choices=["0", "1", "2", "3"], default=["0", "2"])
    ap.add_argument("--zig", help="Zig 0.14.1 executable, supplies both cross compilers and musl")
    ap.add_argument("--source-cc", default="aarch64-linux-gnu-gcc", help="shell-split compiler command, never run via shell")
    ap.add_argument("--target-cc", default="clang-19 --target=riscv64-linux-gnu", help="RVV compiler command including sysroot if needed")
    ap.add_argument("--source-runner", default="qemu-aarch64", help="command prefix, or empty for native AArch64")
    ap.add_argument("--target-runner", default="qemu-riscv64 -cpu rv64,v=true,vlen={vlen},elen=64,vext_spec=v1.0",
                    help="command prefix; {vlen} is substituted, empty for native RVV")
    ap.add_argument("--timeout", type=float, default=120, help="seconds per compiler or runner invocation")
    ap.add_argument("--work-dir", type=Path, help="new directory for binaries, inputs, outputs, command log, and report")
    ap.add_argument("--replay", type=Path, help="recompile and rerun the exact saved case.json")
    args = ap.parse_args()
    default_names = KERNEL_NAMES if args.suite == "kernels" else sorted(fp_cases.OPERATIONS)
    if args.list:
        print("\n".join(default_names)); return 0
    if args.random_cases < 0 or args.timeout <= 0:
        ap.error("--random-cases must be nonnegative and --timeout positive")
    if not EXE.is_file():
        ap.error("build the transpiler first: cd lean-transpiler && lake build")
    replay = json.loads(args.replay.read_text()) if args.replay else None
    if replay:
        validate_case(replay)
    args.fp_reference = args.fp_reference or (replay or {}).get("fp_reference", "instruction")
    names = [replay["kernel"]] if replay else list(dict.fromkeys(args.kernels or default_names))
    args.opt = list(dict.fromkeys(args.opt))
    args.vlen = list(dict.fromkeys(args.vlen))
    work = (args.work_dir or ROOT / ".lake/differential" / f"{time.time_ns()}-{os.getpid()}").resolve()
    work.mkdir(parents=True, exist_ok=False)
    driver = work / "driver.c"
    shutil.copyfile(DRIVER, driver)
    buffer_driver = work / "buffer_driver.c"
    shutil.copyfile(DRIVER.parent / "buffer_driver.c", buffer_driver)
    (work / "include").mkdir()
    shutil.copyfile(ROOT / "include/salty_compat.h", work / "include/salty_compat.h")
    shutil.copyfile(DRIVER.parent / "fp_instruction_reference.h", work / "include/fp_instruction_reference.h")
    runner = Runner(work, args.timeout)
    if args.zig:
        source_cc = [args.zig, "cc", "-target", "aarch64-linux-musl"]
        target_cc = [args.zig, "cc", "-target", "riscv64-linux-musl", "-mcpu=generic_rv64+m+a+f+d+c+v"]
        # Keep all compiler cache writes in the selected work directory.
        os.environ.setdefault("ZIG_GLOBAL_CACHE_DIR", str(work / "zig-cache"))
    else:
        source_cc = shlex.split(args.source_cc)
        target_cc = shlex.split(args.target_cc) + ["-march=rv64gcv", "-mabi=lp64d"]
    report = dict(seed=replay["seed"] if replay else args.seed,
                  float_domain=replay["float_domain"] if replay else args.float_domain, kernels=names,
                  fp_reference=args.fp_reference if any(n in fp_cases.OPERATIONS for n in names) else "not used",
                  vlen=args.vlen, optimization=args.opt, comparisons=0, failures=[], status="running")
    (work / "report.json").write_text(json.dumps(report, indent=2))
    print(f"Artifacts: {work}", flush=True)
    try:
        report["source_compiler"] = runner.checked(source_cc + ["--version"]).decode(errors="replace")
        report["target_compiler"] = runner.checked(target_cc + ["--version"]).decode(errors="replace")
        for name in names:
            adapter = ADAPTERS[name]
            selected_driver = buffer_driver if name in kernel_cases.ADAPTERS else driver
            directory = work / name
            directory.mkdir()
            cases = [replay] if replay else make_cases(name, args.seed, args.random_cases, args.float_domain)
            if name in fp_cases.OPERATIONS:
                for case in cases:
                    case["fp_reference"] = args.fp_reference
            data = b"".join(validate_case(c) for c in cases)
            (directory / "input.bin").write_bytes(data)
            (directory / "cases.json").write_text(json.dumps(cases, indent=2))
            (directory / "adapter.h").write_text(adapter.header())
            src, dst = directory / "source", directory / "target"
            src.mkdir(); dst.mkdir()
            source_path = SOURCES / f"{name}.c"
            if name in fp_cases.OPERATIONS:
                source_path = directory / "input.c"
                source_path.write_text(fp_cases.OPERATIONS[name].source())
            pin_fma = args.fp_reference == "instruction" and name in ["intrinsic-vfma_f32", "intrinsic-vfmaq_f32"]
            (src / "kernel.c").write_text(original_source(source_path, pin_fma))
            runner.checked([EXE, "transpile", source_path, "--kernel", "--arch", "arm64",
                            "-o", dst / "kernel.c"])
            for opt in args.opt:
                common = [f"-O{opt}", "-std=c11", "-static", "-ffp-contract=off", "-fno-fast-math",
                          "-DXNN_ARCH_ARM64=1", "-DXNN_ARCH_ARM=0", "-I", work / "include",
                          "-I", directory]
                source_bin, target_bin = src / f"test-O{opt}", dst / f"test-O{opt}"
                runner.checked(source_cc + common + ["-I", src, "-DTEST_ENTRY=test_neon", selected_driver, "-lm", "-o", source_bin])
                runner.checked(target_cc + common + ["-I", dst, "-DTEST_ENTRY=test_rvv", selected_driver, "-lm", "-o", target_bin])
                source_command = shlex.split(args.source_runner) + [str(source_bin)]
                reference = runner.run(source_command, data)
                (src / f"output-O{opt}.bin").write_bytes(reference.stdout)
                for vlen in args.vlen:
                    target_command = shlex.split(args.target_runner.replace("{vlen}", str(vlen))) + [str(target_bin), str(vlen)]
                    target = runner.run(target_command, data)
                    (dst / f"output-O{opt}-vlen{vlen}.bin").write_bytes(target.stdout)
                    if reference.returncode or target.returncode:
                        stderr = (reference.stderr + target.stderr).decode(errors="replace")
                        match = re.search(r"case (\d+):", stderr)
                        failed = reference if reference.returncode else target
                        position = int(match[1]) if match else incomplete_case(cases, failed.stdout)
                        difference = (min(position, len(cases) - 1),
                                      f"execution failed: source={reference.returncode}, target={target.returncode}; {stderr}")
                    else:
                        difference = compare(cases, reference.stdout, target.stdout)
                    # A completed execution prefix is not automatically a
                    # compared/equal prefix when a process exits abnormally.
                    if not reference.returncode and not target.returncode:
                        report["comparisons"] += len(cases) if not difference else difference[0]
                    if difference:
                        position, reason = difference
                        failure = dict(kernel=name, optimization=opt, vlen=vlen, reason=reason,
                                       fp_reference=report["fp_reference"],
                                       case_index=cases[position]["index"], source_command=source_command,
                                       target_command=target_command)
                        faildir = directory / f"failure-O{opt}-vlen{vlen}"
                        faildir.mkdir()
                        (faildir / "case.json").write_text(json.dumps(cases[position], indent=2))
                        (faildir / "input.bin").write_bytes(validate_case(cases[position]))
                        (faildir / "failure.json").write_text(json.dumps(failure, indent=2))
                        report["failures"].append(failure)
                        print(f"FAIL {name} O{opt} VLEN={vlen}: {reason.strip()} (replay {faildir / 'case.json'})", flush=True)
                    else:
                        print(f"PASS {name} O{opt} VLEN={vlen}: {len(cases)} exact output comparisons", flush=True)
        report["status"] = "failed" if report["failures"] else "passed"
    except (RuntimeError, ValueError, OSError) as e:
        report["status"] = "error"
        report["error"] = str(e)
        print(f"ERROR: {e}", file=sys.stderr)
    finally:
        (work / "report.json").write_text(json.dumps(report, indent=2))
    print(f"{report['status'].upper()}: {report['comparisons']} matching case comparisons; report: {work / 'report.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
