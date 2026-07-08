void test_rvv(
    size_t batch,
    const float* input,
    float* output,
    const struct xnn_f32_default_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(float);
  while (n > 0) {
    size_t vl = __riscv_vsetvl_e32m8(n);
    vfloat32m8_t vx = __riscv_vle32_v_f32m8(input, vl);

    vfloat32m8_t vabsx = __riscv_vfabs_v_f32m8(vx, vl);
    
    // vcaltq_f32(vmagic_number, vx) -> 8388608.0f < abs(vx)
    vbool4_t mask = __riscv_vmfgt_vf_f32m8_b4(vabsx, 8388608.0f, vl);

    // vrndabsx = vabsx + magic_number - magic_number
    vfloat32m8_t vrndabsx = __riscv_vfadd_vf_f32m8(vabsx, 8388608.0f, vl);
    vrndabsx = __riscv_vfsub_vf_f32m8(vrndabsx, 8388608.0f, vl);

    // Restore the original sign bit to the rounded absolute value
    vfloat32m8_t vrndx = __riscv_vfsgnj_vv_f32m8(vrndabsx, vx, vl);

    // Select original vx if abs(vx) > magic_number, otherwise use the rounded value
    vfloat32m8_t vy = __riscv_vmerge_vvm_f32m8(vrndx, vx, mask, vl);

    __riscv_vse32_v_f32m8(output, vy, vl);

    input += vl;
    output += vl;
    n -= vl;
  }
}