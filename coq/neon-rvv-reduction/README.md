# NEON byte reduction and RVV instruction proofs

A Coq 8.19 project for the simplified unsigned-byte sum kernels in
[`programs/`](programs/). The specification is the initial 32-bit output value
plus the sum of the input bytes, modulo 2³².

## Proof coverage

| Component | Main source | Contract |
| --- | --- | --- |
| NEON program | [`NeonByteSpec.v`](theories/NEON/NeonByteSpec.v) | Entry through return, any list of 16-byte blocks and a tail of 0–15 bytes, under the stated memory and register preconditions |
| NEON vector registers | [`NeonRegisters.v`](theories/NEON/NeonRegisters.v) | Preservation of the other vector registers |
| NEON memory representation | [`KernelMemoryBridge.v`](theories/NEON/KernelMemoryBridge.v) | Word, block, array and byte-memory bridges |
| RVV byte load | [`LoadVL0.v`](theories/RVV/LoadVL0.v), [`LoadVL1.v`](theories/RVV/LoadVL1.v) | `vl = 0` and `vl = 1`, arbitrary input bytes and old destination register |
| RVV vector configuration | [`RvvSimpleVset.v`](theories/RVV/RvvSimpleVset.v), [`RvvPrepare.v`](theories/RVV/RvvPrepare.v) | The selected `vl`, capacity queries and vector initialization |
| RVV widening and addition | [`RvvWidenShared.v`](theories/RVV/RvvWidenShared.v), [`RvvAddShared.v`](theories/RVV/RvvAddShared.v), [`RvvWidenAdd.v`](theories/RVV/RvvWidenAdd.v) | All `0 ≤ vl ≤ 8`, arbitrary operands, under the fixed vector configuration |
| RVV reduction and writeback | [`RvvReduceShared.v`](theories/RVV/RvvReduceShared.v), [`RvvFinishShared.v`](theories/RVV/RvvFinishShared.v) | Eight-lane reduction and the instruction sequence through return |
| RVV entry and loop control | [`RvvInitialize.v`](theories/RVV/RvvInitialize.v), [`RvvControl.v`](theories/RVV/RvvControl.v), [`RvvLoopControl.v`](theories/RVV/RvvLoopControl.v), [`RvvEntry.v`](theories/RVV/RvvEntry.v) | Initialization, pointer/count updates and branches |
| RVV arithmetic specification | [`RvvLaneMath.v`](theories/RVV/RvvLaneMath.v), [`RvvProgress.v`](theories/RVV/RvvProgress.v), [`RvvSharedSpec.v`](theories/RVV/RvvSharedSpec.v) | Lane sums, decreasing remaining count and the shared byte-sum specification |

**Confirmed scope:** these are Islaris instruction/continuation contracts for
the recorded extracted semantics. The NEON entry theorem composes its complete
program contract. RVV byte loads for `vl = 2,…,8` remain unfinished, so this
project does not provide a complete RVV program theorem or a NEON/RVV equivalence
theorem. Historical conditional RVV program proofs stay on the research branch.
No independent program termination theorem is included.

The RVV configuration uses `VLEN = 256` bits. For `SEW = 32`, `LMUL = 1`,
`VLMAX = VLEN × LMUL / SEW = 8` elements. The Sail representation of each vector
register is a `bv 65536`; its storage width differs from the configured VLEN.
The selected `vl` follows the snapshot's `selected_vl8` function, including its
balanced choice when `8 < AVL < 16`.

## Layout

```text
neon-rvv-reduction/
├── _CoqProject
├── Makefile
├── coq-neon-rvv-reduction.opam
├── theories/
│   ├── NEON/                   # Program proof, invariants and bridges
│   ├── RVV/                    # Completed instruction proofs and helpers
│   └── Generated/
│       ├── NEON/               # All 20 program instruction traces in Coq
│       ├── RVV/                # All 19 program instruction traces in Coq
│       └── Bridge/             # Four additional NEON semantic bridges
├── programs/                   # Assembly, disassembly and byte inventories
├── traces/
│   ├── NEON/ RVV/ Bridge/      # Complete original .isla.gz traces
│   ├── configs/ dumps/         # Extraction configuration and constraints
│   └── manifest.json          # Source, trace, model and tool provenance
└── scripts/                    # Dependency setup, build, extraction, checking
```

Modules use the `Reduction.*` namespace. NEON and RVV have separate instruction
tables in their respective `Program.v` files. Generated traces are semantic
definitions; their presence alone does not establish an instruction contract.
All dependencies of the selected proof roots are included, including the Coq
helpers with `Cache` in their names.

Compiled `.vo`, `.vos`, `.vok`, `.glob`, local switches, dependency checkouts and
build outputs are ignored by Git.

## Build and check

**Confirmed, 2026-10-02:** all 131 project sources were compiled afresh in the
recorded existing Coq/Islaris environment. Recursive object checking passed, and
all 35 exported theorem reports were closed under the global context. Both
assemblies reproduced every instruction byte; one trace from each extraction
group reproduced both hashes. See [`verification.json`](verification.json).
Installation of the external dependencies from an empty opam root has not been
tested.

Prerequisites: opam 2, Python 3, GNU make, Git and the system dependencies requested
by opam. Run from this directory:

```sh
python3 scripts/setup.py
opam exec -- make -j2
opam exec -- make check
```

The setup script creates a local OCaml 4.14.2 switch, installs the exact versions
and Git pins in the opam file, and builds the pinned Islaris library and frontend
under `deps/islaris`. Use `python3 scripts/setup.py --existing-switch` to install
into an already selected switch. The project itself uses `coq_makefile` and the
source list in `_CoqProject`.
Use the setup script before building: the opam file declares the package's pinned
dependencies, while `setup.py` also prepares the external Islaris source tree.

The two RVV load proofs are expensive: historical individual compilation times
were about 28 and 37 minutes on the development host. Recursive object checking
can also take substantial time. The launcher sets a 256 MiB process stack where
the host's hard limit permits it.

`make` first checks the recorded source, trace and configuration hashes.
`make check` then runs `coqchk` on every project module with recursive dependency
checking enabled, and explicitly runs `Print Assumptions` for all 35 exported
theorems listed in the manifest. The checker enables Coq's VM conversion with
`-bytecode-compiler yes` to handle the large bitvector expressions; this evaluator
is part of the checking environment. The assumption gate requires every report to be
`Closed under the global context`. Logs and a successful result with object
hashes are written to `_build/check/`; an unsuccessful run leaves no success
report.

To display the NEON result interactively:

```sh
opam exec -- coqtop -q \
  -Q deps/islaris/_build/default/theories isla -Q theories Reduction
```

```coq
Require Import Reduction.NEON.NeonByteSpec.
Print Assumptions Reduction.NEON.NeonByteSpec.neon_program_byte_spec.
```

## Reassemble the programs

Use LLVM 14's `llvm-mc-14`, `ld.lld-14`, `llvm-objdump-14` and xPack's
`riscv-none-elf` toolchain 15.2.0-1. When they are on `PATH`:

```sh
python3 scripts/build.py --isa all
```

`LLVM_MC`, `LLVM_LD`, `LLVM_OBJDUMP` and `RVV_TOOLCHAIN_BIN` can select binaries
outside `PATH`. The script compares every regenerated instruction address and
byte with the recorded inventory, then checks those bytes in executable ELF
load segments. It writes ELF files and disassemblies under `_build/programs/`.

## Inspect or regenerate the instruction traces

The committed traces use lossless gzip compression. For example:

```sh
gzip -dc traces/RVV/a800001ca.isla.gz > /tmp/a800001ca.isla
```

The RVV load trace retains its complete extracted `vl = 0,…,8` behavior;
the load proofs specialize this trace to `vl = 0/1`.

Regeneration additionally requires Rust/Cargo, a C compiler, GMP development
files, Z3 development files and the assembly tools listed above. Select tools
outside `PATH` with the same `LLVM_*` and `RVV_TOOLCHAIN_BIN` variables.
The recorded extractor linked Z3 4.8.12.0.
After `scripts/setup.py`:

```sh
python3 scripts/setup_extraction.py
opam exec -- python3 scripts/extract.py --group NEON --address 0x80001000
opam exec -- python3 scripts/extract.py --group RVV
opam exec -- python3 scripts/extract.py --group Bridge
```

The extraction setup pins Isla and downloads the two Sail IR snapshots with
SHA-256 verification. Extraction uses the exact opcode, configuration,
constraints and model hashes in `traces/manifest.json`, and compares both the
regenerated `.isla` and `.v` hashes. Outputs and comparison reports go to
`_build/extracted/`. Original configurations retain their provenance; runtime
copies replace historical absolute assembler/linker tool paths with the selected
local tools and record those replacements in the comparison reports. Semantic
configuration and SMT constraints are preserved.
`ISLA_FOOTPRINT` and `ISLARIS_FRONTEND` accept full paths to
existing binaries; `SAIL_MODELS` selects a directory containing `aarch64.ir` and
`riscv64.ir` with the recorded hashes.

## Provenance and interpretation

The manifest binds this extraction to research commit `bc8b3b8`, records the
original and migrated source hashes, and pins Islaris, Isla, Sail snapshots and
proof dependencies. Handwritten proofs were migrated by changing module paths;
the mixed instruction table was split into its two ISA tables.

Recursive Coq checking validates proof terms against the loaded Coq definitions.
`Print Assumptions` follows theorem dependencies, including opaque proofs. These
checks do not prove that the external Sail-to-Isla-to-Coq extraction preserves
ISA semantics. This project also provides no C-to-assembly correctness theorem
or independent adequacy theorem connecting the whole ELF to hardware execution.
