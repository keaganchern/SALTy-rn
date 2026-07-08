void test_rvv(
    size_t mr,
    size_t nc,
    size_t kc,
    const int8_t* restrict a,
    size_t a_stride,
    const void* restrict w,
    float* restrict c,
    size_t cm_stride,
    size_t cn_stride,
    const struct xnn_f32_qc4w_minmax_params* restrict params,
    const struct xnn_qd8_quantization_params* restrict quantization_params) XNN_OOB_READS
{
  assert(mr != 0);
  assert(mr <= 1);
  assert(nc != 0);
  assert(kc != 0);
  assert(kc % sizeof(int8_t) == 0);
  assert(a != NULL);
  assert(w != NULL);
  assert(c != NULL);

  float* c0 = c;
  kc = round_up_po2(kc, 2);

  while (nc > 0) {
    // The weights are packed in blocks of 16 columns.
    // We process up to 16 columns per iteration to match the packed layout.
    size_t vl = __riscv_vsetvl_e32m8(nc > 16 ? 16 : nc);

    vint32m8_t vacc = __riscv_vle32_v_i32m8((const int32_t*)w, vl);
    int32_t vzp0 = quantization_params[0].zero_point;
    vacc = __riscv_vmul_vx_i32m8(vacc, vzp0, vl);

    const int8_t* w_weights = (const int8_t*)w + 64;
    const int8_t* a0_ptr = a;
    size_t k = kc;

    while (k >= 8) {
      int16_t a0_val = (int16_t) a0_ptr[0];
      int16_t a1_val = (int16_t) a0_ptr[1];
      int16_t a2_val = (int16_t) a0_ptr[2];
      int16_t a3_val = (int16_t) a0_ptr[3];
      int16_t a4_val = (int16_t) a0_ptr[4];
      int16_t a5_val = (int16_t) a0_ptr[5];
      int16_t a6_val = (int16_t) a0_ptr[6];
      int16_t a7_val = (int16_t) a0_ptr[7];
      a0_ptr += 8;

      vint8m2_t vb_c01 = __riscv_vle8_v_i8m2(w_weights, vl); w_weights += 16;
      vint16m4_t vxb_c0 = __riscv_vsext_vf2_i16m4(__riscv_vsll_vx_i8m2(vb_c01, 4, vl), vl);
      vint16m4_t vxb_c1 = __riscv_vsext_vf2_i16m4(__riscv_vand_vx_i8m2(vb_c01, (int8_t)0xF0, vl), vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a0_val, vxb_c0, vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a1_val, vxb_c1, vl);

      vint8m2_t vb_c23 = __riscv_vle8_v_i8m2(w_weights, vl); w_weights += 16;
      vint16m4_t vxb_c2 = __riscv_vsext_vf2_i16m4(__riscv_vsll_vx_i8m2(vb_c23, 4, vl), vl);
      vint16m4_t vxb_c3 = __riscv_vsext_vf2_i16m4(__riscv_vand_vx_i8m2(vb_c23, (int8_t)0xF0, vl), vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a2_val, vxb_c2, vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a3_val, vxb_c3, vl);

      vint8m2_t vb_c45 = __riscv_vle8_v_i8m2(w_weights, vl); w_weights += 16;
      vint16m4_t vxb_c4 = __riscv_vsext_vf2_i16m4(__riscv_vsll_vx_i8m2(vb_c45, 4, vl), vl);
      vint16m4_t vxb_c5 = __riscv_vsext_vf2_i16m4(__riscv_vand_vx_i8m2(vb_c45, (int8_t)0xF0, vl), vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a4_val, vxb_c4, vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a5_val, vxb_c5, vl);

      vint8m2_t vb_c67 = __riscv_vle8_v_i8m2(w_weights, vl); w_weights += 16;
      vint16m4_t vxb_c6 = __riscv_vsext_vf2_i16m4(__riscv_vsll_vx_i8m2(vb_c67, 4, vl), vl);
      vint16m4_t vxb_c7 = __riscv_vsext_vf2_i16m4(__riscv_vand_vx_i8m2(vb_c67, (int8_t)0xF0, vl), vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a6_val, vxb_c6, vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a7_val, vxb_c7, vl);

      k -= 8;
    }

    while (k > 0) {
      int16_t a0_val = (int16_t) a0_ptr[0];
      int16_t a1_val = (int16_t) a0_ptr[1];
      a0_ptr += 2;

      vint8m2_t vb_c01 = __riscv_vle8_v_i8m2(w_weights, vl); w_weights += 16;
      vint16m4_t vxb_c0 = __riscv_vsext_vf2_i16m4(__riscv_vsll_vx_i8m2(vb_c01, 4, vl), vl);
      vint16m4_t vxb_c1 = __riscv_vsext_vf2_i16m4(__riscv_vand_vx_i8m2(vb_c01, (int8_t)0xF0, vl), vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a0_val, vxb_c0, vl);
      vacc = __riscv_vwmacc_vx_i32m8(vacc, a1_val, vxb_c1, vl);

      k -= 2;
    }

    vacc = __riscv_vsra_vx_i32m8(vacc, 4, vl);
    vfloat32m8_t vout = __riscv_vfcvt_f_x_v_f32m8(vacc, vl);

    float inv_scale = quantization_params[0].inv_scale;
    vout = __riscv_vfmul_vf_f32m8(vout, inv_scale, vl);

    const float* w_scales = (const float*)w_weights;
    vfloat32m8_t vfilter_output_scale = __riscv_vle32_v_f32m8(w_scales, vl);
    
    const float* w_biases = w_scales + 16;
    vfloat32m8_t vbias = __riscv_vle32_v_f32m8(w_biases, vl);

    vout = __riscv_vfmacc_vv_f32m8(vbias, vout, vfilter_output_scale, vl);

    vout = __riscv_vfmax_vf_f32m8(vout, params->scalar.min, vl);
    vout = __riscv_vfmin_vf_f32m8(vout, params->scalar.max, vl);

    __riscv_vse32_v_f32m8(c0, vout, vl);

    c0 = (float*) ((uintptr_t) c0 + cn_stride);
    w = (const void*) (w_biases + 16);
    nc -= vl;
  }
}