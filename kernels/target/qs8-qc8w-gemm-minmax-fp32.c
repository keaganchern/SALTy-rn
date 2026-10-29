void test_rvv(
    size_t mr,
    size_t nc,
    size_t kc,
    const int8_t* restrict a,
    size_t a_stride,
    const void* restrict w,
    int8_t* restrict c,
    size_t cm_stride,
    size_t cn_stride,
    const union xnn_qs8_qc8w_conv_minmax_params* restrict params) XNN_OOB_READS
{
  assert(mr != 0);
  assert(mr <= 1);
  assert(nc != 0);
  assert(kc != 0);
  assert(kc % sizeof(int8_t) == 0);
  assert(a != NULL);
  assert(w != NULL);
  assert(c != NULL);

  const int8_t* a0 = a;
  int8_t* c0 = c;

  do {
    // The weights are packed in fixed blocks of NR=8:
    //   [8 x i32 bias][kc x 8 x i8][8 x f32 scale]
    size_t vl = __riscv_vsetvl_e32m2(nc < 8 ? nc : 8);

    vint32m2_t vacc = __riscv_vle32_v_i32m2((const int32_t*) w, vl);
    w = (const int32_t*) w + 8;

    size_t k = kc;
    do {
      const int16_t va0 = (int16_t) *a0++;

      vint8mf2_t vb = __riscv_vle8_v_i8mf2((const int8_t*) w, vl);
      w = (const int8_t*) w + 8;
      vint16m1_t vxb = __riscv_vsext_vf2_i16m1(vb, vl);

      vacc = __riscv_vwmacc_vx_i32m2(vacc, va0, vxb, vl);

      k -= sizeof(int8_t);
    } while (k != 0);

    vfloat32m2_t vfpacc = __riscv_vfcvt_f_x_v_f32m2(vacc, vl);

    vfloat32m2_t vscale = __riscv_vle32_v_f32m2((const float*) w, vl);
    w = (const float*) w + 8;
    vfpacc = __riscv_vfmul_vv_f32m2(vfpacc, vscale, vl);

    // Magic-bias rounding (round-to-nearest-even), then saturating removal of
    // the bias and output zero point.
    vfpacc = __riscv_vfadd_vf_f32m2(vfpacc, params->fp32_neon.magic_bias, vl);
    vacc = __riscv_vreinterpret_v_f32m2_i32m2(vfpacc);
    vacc = __riscv_vssub_vx_i32m2(vacc, params->fp32_neon.magic_bias_less_output_zero_point, vl);

    vint16m1_t vout16 = __riscv_vnclip_wx_i16m1(vacc, 0, __RISCV_VXRM_RDN, vl);
    vint8mf2_t vout = __riscv_vnclip_wx_i8mf2(vout16, 0, __RISCV_VXRM_RDN, vl);

    vout = __riscv_vmax_vx_i8mf2(vout, params->fp32_neon.output_min, vl);
    vout = __riscv_vmin_vx_i8mf2(vout, params->fp32_neon.output_max, vl);

    __riscv_vse8_v_i8mf2(c0, vout, vl);

    c0 = (int8_t*) ((uintptr_t) c0 + cn_stride);
    a0 = (const int8_t*) ((uintptr_t) a0 - kc);
    nc -= vl;
  } while (nc != 0);
}
