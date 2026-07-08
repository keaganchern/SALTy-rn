void test_rvv(
    size_t batch,
    const float* input,
    float* output,
    const struct xnn_f32_lrelu_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(float);
  const float slope = params->scalar.slope;

  while (n > 0) {
    size_t vl = __riscv_vsetvl_e32m8(n);
    vfloat32m8_t vx = __riscv_vle32_v_f32m8(input, vl);
    input += vl;

    vfloat32m8_t vacc = __riscv_vfmul_vf_f32m8(vx, slope, vl);
    
    // Reinterpret as i32 and check < 0 to match NEON's vcltq_s32(vreinterpretq_s32_f32(vx), 0).
    // This ensures exact Arm-correct behavior for -0.0f and NaNs with the sign bit set.
    vint32m8_t vx_i32 = __riscv_vreinterpret_v_f32m8_i32m8(vx);
    vbool4_t mask = __riscv_vmslt_vx_i32m8_b4(vx_i32, 0, vl);

    // vmerge_vvm selects op2 (vacc) when mask is 1, and op1 (vx) when mask is 0.
    // This matches NEON's vbslq_f32(mask, vacc, vx).
    vfloat32m8_t vout = __riscv_vmerge_vvm_f32m8(vx, vacc, mask, vl);

    __riscv_vse32_v_f32m8(output, vout, vl);
    output += vl;
    n -= vl;
  }
}