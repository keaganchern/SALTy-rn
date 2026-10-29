# SALTy-RN

LLM-powered SIMD kernel translation pipeline (Neon → RVV), with **bounded formal
verification** of every translation.

The pipeline takes an upstream NEON microkernel, translates it to RVV with an LLM,
sanity-checks it on Spike, and then **proves** the RVV output bit-equivalent to the
NEON source with an SMT solver (cvc5). For a guided, end-to-end tour of how all the
pieces fit together — using `qs8-vadd-minmax` as a live example — see
[`PIPELINE_WALKTHROUGH.md`](PIPELINE_WALKTHROUGH.md).

## Requirements

- **Python ≥ 3.11**
- **A C++17 compiler + CMake (≥ 3.20)** — for building verification harnesses
- **cvc5 C++ distribution** — the verification backend (Linux setup uses 1.3.2;
  this macOS checkout reuses the downloaded 1.3.1 distribution at
  `third_party/cvc5/install/`)
- **libclang** — installed automatically with the package (verification parses
  kernel signatures via libclang)
- *(optional)* **Chipyard / Spike** — only needed for the Spike differential-test
  gate; verification works without it

## Setup

```bash
# Clone with submodules (autocomp, zephyr, XNNPACK)
git clone --recursive git@github.com:keaganchern/SALTy-rn.git
cd SALTy-rn

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package + Python dependencies (incl. libclang)
pip install -e .
```

### API keys (for the translation step)

Two ways, env vars take precedence over the file:

```bash
# Option A — environment variables
export GOOGLE_API_KEY=...        # default model is Gemini
export ANTHROPIC_API_KEY=...     # or OPENAI_API_KEY / TOGETHER_API_KEY

# Option B — a keys file
cp src/workflow/llm/keys.py.example src/workflow/llm/keys.py
# then edit keys.py
```

Keys are only needed for translation. `--skip-translation` (verify an existing
target kernel) and the standalone verification entry points need no API key.

### cvc5 (verification backend)

The verification harnesses need the cvc5 **C++ headers and libraries**, in addition
to the solver executable. CMake locates them at `third_party/cvc5/install/`.
On this Mac, that directory contains the existing downloaded
`cvc5-macOS-arm64-static.zip` distribution (version 1.3.1). Its exported CMake
target supplies the macOS dependencies; Linux retains the 1.3.2 static-library
link configuration. Extracted solver files are Git-ignored.

On a fresh machine, install a complete cvc5 C++ distribution there, or point
CMake at an existing install:

```bash
# override the default location if your cvc5 lives elsewhere
cmake ... -DCVC5_INSTALL_DIR=/path/to/cvc5/install
```

Automatic solver routing reuses Bitwuzla from
`third_party/bitwuzla/install/bin/bitwuzla`, then searches `PATH` (this Mac uses
`/usr/local/bin/bitwuzla`). `SALT_BITWUZLA=/absolute/path/to/bitwuzla` overrides
that choice. The default `--backend auto` routes integer queries to Bitwuzla
and floating-point queries to cvc5; `--backend cvc5` uses cvc5 alone.

Local verification smoke check (no LLM or Spike needed):

```bash
.venv/bin/python -m src.workflow.verification.orchestrator \
    --neon kernels/source/s8-vclamp.c --rvv kernels/target/s8-vclamp.c \
    --batch 16 --timeout 15
```

### Spike (optional)

```bash
export CHIPYARD_PATH=/path/to/chipyard      # enables the Spike sanity gate
# ZEPHYR_BASE / --zephyr-base override the Zephyr location if needed
```

## Usage

The single entry point is `salty-rn` (installed on your `PATH` inside the venv). It
runs the full flow: **translate → compile → Spike → verify**.

### Translate + verify

```bash
# Translate one kernel and verify it (by name or by file)
salty-rn -k qs8-vadd
salty-rn -f kernels/source/qs8-vadd.c

# Translate everything in kernels/source/
salty-rn -b

# Dry run (no LLM calls)
salty-rn -k qs8-vadd --dry-run

# Translation knobs
salty-rn -k qs8-vadd --model <model> --thinking medium --rules-only --tools
```

### Verify only (skip the LLM)

```bash
# Verify the existing kernels/target/qs8-vadd.c — no translation, 2-minute budget
salty-rn -k qs8-vadd --skip-translation --verification-timeout 120

# Also skip the Spike gate; pin a single batch size; restrict FP inputs
salty-rn -k qs8-vadd --skip-translation --skip-spike
salty-rn -k qs8-vadd --skip-translation --verify-batch 16
salty-rn -k qs8-vadd --skip-translation --input-range=-1,1   # FP-multiply families
```

`--verification-timeout` is the **total** wall-clock budget (seconds) for the batch
sweep; the sweep grows the batch until the budget is spent.

### Standalone verification tools

```bash
# Generate + compile + run + verdict for a NEON/RVV pair directly
python -m src.workflow.verification.orchestrator \
    --neon kernels/source/qs8-vadd.c --rvv kernels/target/qs8-vadd.c \
    --vlen 256 --timeout 60 [--symbolic-params] [--input-range=-1,1]

# Just emit the C++ harness (debugging the engine)
python -m src.workflow.verification.engine.generate \
    --neon kernels/source/qs8-vadd.c --rvv kernels/target/qs8-vadd.c --name qs8-vadd

# Regression / verdict-parity sweep over all supported kernels
python -m src.workflow.verification.engine.parity_sweep
```

### Verify externally generated qc8w kernels

Run from the checkout containing the working `.venv` and cvc5 distribution.
The candidate can remain in another source tree; no translation, API key,
package installation, or Spike run is needed:

```bash
.venv/bin/python -m src.workflow.verification.orchestrator \
    --neon kernels/source/qd8-f32-qc8w-gemm-minmax.c \
    --rvv ../SALTcur/kernels/target/qd8-f32-qc8w-gemm-minmax.c \
    --backend cvc5 --vlen 128 --timeout 600
```

Substitute `qd8-f32-qc8w-igemm-minmax` or `qs8-qc8w-gemm-minmax-fp32`
in both paths to check the other candidates. These fixtures model one-row,
eight-channel packed tiles, with byte-sized weights and full-domain symbolic
integer inputs. Packed scales are finite and nonnegative; qd8 packed biases
are finite. The qd8 reference uses the ARM64 fused multiply-add branch.
Three concrete parameter profiles exercise wide/narrow clamps and zero points.
`--symbolic-params` and `--input-range` are rejected for these fixtures rather
than silently changing or ignoring the requested domain.

The direct GEMM grid uses `nc,kc ∈ {1,2,3,4,5,6,7,8,9,16,17}`.
The igemm grid uses `nc ∈ {1,4,7,8,9,17}`, `kc ∈ {1,7,8,9}`, one or
three input pointers, offsets of zero or three bytes, and ordinary/all-zero/
mixed pointer tables. `ks` is the pointer-table size in bytes. `zero_data` is
symbolic, and the sentinel has a distinct address. Shape log dimensions are
`param_case,mr,nc,kc[,ks_count,a_offset,zero_mode]`.

These are fixed shape grids: `--batch` and `--max-batch` do not select their
dimensions. `ALL_PASSED` means every shape in the grid passed under these
assumptions; `PARTIAL` means the time budget left coverage incomplete.
FP comparison uses the existing NEON/RVV equality policy (signed zeros compare
equal; all NaN payloads compare equal to each other, but never to a number),
and this remains a check under the symbolic intrinsic and memory models.
It is not a proof for every shape, parameter value, VLEN, or memory access.

The cvc5 NEON `vminq_f32`/`vmaxq_f32` model propagates NaNs; the RVV
`vfmin`/`vfmax` model retains its numeric-operand behavior. The qd8 candidates in
`../SALTcur/kernels/target/` preserve NaNs through the clamp, including NaN bounds.
NaN payload bits and floating-point exception flags are outside this contract.
Compile these candidates without fast-math assumptions that exclude NaNs.
The ordinary fixture above still constrains packed FP values to finite values.
Separate NaN regressions remove those constraints for symbolic bias/scale inputs
and exercise mixed lanes, arithmetic-generated NaNs, NaN bounds, and output tails.
They check the actual external candidates at VLEN 128/256/512 and reject the old
clamp. Set `SALT_QC8W_TARGET_DIR` if the candidates are stored elsewhere.

For `u8-vclamp`, concrete mode now sweeps seven valid unsigned clamp profiles,
including identity, constant, and interior ranges, instead of applying signed
default bounds. Use `--max-batch` to finish each profile before moving to the
next. Its symbolic-parameter mode still requires additional intrinsic overloads.

Verifier regressions, including deliberately incorrect controls:

```bash
.venv/bin/python -m pytest tests/test_qc8w_verification.py -q
.venv/bin/python -m pytest tests/test_nan_equivalence.py -q
```

### Growing multidimensional shapes

Run the seven convolution, GEMM, and packing fixtures concurrently, with a separate
ten-minute budget per kernel at VLEN 512:

```bash
.venv/bin/python -m src.workflow.verification.engine.growth_sweep --vlen 512 --seconds 600
```

The runner compiles before starting the timers, expands complete shape frontiers,
and saves exact per-shape results plus `summary.json` under `results/growth_vlen512_<timestamp>/`.
A kernel stops on its first timeout, counterexample, or error; other kernels continue.
`completed_level` counts only frontiers where every shape passed. This opt-in runner
uses corrected DWConv packing/clamp and IGEMM stride fixtures; its manifest records
the full settings and existing proof restrictions. See the
[VLEN 512 experiment results](results/growth_vlen512_10min/SUMMARY.md).

### Compile / Spike only

```bash
salty-compile qs8-vadd                # build + run on Spike
salty-compile qs8-vadd --build-only   # build only
```

## Project structure

```
SALTy-rn/
├── PIPELINE_WALKTHROUGH.md   # end-to-end tour (start here)
├── pyproject.toml            # package + entry points (salty-rn, salty-compile)
├── src/
│   ├── workflow/             # the pipeline (Python)
│   │   ├── pipeline.py       # entry point: translate → compile → Spike → verify
│   │   ├── config.py         # configuration + CLI
│   │   ├── llm/              # multi-provider LLM client (+ keys.py)
│   │   ├── prompts_pkg/      # prompt loading + intrinsics-search tools
│   │   ├── build/            # Zephyr compilation + Spike runner (salty-compile)
│   │   ├── optimize/         # post-verify autocomp optimization (opt-in)
│   │   └── verification/     # the verification driver
│   │       ├── orchestrator.py   # generate → compile → run → verdict
│   │       ├── engine/           # libclang frontend + harness generator (emit.py)
│   │       └── param_configs.py  # param edge-configs + ranges
│   └── verification_cvc5/    # the C++ symbolic shims (the "intrinsics trap")
│       ├── salt.hpp          # umbrella header
│       ├── core/             # symbolic buffers / vectors / comparison + cvc5 context
│       ├── neon/intrinsics.hpp   # NEON intrinsics as Term-builders
│       └── rvv/intrinsics.hpp    # RVV  intrinsics as Term-builders
├── kernels/
│   ├── source/               # input NEON kernels (function: test_neon)
│   ├── target/               # generated RVV kernels (function: test_rvv)
│   ├── harness/              # Spike differential-test drivers
│   └── status.json           # translation/verification progress
├── prompts/Neon/             # translation prompt + rules + background docs
├── op-semantics/             # NEON / RVV intrinsic semantics (LLM-searchable)
├── third_party/              # cvc5, zephyr, autocomp, chipyard, bitwuzla
└── benchmark/XNNPACK/        # upstream kernels (submodule)
```

## How it works

Two stages, each with a repair loop:

1. **Translation (LLM).** A prepped NEON kernel (`test_neon`) plus the translation
   rules, ISA background docs, and intrinsic-semantics search tools go to the model,
   which emits one `vsetvl`-driven RVV kernel (`test_rvv`). A Spike differential test
   against XNNPACK's scalar reference is the fast sanity gate.
2. **Verification (solver).** Both kernels are inlined verbatim into one C++ harness
   where every SIMD intrinsic is redefined to build an SMT formula instead of
   computing numbers. The harness asserts the two outputs *differ* and asks cvc5;
   **UNSAT** means no input can make them differ → proven equivalent (bounded by the
   swept sizes and VLEN).

See [`PIPELINE_WALKTHROUGH.md`](PIPELINE_WALKTHROUGH.md) for the full story,
including the "intrinsics trap" that makes the verifier work.

### Verify after AutoComp (RVV → RVV)

AutoComp's selected candidate is now symbolically compared with a snapshot of
its input RVV baseline **before** publishing to `kernels/target_optimized/`.
The proof uses `--autocomp-vlen` (default 512), and requires `--verify-batch`
with the benchmark workload's **element count** (the verifier converts to bytes
for byte-count kernels). Match the benchmark harness workload explicitly; it is
not inferred from AutoComp's harness. For an end-to-end claim from NEON, the
Phase 1 proof must also cover this workload and VLEN.

```bash
salty-rn -k s8-vclamp --optimize --prob-id 0 \
    --vlen 512 --autocomp-vlen 512 --verify-batch 128

# Check an existing candidate without running the LLM or AutoComp.
# Both files expose test_rvv with matching parameter names and types.
python -m src.workflow.verification.orchestrator \
    --reference-rvv kernels/target/s8-vclamp-512.c \
    --rvv kernels/target_optimized/s8-vclamp-512.c \
    --batch 128 --vlen 512 --timeout 600
```

Only `ALL_PASSED` at the requested batch accepts a candidate. Counterexamples,
unknown/timeouts, compilation failures, and partial proofs preserve the baseline
and any previously accepted optimized file. Each search run retains
`verification_reference.c`, `verification_candidate.c`, and `verification.json`
with the verdict, workload, VLEN, parameter mode, input restrictions, and any
counterexample. Direct verification exits nonzero when the proof does not pass.

RVV/RVV comparisons require identical output bits, including floating-point
bits; the NEON/RVV ULP allowances are not reused. Parameter edge configurations
remain the default; `--symbolic-params` enables the existing symbolic parameter
model. This is bounded output equivalence under the existing intrinsic and
memory models, not a memory-safety proof.

The initial RVV/RVV path supports the engine's single-bound, buffer-output
kernels. Multidimensional workload fixtures and native scalar reduction stores
currently return `UNSUPPORTED` rather than accept an incomplete proof. This
checks AutoComp's selected best candidate; finalist ranking and counterexample-
guided optimization repair are not part of this gate.
