void test_rvv(
    size_t mr,
    size_t nc,
    size_t kc,
    size_t ks,
    const int8_t** restrict a,
    const void* restrict w,
    float* restrict c,
    size_t cm_stride,
    size_t cn_stride,
    size_t a_offset,
    const int8_t* zero,
    const int8_t* zero_data,
    const struct xnn_f32_minmax_params* restrict params,
    const struct xnn_qd8_quantization_params* restrict quantization_params) XNN_OOB_READS
{
  assert(mr != 0);
  assert(mr <= 1);
  assert(nc != 0);
  assert(kc != 0);
  assert(ks != 0);
  assert(ks % (1 * sizeof(void*)) == 0);
  assert(a_offset % sizeof(int8_t) == 0);
  assert(a != NULL);
  assert(w != NULL);
  assert(c != NULL);

  float* c0 = c;
  const int bounds_nan = params->scalar.min != params->scalar.min ||
                         params->scalar.max != params->scalar.max;

  do {
    // The weights are packed in fixed blocks of NR=8:
    //   [8 x i32 ksum][ks*kc x 8 x i8][8 x f32 filter scale][8 x f32 bias]
    size_t vl = __riscv_vsetvl_e32m2(nc < 8 ? nc : 8);

    vint32m2_t vksum = __riscv_vle32_v_i32m2((const int32_t*) w, vl);
    w = (const int32_t*) w + 8;
    vint32m2_t vacc = __riscv_vmul_vx_i32m2(vksum, quantization_params->zero_point, vl);

    size_t p = ks;
    do {
      const int8_t* restrict a0 = a[0];
      if (a0 != zero) {
        a0 = (const int8_t*) ((uintptr_t) a0 + a_offset);
      } else {
        a0 = zero_data;
      }
      a += 1;

      size_t k = kc;
      do {
        const int16_t va0 = (int16_t) *a0++;

        vint8mf2_t vb = __riscv_vle8_v_i8mf2((const int8_t*) w, vl);
        w = (const int8_t*) w + 8;
        vint16m1_t vxb = __riscv_vsext_vf2_i16m1(vb, vl);

        vacc = __riscv_vwmacc_vx_i32m2(vacc, va0, vxb, vl);

        k -= sizeof(int8_t);
      } while (k != 0);

      p -= 1 * sizeof(void*);
    } while (p != 0);

    vfloat32m2_t vout = __riscv_vfcvt_f_x_v_f32m2(vacc, vl);
    vout = __riscv_vfmul_vf_f32m2(vout, quantization_params->inv_scale, vl);

    vfloat32m2_t vfilter_output_scale = __riscv_vle32_v_f32m2((const float*) w, vl);
    w = (const float*) w + 8;
    vfloat32m2_t vbias = __riscv_vle32_v_f32m2((const float*) w, vl);
    w = (const float*) w + 8;

    // vout = vbias + vout * vfilter_output_scale (fused, as vfmaq_f32 on ARM64)
    vout = __riscv_vfmacc_vv_f32m2(vbias, vout, vfilter_output_scale, vl);

    // NEON min/max propagates NaNs. Preserve that result under NaN equivalence.
    vfloat32m2_t vunclamped = vout;
    vbool16_t vnan = __riscv_vmfne_vv_f32m2_b16(vout, vout, vl);
    vout = __riscv_vfmax_vf_f32m2(vout, params->scalar.min, vl);
    vout = __riscv_vfmin_vf_f32m2(vout, params->scalar.max, vl);
    vout = __riscv_vmerge_vvm_f32m2(vout, vunclamped, vnan, vl);
    if (bounds_nan) {
      vout = __riscv_vfmv_v_f_f32m2(__builtin_nanf(""), vl);
    }

    __riscv_vse32_v_f32m2(c0, vout, vl);

    a = (const int8_t**restrict) ((uintptr_t) a - ks);
    c0 = (float*) ((uintptr_t) c0 + cn_stride);
    nc -= vl;
  } while (nc != 0);
}
