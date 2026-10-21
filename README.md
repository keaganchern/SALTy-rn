# SALTy-RN

LLM-powered SIMD kernel translation pipeline (Neon → RVV), with **bounded formal
verification** of every translation.

The pipeline takes an upstream NEON microkernel, translates it to RVV with an LLM,
sanity-checks it on Spike, and then **proves** the RVV output bit-equivalent to the
NEON source with an SMT solver (cvc5). For a guided, end-to-end tour of how all the
pieces fit together — using `qs8-vadd-minmax` as a live example — see
[`PIPELINE_WALKTHROUGH.md`](PIPELINE_WALKTHROUGH.md).

## Coq reduction proofs

[`coq/neon-rvv-reduction`](coq/neon-rvv-reduction/README.md) contains the simplified
NEON byte-sum program's partial-correctness proof and completed RVV instruction
contracts, including byte loads for `vl=0/1`. It includes every program instruction's
generated Coq semantics and original Isla trace, pinned dependencies, build
instructions and recursive proof checks. See its README for the exact coverage
and extraction trust boundary.

## Requirements

- **Python ≥ 3.11**
- **A C++17 compiler + CMake (≥ 3.20)** — for building verification harnesses
- **cvc5 1.3.2** — the verification backend (see *Setup* below; already present in
  this checkout at `third_party/cvc5/install/`)
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

The verification harnesses link **cvc5 1.3.2**, which CMake locates at
`third_party/cvc5/install/` (already built in this checkout). On a fresh machine,
build cvc5 1.3.2 with its CMake install prefix set there, or point CMake at an
existing install:

```bash
# override the default location if your cvc5 lives elsewhere
cmake ... -DCVC5_INSTALL_DIR=/path/to/cvc5/install
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
