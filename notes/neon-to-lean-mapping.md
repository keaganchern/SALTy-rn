# NEON C 到 Lean implementation model：第一步设计

> 2026-07-14 状态：主线已收敛为 generated source IR 与 target IR 的直接等价。
> architecture-neutral spec 是可选的独立 refinement witness，不再是必经的、与
> implementation 同源生成的“答案”。第 7--8 节记录当前实现和下一步；前文保留设计依据。

## 1. 目标和正确的 claim

SaltyRN 当前需要的不是“让 LLM 写出一个能通过 Lean 的 theorem”，而是建立一条可审计的链：

```text
NEON C source
  -> faithful typed model
  -> generated Lean IR denotation
  = generated RVV IR denotation
  <- faithful typed model
  <- generated RVV C
```

可另行证明两边都 refine 一个独立审查的 architecture-neutral spec，以降低共同错误风险，
但直接的 source-IR/target-IR equivalence 是固定主命题。

第一步应解决左半边：真实 NEON C 如何映射到 Lean implementation model。只有这层可信，后续
`neonModel = rvvModel` 才能支撑源代码等价的 claim。

第一阶段不应声称：

- 已验证任意 C；
- 已验证完整 Arm/RISC-V ISA；
- 已证明机器码等价；
- 已覆盖全部 SaltyRN kernel。

## 2. 本地仓库给出的约束

- `main` 有 40 个 NEON source kernel，约 191 种 NEON call spelling。
- 当前 Lean 只实现约 13 个 NEON intrinsic，生产 kernel 覆盖集中于 QS8 VAdd/clamp。
- 仓库没有已提交的 C-body -> Lean emitter；`Emit/Parsed/ParsedFully` 是生成实验产物。
- 现有 `CoreOp -> Lane -> Intrinsic -> Kernel.Class` 分层值得保留。
- 当前 intrinsic 使用任意长度 `List`，没有在类型中表达固定 NEON lane 数。
- 当前 `Adequacy.lean` 证明的是手写 intrinsic 与自身 CoreOp 展开定义相等，不是与 Arm 官方语义
  相等。
- `kernels/target/u8-vclamp.c` 当前是空文件，所以现在只能诚实展示真实
  NEON -> Lean -> spec，不能声称真实 u8-vclamp NEON/RVV pair 已验证。

## 3. 候选方案

| 方案 | 落地速度 | source fidelity | 扩展性 | 判断 |
|---|---:|---:|---:|---|
| 直接把 intrinsic call 拼成 Lean shallow definitions | 快 | 低到中 | 中 | 可做临时 golden，不应作为生成架构 |
| Clang AST -> typed SALT IR data -> Lean interpreter | 中 | 高（对受限子集） | 高 | **推荐主线** |
| Clang -> LLVM/MLIR -> LeanMLIR/Alive2 | 中到慢 | 中到高 | 中 | 适合纯 SSA/dataflow；RVV scalable vector、memory/loop 是当前障碍 |
| C++ symbolic shim -> expression trace -> Lean | 快 | 仅有界 | 低到中 | 适合 differential oracle，不能得到任意长度 loop theorem |
| 完整 Arm ASL/Sail 与 RISC-V Sail machine semantics | 很慢 | 最高 | 高 | 作为后续 bridge，不作为第一层日常 proof IR |
| Verus/Dafny/Rocq 直接重写 kernel | 中 | 仍需 C 映射 | 中 | 对 loop invariant 友好，但没有消除 source-model gap |

### 为什么不直接走 LLVM/Alive2

Alive2 是成熟的 LLVM translation validator，但这里同时存在：

- Arm intrinsic 与 RVV intrinsic 的 target-specific lowering；
- fixed-width NEON 与 scalable RVV 的表示差异；
- `vl`、tail/mask policy；
- XNNPACK 特有的部分 load/store 和 OOB-read contract；
- 目标是可组合的 Lean theorem，而不仅是 SMT verdict。

LLVM/MLIR 可作为第二前端或交叉检查器，但不适合作为当前唯一语义层。

### 为什么不直接展开完整 Sail

权威 ISA model 对最终信任很重要，但规模和状态细节会淹没 kernel-level proof。更实际的 precedent 是
先在小语义上证明程序，再用逐 instruction bridge lemma 连接权威模型。

## 4. 推荐架构

### 4.1 外部前端只生成 data

```text
Clang full-body AST
  -> fail-closed extractor
  -> JSON/Lean KernelIR declaration + source hash + source ranges + coverage manifest
```

不要让 emitter 直接生成任意 theorem/tactic。复杂语义和 proof combinator 应留在版本化的 Lean
library 内。

extractor 必须：

1. 使用 Clang 类型和 `ImplicitCastExpr`，不靠 regex 猜类型转换。
2. 把 vector locals 转为 SSA dataflow。
3. 每个 effectful statement 都被消费一次；未知 call、alias 或 control flow 直接拒绝。
4. 保留 source hash、AST range、intrinsic spelling 和原始 C type。
5. 分开输出 dataflow 与 schedule/memory effect。

### 4.2 Lean typed IR

生产版至少需要：

```text
ScalarTy = BV(width, signedness) | FP(format)
VectorTy = Fixed(elem, lanes) | Scalable(elem, SEW, LMUL, activeVL)

Scalar/Vector ops:
  wrap arithmetic, widen/narrow, saturate, shift+rounding,
  signed/unsigned compare/min/max, mask/select, permute

Memory/schedule:
  Load, Store, FixedBlock, PrefixTail, StripMine, Reduction
```

固定 NEON value 建议用 `Fin lanes -> BitVec width`（或等价 dependent vector），不要再用任意长度
`List` 表示寄存器。kernel memory 可以继续用 list/array/function model。

### 4.3 证明分层

```text
intrinsic spelling
  -> typed intrinsic node
  -> lane-level denotation
  -> CoreOp normal form
  -> kernel class normal form (map/zip/reduce/...)
```

RVV 侧不能要求整个物理 vector register 与 NEON 相等。定理应使用 observational equivalence：

- 只比较 `[0, vl)` active lanes；
- 显式记录 SEW/LMUL/VLMAX legality；
- 只比较实际写回的地址和值；
- tail/mask agnostic lanes 不可观察；
- `vstart = 0`、no-trap 和 buffer/alias 前置条件显式出现。

## 5. Intrinsic 语义的 single source of truth

可以借鉴 Jasmin 的 instruction descriptor：每个 intrinsic descriptor 同时包含：

- C spelling 和精确 type signature；
- immediate 范围；
- lane/element shape；
- pure denotation；
- memory footprint；
- lowering 到 CoreOp；
- 对应官方 ISA operation/version。

同一个 descriptor 应生成/驱动 Lean 和 CVC5 adapter，避免当前两套手写语义漂移。LLM 可以提出新
descriptor 草案，但不能自动进入 trusted registry。

## 6. Demo 中发现的真实 obligation

真实 `u8-vclamp.c` 不是所有路径使用同一顺序：

```text
64-byte main loop:  umin (umax x trunc8(min)) trunc8(max)
8-byte/tail:        umax (umin x trunc8(max)) trunc8(min)
```

两者相等需要：

```text
trunc8(min).toNat <= trunc8(max).toNat
```

仅有 raw `uint32 min <= max` 不够，例如 `min=255, max=256` 截断后顺序反转。现有手写 clamp
model 把路径提前归一化，漏掉了这个 proof obligation。这正说明 faithful extraction 应先保留 C
结构，再由 Lean lemma 做合法归一化。

其他必须进入 full-kernel theorem 的条件：

- `XNN_OOB_READS` 尾部可读范围；
- little-endian 4/2/1 lane store；
- input/output alias 与 buffer capacity；
- `batch != 0`；
- arbitrary padding 对实际写回前缀无影响。

## 7. 已实现的垂直切片

位置：`prototype/neon2lean/`

最早的 U8 demo 从真实 `u8-vclamp.c` 的 64-byte 主循环提取：

```text
4 x (load16 -> unsigned max -> unsigned min -> store16)
```

它生成 typed Lean IR，并证明：

- 每个 block 对 16 个 8-bit lane 实现截断参数后的 unsigned clamp；
- 一个 loop body 恰好写 offset `[0, 64)`；
- guard/decrement/input advance/output advance 都是 64；
- 生成 IR 的三个检查不依赖任何公理；路径顺序 lemma 只依赖 Lean 标准的
  `propext`/`Quot.sound`，没有 `sorry` 或自定义公理。

它明确没有覆盖 8-byte loop、4/2/1 tail 或 RVV。

之后的真实 `s8-vclamp` 工作对 Neon/RVV 完整函数体做 fail-closed AST shape audit，
并有任意正分块的 Lean value theorem；但 399/399 与 121/121 节点仍是
`AST_AUDIT_ONLY`，所以这不是 C 到 semantic IR 的完成态。

当前的 synthetic `s8-clamp16` 是第一个完整 generated semantic-IR E2E：前端把两份
C 函数全部 body node 降到 typed IR，Lean 重新检查 provenance/registry/coverage/use
order，并直接解释生成操作，证明输出、最终 memory、frame 与 16-byte write set 相等。
支持子集内的 `vmin -> vmax` mutation 会生成不同 IR，并由 Lean 给出执行反例。

边界仍然明确：这是 restricted synthetic C、parse facade 和 structured single-block loop；
尚未建立 Clang/C adequacy、intrinsic/ISA adequacy 或真实 `vsetvl` trace bridge。

## 8. 建议的执行顺序

1. 用同一 normalized AST/IR frontend 替换真实 `s8-vclamp` 的 answer-shaped audit。
2. 扩展 structured control 到 64-byte、8-byte 和 4/2/1 tail，并建模物理 8-byte tail read。
3. 证明任意 batch 下的 memory safety、精确 partial store、frame 和 paired equivalence。
4. 将真实 `vsetvl(VLEN,VLMAX)` trace bridge 到 positive-progress theorem；不把所有正分块称为 ISA legal。
5. 在 CI 中重算 digest/registry/coverage，执行 mutation regression，并审计 exported theorem axioms。
6. 第一批仍只支持少量 integer intrinsics；FP、table lookup、复杂 reduction/alias fail closed。
7. 为已覆盖 intrinsic 做官方模型/执行 oracle 的 differential audit，再补逐条 adequacy bridge。

## 9. 可借鉴案例

- [Clang AST documentation](https://clang.llvm.org/docs/IntroductionToTheClangAST.html)
- [Arm Neon Intrinsics Reference](https://arm-software.github.io/acle/neon_intrinsics/advsimd.html)
- [RISC-V Vector C Intrinsics Specification](https://docs.riscv.org/reference/vector-c-intrinsics/)
- [Jasmin instruction descriptors](https://jasmin-lang.readthedocs.io/en/stable/compiler/advanced/add_instructions.html)
- [Lean-MLIR](https://github.com/opencompl/lean-mlir)
- [Alive2](https://github.com/AliveToolkit/alive2)
- [RISC-V Sail model](https://github.com/riscv/sail-riscv)
- [Arm Sail model](https://github.com/rems-project/sail-arm)
- [SIMDe Neon-to-RVV case study](https://arxiv.org/abs/2309.16509)
- [EvmAsm small-semantics/Sail bridge precedent](https://reservoir.lean-lang.org/@Verified-zkEVM/EvmAsm)
- [ARM-TV](https://web.ist.utl.pt/nuno.lopes/pubs/armtv-oopsla25.pdf)
