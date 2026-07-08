void test_rvv(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct xnn_qs8_cvt_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(int8_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const int16_t input_zero_point = params->scalar.input_zero_point;
  const int16_t multiplier = (int16_t)(-params->scalar.multiplier);
  const int16_t output_zero_point = params->scalar.output_zero_point;

  size_t vl;
  for (; batch > 0; batch -= vl, input += vl, output += vl) {
    vl = __riscv_vsetvl_e8m2(batch);

    vint8m2_t vx = __riscv_vle8_v_i8m2(input, vl);
    
    vint16m4_t vx_ext = __riscv_vsext_vf2_i16m4(vx, vl);
    vint16m4_t vacc = __riscv_vrsub_vx_i16m4(vx_ext, input_zero_point, vl);
    
    vacc = __riscv_vsll_vx_i16m4(vacc, 7, vl);
    
    vint32m8_t vacc32 = __riscv_vwmul_vx_i32m8(vacc, multiplier, vl);
    vacc32 = __riscv_vsll_vx_i32m8(vacc32, 1, vl);
    vacc = __riscv_vnclip_wx_i16m4(vacc32, 16, __RISCV_VXRM_RNU, vl);
    
    vacc = __riscv_vsadd_vx_i16m4(vacc, output_zero_point, vl);
    
    vint8m2_t vy = __riscv_vnclip_wx_i8m2(vacc, 0, __RISCV_VXRM_RDN, vl);
    
    __riscv_vse8_v_i8m2(output, vy, vl);
  }
}