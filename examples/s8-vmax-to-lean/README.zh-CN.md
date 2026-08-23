# 从 Neon/RVV C 到 Lean：一个逐句对应的新例子

本目录提供一个专门为理解翻译流程新写的 `s8-vmax` 例子。它不是 40 个生产
kernel 之一，但它使用当前 backend 的真实 Clang frontend、exact intrinsic registry
和 Lean emitter，而不是人工仿写一份“类似生成结果”的 Lean。

例子的逐元素含义是：

```text
output[i] = signedMax(input[i], threshold)
```

例如 `threshold = 2`，逻辑输入片段为 `[-3, 0, 5, -128, 127]` 时，两侧的
逻辑输出片段都是 `[2, 2, 5, 2, 127]`。实际 block theorem 使用 16 个 lane。

相关文件：

- [`neon.c`](./neon.c)：原始 Neon C。
- [`rvv.c`](./rvv.c)：原始 RVV C。
- [`s8_vmax_example.h`](../../src/workflow/verification/lean_backend/facade/s8_vmax_example.h)：
  只供 Clang 解析的固定声明，不提供 intrinsic 语义。
- [`Models.lean`](../../src/verification_bw/lean/SALT/Example/S8VMax/Models.lean)：
  frontend/emitter 实际生成的两份 implementation model。
- [`Proof.lean`](../../src/verification_bw/lean/SALT/Example/S8VMax/Proof.lean)：
  人工审查的 refinement 和 equivalence proof。

## 1. 原始 Neon 文件

[`neon.c`](./neon.c) 的完整内容是：

```c
/* Parsed together with the pinned s8_vmax_example.h facade. */
void test_neon(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct salt_s8_vmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % 16 == 0);
  assert(input != NULL);
  assert(output != NULL);

  const int8x16_t vthreshold = vdupq_n_s8(params->scalar.threshold);

  for (; batch >= 16; batch -= 16) {
    int8x16_t vx = vld1q_s8(input); input += 16;
    vx = vmaxq_s8(vx, vthreshold);
    vst1q_s8(output, vx); output += 16;
  }
}
```

Neon 每次循环固定处理 16 个 signed byte。`batch % 16 == 0` 排除了这个教学
kernel 没有实现的 tail。

## 2. 原始 RVV 文件

[`rvv.c`](./rvv.c) 的完整内容是：

```c
/* Parsed together with the pinned s8_vmax_example.h facade. */
void test_rvv(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct salt_s8_vmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(input != NULL);
  assert(output != NULL);

  const int8_t threshold = params->scalar.threshold;

  while (batch > 0) {
    const size_t vl = __riscv_vsetvl_e8m8(batch);
    vint8m8_t vx = __riscv_vle8_v_i8m8(input, vl);
    vx = __riscv_vmax_vx_i8m8(vx, threshold, vl);
    __riscv_vse8_v_i8m8(output, vx, vl);
    input += vl;
    output += vl;
    batch -= vl;
  }
}
```

RVV 每次处理由 `vsetvl` 选出的 `vl` 个 active lanes。物理 vector 长度可以不同，
但每个 active lane 仍执行相同的 signed maximum。

## 3. 自动翻译命令

在仓库根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python3 -m workflow.verification.lean_backend.generate_s8_vmax_example \
  --repository-root .
```

实际路径是：

```text
两份 C
  -> Clang JSON AST（固定 target triple 和 parse facade）
  -> typed call/dataflow/control facts
  -> 只接受 9 个精确 spelling 的 registry
  -> fail-closed block emitter
  -> Models.lean
```

未知调用、类型、cast、控制结构、错误的指针步长或错误的 `vl` operand 都会让
生成失败，而不是被忽略。

## 4. 翻译后的 Lean 文件

[`Models.lean`](../../src/verification_bw/lean/SALT/Example/S8VMax/Models.lean)
由上述命令生成。去掉 provenance hash 后，核心语义部分是：

```lean
structure S8VMaxParams where
  threshold : BitVec 8

def neonBlock16FromIntrinsics (p : S8VMaxParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vthreshold_0 := List.replicate 16 ((p.threshold).truncate 8)
  let vx_0 := (input).take 16
  let vx_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vx_0) (vthreshold_0)
  (vx_1)

def rvvChunkFromIntrinsics (p : S8VMaxParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_1 := SALT.Intrinsics.RVV.vmax_vx
    (vx_0) ((p.threshold).truncate 8)
  vx_1
```

生成文件同时记录两份 C、预处理结果、facade 和 registry 的 SHA-256，因此旧
Lean 文件不能在源文件变化后悄悄通过 freshness check。

## 5. 一一对应关系

| 原始 C | 生成 Lean | 含义 |
|---|---|---|
| `int8_t threshold` | `threshold : BitVec 8` | 保存精确的 8 位表示 |
| `int8x16_t` | 长度应为 16 的 `List (BitVec 8)` | 当前 Neon register abstraction |
| `vdupq_n_s8(threshold)` | `List.replicate 16 p.threshold` | 结构性 broadcast |
| `vld1q_s8(input)` | `input.take 16` | 取一次固定宽度 Neon block |
| `vmaxq_s8(vx, vthreshold)` | `Neon.vmaxq_s8 vx vthreshold` | 保留 Neon vector-vector intrinsic 身份 |
| `vst1q_s8(output, vx)` | 返回 `vx` | local-block observation 是写回值 |
| `vsetvl_e8m8(batch)` | 当前 `input.length` | active chunk 的 schedule abstraction |
| RVV `vle8(input, vl)` | `let vx := input` | 输入 list 就是 active load 结果 |
| RVV `vmax_vx(vx, threshold, vl)` | `RVV.vmax_vx vx p.threshold` | 保留 RVV vector-scalar intrinsic 身份 |
| RVV `vse8(output, vx, vl)` | 返回 `vx` | 只观察 active chunk 的写回值 |
| `input/output += ...`、`batch -= ...` | 不进入 block 返回值 | frontend 检查其精确形状，为后续 loop bridge 留证据 |

这里不是把 `vmaxq_s8` 直接改名成 `vmax_vx`。两边分别生成不同的表达式：

```lean
-- Neon intrinsic definition
List.zipWith SALT.bvSignedMax vx vthreshold

-- RVV intrinsic definition
vx.map (fun x => SALT.bvSignedMax x threshold)
```

只有当 Neon 的 broadcast vector 每个 lane 都等于 `threshold` 时，才能证明两者
归一化为同一个 `List.map`。

## 6. Proof 文件证明什么

[`Proof.lean`](../../src/verification_bw/lean/SALT/Example/S8VMax/Proof.lean)
不是 C 的翻译结果。它先定义共同的逐元素 normal form：

```lean
def element (p : S8VMaxParams) (x : BitVec 8) : BitVec 8 :=
  SALT.bvSignedMax x (p.threshold.truncate 8)
```

然后 Lean 检查三层结论：

```text
neonBlock16FromIntrinsics p input = input.map (element p)
rvvChunkFromIntrinsics p input    = input.map (element p)
neonBlock16FromIntrinsics p input = rvvChunkFromIntrinsics p input
```

Neon 定理需要 `input.length = 16`；RVV chunk 定理允许任意 active length。最终
`block_equal` 是 local block/chunk value equivalence。

## 7. Loop 到底处理到了哪里

Frontend 读取并检查了原始 `for`/`while`：

- Neon loop guard 必须是 `batch >= 16`，更新必须是 `batch -= 16`；
- Neon load/store 和 `input/output += 16` 必须吻合；
- RVV 必须先用 `batch` 调用一次 `vsetvl`；
- 每个 RVV vector call 必须使用同一个 `vl`；
- RVV 必须执行 `input/output += vl` 和 `batch -= vl`。

但是 emitter 目前只生成“一次 Neon iteration”和“一次 RVV active chunk”。已有
`SALT.Kernel.Schedule` 定理说明，只要 chunk 完整覆盖输入且每块执行同一个
`element`，任意分块结果都等于 `input.map element`。还没有建立的是：

```text
真实 C loop/pointer/memory execution
        -> FixedChunkTail / PositivePartition
```

所以不能把这个示例称为完整 C 函数等价。仍缺 C loop back-edge、实际内存、alias、
边界、frame property，以及 ISA 合法 `vsetvl` trace 到正分块的 correspondence。

## 8. 当前 TCB

这个例子目前信任：

1. Clang JSON AST 和受限 Python frontend/emitter。
2. 固定 parse facade 中的类型和函数签名。
3. exact registry 到 `Neon.vmaxq_s8`、`RVV.vmax_vx` 的映射。
4. 两个 Lean intrinsic definition 对真实 intrinsic value semantics 的准确性。
5. local load/store observation abstraction。
6. Lean kernel 和基础库。

Lean proof 排除了“已经生成的两份 model 不等价”，但 intrinsic/ISA adequacy 和完整
C correspondence 仍需单独的 bridge。

## 9. 复现检查

```sh
# 生成结果必须与两份 C 保持一致
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python3 -m workflow.verification.lean_backend.generate_s8_vmax_example \
  --repository-root . --check

# frontend/emitter 的示例回归
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python3 -m pytest -q -p no:cacheprovider \
  tests/verification/lean_backend/test_s8_vmax_example.py

# Lean kernel 检查 proof
cd src/verification_bw/lean
lake env lean --trust=0 SALT/Example/S8VMax/Proof.lean
```

将 Neon 的 `vmaxq_s8` 改成 registry 已支持的 `vminq_s8` 会生成不同的 Lean
model；将指针步长 `input += 16` 改成 `input += 8` 则会被 frontend/emitter
直接拒绝。
