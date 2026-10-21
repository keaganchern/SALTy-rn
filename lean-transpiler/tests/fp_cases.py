"""Synthetic NEON programs and operand grids for FP lowering rules.

The oracle still executes original NEON intrinsics, not a Python FP model.
The two protocol buffers hold a/b at input_a[0:4]/[4:8] and c at input_b[0:4].
"""
from dataclasses import dataclass
import itertools
import random
import struct


@dataclass(frozen=True)
class Operation:
    name: str
    lanes: int
    arity: int
    scalar: bool = False
    lane: int | None = None

    def source(self):
        load = "vld1q_f32" if self.lanes == 4 else "vld1_f32"
        declarations = f"float32x{self.lanes}_t a = {load}(input_a);\n"
        if self.arity >= 2:
            declarations += f"float32x{self.lanes}_t b = {load}(input_a + 4);\n"
        if self.arity == 3:
            c_lanes = 2 if self.name == "vfmaq_lane_f32" else self.lanes
            c_load = "vld1q_f32" if c_lanes == 4 else "vld1_f32"
            declarations += f"float32x{c_lanes}_t c = {c_load}(input_b);\n"
        args = ", ".join(["a", "b", "c"][:self.arity])
        if self.lane is not None:
            args += f", {self.lane}"
        call = f"{self.name}({args})"
        store = f"output[0] = {call};" if self.scalar else f"{'vst1q_f32' if self.lanes == 4 else 'vst1_f32'}(output, {call});"
        return f"""/* struct xnn_f32_default_params {{ char unused; }}; */
void test_neon(size_t batch, const float* input_a, const float* input_b,
               float* output, const struct xnn_f32_default_params* params) {{
  {declarations}
  {store}
}}
"""


OPS = [
    Operation(name, lanes, arity, scalar)
    for name, lanes, arity, scalar in [
        ("vadd_f32", 2, 2, False), ("vaddq_f32", 4, 2, False),
        ("vsubq_f32", 4, 2, False), ("vmulq_f32", 4, 2, False),
        ("vdivq_f32", 4, 2, False), ("vsqrtq_f32", 4, 1, False),
        ("vmin_f32", 2, 2, False), ("vminq_f32", 4, 2, False),
        ("vmax_f32", 2, 2, False), ("vmaxq_f32", 4, 2, False),
        ("vfma_f32", 2, 3, False), ("vfmaq_f32", 4, 3, False),
        ("vmlaq_f32", 4, 3, False), ("vmlsq_f32", 4, 3, False),
        ("vpadd_f32", 2, 2, False), ("vaddv_f32", 2, 1, True),
        ("vaddvq_f32", 4, 1, True),
    ]
] + [Operation(name, 4, 3, lane=lane)
     for name, lanes in [("vfmaq_lane_f32", 2), ("vfmaq_laneq_f32", 4)]
     for lane in range(lanes)]
OPERATIONS = {"intrinsic-" + op.name + (f"-{op.lane}" if op.lane is not None else ""): op for op in OPS}

FINITE = [0, 0x80000000, 0x3F800000, 0xBF800000, 1, 0x7F7FFFFF]
SPECIAL = [0x7F800000, 0xFF800000, 0x7FC12345, 0xFFC23456, 0x7F812345, 0xFF823456]


def make_cases(name, seed, random_cases, domain, pad):
    op = OPERATIONS[name]
    values = FINITE + (SPECIAL if domain == "ieee" else [])
    # Reductions/pairwise operations need mixed lanes to check tree order.
    mixed = op.scalar or op.name == "vpadd_f32"
    count = 3 if mixed else op.arity
    grid = itertools.product(values, repeat=count)
    rows = [(list(row) + [0] * (3 - len(row)), "operand-grid") for row in grid]
    rng = random.Random(f"salty-fp-v1:{name}:{seed}")
    for _ in range(random_cases):
        words = [rng.getrandbits(32) for _ in range(12)]
        if domain == "finite":
            words = [w ^ 0x00800000 if (w & 0x7F800000) == 0x7F800000 else w for w in words]
        rows.append((words, "random-lanes"))
    cases = []
    n = op.lanes
    for index, (words, pattern) in enumerate(rows):
        if pattern == "random-lanes":
            a, b, c = words[:4], words[4:8], words[8:]
        elif mixed:
            x, y, z = words
            a, b, c = [x, y, z, x], [z, x, y, z], [0] * 4
        else:
            a, b, c = ([word] * 4 for word in words)
        input_a, input_b = [0] * (n + pad), [0] * (n + pad)
        input_a[:8], input_b[:4] = a + b, c
        cfg = [0] * 10
        payload = struct.pack("<I10i", n, *cfg)
        payload += struct.pack(f"<{len(input_a)}I", *input_a)
        payload += struct.pack(f"<{len(input_b)}I", *input_b)
        cases.append(dict(kernel=name, seed=seed, index=index, n=n, pattern=pattern,
                          float_domain=domain, parameters=cfg, input_hex=payload.hex(),
                          operands=[[f"{word:08x}" for word in lane] for lane in [a, b, c]]))
    return cases
