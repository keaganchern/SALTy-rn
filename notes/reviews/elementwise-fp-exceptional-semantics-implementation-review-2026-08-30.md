# Elementwise FP Exceptional-Semantics Implementation Review

Date: 2026-08-30 (Asia/Seoul)

Reviewer: `agent:vrndne-plan-reviewer`

The following is the reviewer's final implementation-gate response, preserved
verbatim. It authorizes only a local bootstrap publication. It is deliberately
not the final 180-subject approval.

> 阻塞项（实现候选）：无。
>
> - **Confirmed**：Neon 浮点算术、转换、max/min 和 `vcaltq_f32` 已统一声明全部六类 FP trap-enable 位为 0；RN、FZ、DN、AH 条件按操作需要保留。新增 audit 单测通过。
> - **Confirmed**：AArch64 probe 正确清除了 AH、RMode、FZ、DN、IOE/DZE/OFE/UFE/IXE、IDE，并明确 FPSR 不属于值结果 claim。
> - **Confirmed**：Arm `0*∞`、`0/0`、`sqrt(-1)` 三条 invalid 分支均已有聚焦 Lean 检查。
> - **Confirmed**：audit/plan/checks 可确定性重算，结果为 189 registry variants、180 used variants、12 families、180 passed checks。
> - **Confirmed**：implementation hash 仍精确变化 112 条：53 Neon、59 RVV，且全部为 semantic subjects。
> - **Confirmed**：未发现新的语义错误、wrapper 接错或 theorem weakening。
>
> Implementation gate: GO
>
> 授权使用 `_validate_execution_evidence=False` 向真实 review 目录进行一次**仅限本地、不得提交、不得宣称正式通过**的临时发布，以解除 review→corpus/proof→test 的闭环。之后必须：
>
> 1. 重新生成 corpus、证明和程序审核工件；
> 2. 完成零失败 Python 回归及正式 Lean builds；
> 3. 用新输出覆盖旧 evidence；
> 4. 使用默认的证据校验重新正式发布 180 条 reviews；
> 5. 确认正式 records 绑定当前 audit、checks、implementation 和新执行证据哈希。
>
> 旧的绿色 evidence 仍不能作为本次执行证据，因此最终 180 审批目前尚未满足。
>
> Verdict: NO-GO

## Follow-up: canonical result path

The following follow-up response is also preserved verbatim:

> **Confirmed**：该收紧是语义正确的，没有改变正常或 invalid 的 Arm 结果。
>
> - RISC-V 五个运算现在保证所有 NaN 结果显式 canonical，避免依赖宿主 `Float32` 的 NaN 位模式。
> - Arm 输入 NaN 仍先走 `armNaNResultDN0AH0`，因此 sNaN/qNaN 优先级、quiet、符号和 payload 均不受影响。
> - Arm 无输入 NaN时复用 RISC-V helper 是安全的：
>   - invalid 运算在两种架构下都应返回默认/canonical `0x7FC00000`；
>   - 普通结果保持宿主 binary32/RNE 位结果；
>   - overflow、underflow、除零产生的非 NaN 结果不会被修改。
> - `canonicalizeNaNResult` 只改变 NaN 编码，不影响有限值、零或无穷。
> - 该共享路径还能避免证明时必须从宿主黑盒推出“普通结果不是 NaN”。
>
> Implementation gate: GO
>
> 正式执行证据尚未重新生成，因此最终 evidence gate 仍为：
>
> Verdict: NO-GO

## Follow-up: reducible ordered comparison

The following follow-up response is also preserved verbatim:

> **Confirmed**：位级 `FP32.lt` 对所有非 NaN binary32 编码都正确。
>
> - 任一 NaN 返回 `false`，符合 ordered comparison。
> - `+0/-0` 双向都不小于。
> - 异号且不同时为零时，负数小于正数。
> - 同为非负数时，binary32 无符号位序与数值顺序一致，包括次正规数和 `+∞`。
> - 同为负数时，无符号位序与数值顺序相反，代码正确反向比较，包括负次正规数和 `-∞`。
> - 相同编码不会小于自身；`gt left right := lt right left` 也保持正确。
>
> 新增 theorem 都由现有定义直接证明，只作为化简桥；未发现 axiom、`sorry`、`admit` 或 theorem weakening。该修改消除了 `lt` 的宿主黑盒依赖，也适合支持两个 staging 全输入证明。
>
> Implementation gate: GO
>
> 正式新执行证据尚未完成，因此最终 evidence gate 仍为：
>
> Verdict: NO-GO
