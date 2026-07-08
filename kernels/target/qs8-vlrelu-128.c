void test_rvv(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct xnn_qs8_lrelu_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(int8_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const int16_t input_zero_point = (int16_t) params->scalar.input_zero_point;
  const int16_t positive_multiplier = (int16_t) -params->scalar.positive_multiplier;
  const int16_t negative_multiplier = (int16_t) -params->scalar.negative_multiplier;
  const int16_t output_zero_point = (int16_t) params->scalar.output_zero_point;

  while (batch > 0) {
    size_t vl = __riscv_vsetvl_e8m2(batch);

    vint8m2_t vx = __riscv_vle8_v_i8m2(input, vl);
    
    // vacc = vsubw_s8(vinput_zero_point, vx)
    vint16m4_t vx_wide = __riscv_vsext_vf2_i16m4(vx, vl);
    vint16m4_t vacc = __riscv_vrsub_vx_i16m4(vx_wide, input_zero_point, vl);
    
    // vmask = vcltq_s16(vacc, 0)
    vbool4_t vmask = __riscv_vmslt_vx_i16m4_b4(vacc, 0, vl);
    
    // vacc = vshlq_n_s16(vacc, 7)
    vacc = __riscv_vsll_vx_i16m4(vacc, 7, vl);
    
    // vmultiplier = vbslq_s16(vmask, vpositive_multiplier, vnegative_multiplier)
    vint16m4_t vneg_mult = __riscv_vmv_v_x_i16m4(negative_multiplier, vl);
    vint16m4_t vmultiplier = __riscv_vmerge_vxm_i16m4(vneg_mult, positive_multiplier, vmask, vl);
    
    // vacc = vqrdmulhq_s16(vacc, vmultiplier)
    // Rule 26: vqrdmulh is widening multiply -> double -> vnclip with RNU.
    vint32m8_t vprod = __riscv_vwmul_vv_i32m8(vacc, vmultiplier, vl);
    vprod = __riscv_vsll_vx_i32m8(vprod, 1, vl);
    vacc = __riscv_vnclip_wx_i16m4(vprod, 16, __RISCV_VXRM_RNU, vl);
    
    // vacc = vqaddq_s16(vacc, voutput_zero_point)
    vacc = __riscv_vsadd_vx_i16m4(vacc, output_zero_point, vl);
    
    // vy = vqmovn_s16(vacc)
    vint8m2_t vy = __riscv_vnclip_wx_i8m2(vacc, 0, __RISCV_VXRM_RDN, vl);
    
    __riscv_vse8_v_i8m2(output, vy, vl);
    
    input += vl;
    output += vl;
    batch -= vl;
  }
}