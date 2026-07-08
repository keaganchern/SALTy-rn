void test_rvv(
    size_t batch,
    const int8_t* input_a,
    const int8_t* input_b,
    int8_t* output,
    const union xnn_qs8_mul_minmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(int8_t) == 0);
  assert(input_a != NULL);
  assert(input_b != NULL);
  assert(output != NULL);

  const int8_t a_zero_point = params->scalar.a_zero_point;
  const int8_t b_zero_point = params->scalar.b_zero_point;
  const float scale = params->scalar.scale;
  const int16_t output_zero_point = params->scalar.output_zero_point;
  const int8_t output_min = params->scalar.output_min;
  const int8_t output_max = params->scalar.output_max;

  while (batch > 0) {
    size_t vl = __riscv_vsetvl_e8m2(batch);

    vint8m2_t va = __riscv_vle8_v_i8m2(input_a, vl);
    vint8m2_t vb = __riscv_vle8_v_i8m2(input_b, vl);

    vint16m4_t vxa = __riscv_vwsub_vx_i16m4(va, a_zero_point, vl);
    vint16m4_t vxb = __riscv_vwsub_vx_i16m4(vb, b_zero_point, vl);

    vint32m8_t vacc = __riscv_vwmul_vv_i32m8(vxa, vxb, vl);

    vfloat32m8_t vfpacc = __riscv_vfcvt_f_x_v_f32m8(vacc, vl);
    vfpacc = __riscv_vfmul_vf_f32m8(vfpacc, scale, vl);

    vacc = __riscv_vfcvt_x_f_v_i32m8(vfpacc, vl);
    vacc = __riscv_vadd_vx_i32m8(vacc, (int32_t)output_zero_point, vl);

    vint16m4_t vout16 = __riscv_vnclip_wx_i16m4(vacc, 0, __RISCV_VXRM_RDN, vl);
    vint8m2_t vout = __riscv_vnclip_wx_i8m2(vout16, 0, __RISCV_VXRM_RDN, vl);

    vout = __riscv_vmax_vx_i8m2(vout, output_min, vl);
    vout = __riscv_vmin_vx_i8m2(vout, output_max, vl);

    __riscv_vse8_v_i8m2(output, vout, vl);

    input_a += vl;
    input_b += vl;
    output += vl;
    batch -= vl;
  }
}