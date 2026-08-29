# `s8-vmax` 的 element-wise family 原型

这个原型用于检验目标结构，不表示当前 Python backend 已经完成改造。

## 文件所有权

| 文件 | 目标所有者 | 当前原型状态 |
|---|---|---|
| `neon.c` / `rvv.c` | 输入 | 已有示例源码 |
| `S8VMax/Models.lean` | 程序生成器 | 当前 backend 已真实生成局部 block/chunk |
| `S8VMaxV2/Models.lean` | 程序生成器 | 本分支手工搭出的目标输出，尚未接入 Python 生成器 |
| `S8VMaxV2/Spec.lean` | 程序生成器 | 本分支手工搭出的目标输出，只有命题、没有证明 |
| `S8VMaxV2/Proof.lean` | proof agent | 已给出一个可被 Lean 检查的 proof |
| `S8VMaxV2/Audit.lean` | 固定检查器 | 固定最终命题类型并打印依赖的 axioms |

## 证明形状

```text
Neon 16-lane block = map FNeon
        ↓ 通用 fixed-width family theorem
完整 Neon loop = map FNeon

任意 RVV active chunk = map FRvv
        ↓ 通用 positive-partition family theorem
完整 RVV loop = map FRvv

FNeon(x) = FRvv(x)
        ↓
完整 Neon value result = 完整 RVV value result
```

`Spec.lean` 把四个命题定义成 `Prop`，没有使用 `axiom` 或 `sorry`。
proof agent 只能填写 `Proof.lean`，不能修改 `Models.lean` 或 `Spec.lean`。

## `assert` 在这个例子中的位置

Neon 的 `assert(batch % 16 == 0)` 被保留为 `neonSourceAsserts`，并用于证明
没有 tail 的固定宽循环覆盖全部输入。`assert(batch != 0)` 也被保留，不过对纯值
定理并非必要。指针非空在这个 List 值模型中由类型表示吸收；要声称完整 C 函数
等价，还必须另行生成并证明内存范围、可写性、alias/restrict、越界读许可等条件。

## 检查

```sh
cd src/verification_bw/lean
lake build SALT.Example.S8VMaxV2.Audit
```

