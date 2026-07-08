void test_rvv(
    size_t batch,
    const int8_t* input,
    float* output,
    const struct xnn_qs8_f32_cvt_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(int8_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const int16_t minus_zero_point = (int16_t)-(uint32_t)params->scalar.zero_point;
  const float scale = params->scalar.scale;

  while (batch > 0) {
    size_t vl = __riscv_vsetvl_e8m2(batch);

    vint8m2_t vx = __riscv_vle8_v_i8m2(input, vl);
    input += vl;

    vint16m4_t vhx = __riscv_vsext_vf2_i16m4(vx, vl);
    vhx = __riscv_vadd_vx_i16m4(vhx, minus_zero_point, vl);

    vint32m8_t vwx = __riscv_vsext_vf2_i32m8(vhx, vl);

    vfloat32m8_t vy = __riscv_vfcvt_f_x_v_f32m8(vwx, vl);
    vy = __riscv_vfmul_vf_f32m8(vy, scale, vl);

    __riscv_vse32_v_f32m8(output, vy, vl);
    output += vl;

    batch -= vl;
  }
}