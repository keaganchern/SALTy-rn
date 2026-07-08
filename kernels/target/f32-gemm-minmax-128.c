void test_rvv(
    size_t mr,
    size_t nc,
    size_t kc,
    const float* restrict a,
    size_t a_stride,
    const float* restrict w,
    float* restrict c,
    size_t cm_stride,
    size_t cn_stride,
    const struct xnn_f32_minmax_params* restrict params)
{
  assert(mr != 0);
  assert(mr <= 4);
  assert(nc != 0);
  assert(kc != 0);
  assert(kc % sizeof(float) == 0);
  assert(a != NULL);
  assert(w != NULL);
  assert(c != NULL);

  (void) cn_stride;

  const float* a0 = a;
  float* c0 = c;
  const float* a1 = (const float*) ((uintptr_t) a0 + a_stride);
  float* c1 = (float*) ((uintptr_t) c0 + cm_stride);
  if XNN_UNPREDICTABLE(mr < 2) {
    a1 = a0;
    c1 = c0;
  }
  const float* a2 = (const float*) ((uintptr_t) a1 + a_stride);
  float* c2 = (float*) ((uintptr_t) c1 + cm_stride);
  if XNN_UNPREDICTABLE(mr <= 2) {
    a2 = a1;
    c2 = c1;
  }
  const float* a3 = (const float*) ((uintptr_t) a2 + a_stride);
  float* c3 = (float*) ((uintptr_t) c2 + cm_stride);
  if XNN_UNPREDICTABLE(mr != 4) {
    a3 = a2;
    c3 = c2;
  }

  do {
    size_t vl = __riscv_vsetvl_e32m8(nc);

    vfloat32m8_t vacc0 = __riscv_vle32_v_f32m8(w, vl); w += vl;
    vfloat32m8_t vacc1 = vacc0;
    vfloat32m8_t vacc2 = vacc0;
    vfloat32m8_t vacc3 = vacc0;

    size_t k = kc;
    for (; k >= 2 * sizeof(float); k -= 2 * sizeof(float)) {
      float a0c0 = a0[0]; float a0c1 = a0[1]; a0 += 2;
      float a1c0 = a1[0]; float a1c1 = a1[1]; a1 += 2;
      float a2c0 = a2[0]; float a2c1 = a2[1]; a2 += 2;
      float a3c0 = a3[0]; float a3c1 = a3[1]; a3 += 2;

      vfloat32m8_t vb0 = __riscv_vle32_v_f32m8(w, vl); w += vl;
      vfloat32m8_t vb1 = __riscv_vle32_v_f32m8(w, vl); w += vl;

      vacc0 = __riscv_vfmacc_vf_f32m8(vacc0, a0c0, vb0, vl);
      vacc1 = __riscv_vfmacc_vf_f32m8(vacc1, a1c0, vb0, vl);
      vacc2 = __riscv_vfmacc_vf_f32m8(vacc2, a2c0, vb0, vl);
      vacc3 = __riscv_vfmacc_vf_f32m8(vacc3, a3c0, vb0, vl);

      vacc0 = __riscv_vfmacc_vf_f32m8(vacc0, a0c1, vb1, vl);
      vacc1 = __riscv_vfmacc_vf_f32m8(vacc1, a1c1, vb1, vl);
      vacc2 = __riscv_vfmacc_vf_f32m8(vacc2, a2c1, vb1, vl);
      vacc3 = __riscv_vfmacc_vf_f32m8(vacc3, a3c1, vb1, vl);
    }
    if XNN_UNLIKELY(k != 0) {
      float a0c0 = *a0; a0 += 1;
      float a1c0 = *a1; a1 += 1;
      float a2c0 = *a2; a2 += 1;
      float a3c0 = *a3; a3 += 1;

      vfloat32m8_t vb0 = __riscv_vle32_v_f32m8(w, vl); w += vl;

      vacc0 = __riscv_vfmacc_vf_f32m8(vacc0, a0c0, vb0, vl);
      vacc1 = __riscv_vfmacc_vf_f32m8(vacc1, a1c0, vb0, vl);
      vacc2 = __riscv_vfmacc_vf_f32m8(vacc2, a2c0, vb0, vl);
      vacc3 = __riscv_vfmacc_vf_f32m8(vacc3, a3c0, vb0, vl);
    }

    vacc0 = __riscv_vfmin_vf_f32m8(vacc0, params->scalar.max, vl);
    vacc1 = __riscv_vfmin_vf_f32m8(vacc1, params->scalar.max, vl);
    vacc2 = __riscv_vfmin_vf_f32m8(vacc2, params->scalar.max, vl);
    vacc3 = __riscv_vfmin_vf_f32m8(vacc3, params->scalar.max, vl);

    vacc0 = __riscv_vfmax_vf_f32m8(vacc0, params->scalar.min, vl);
    vacc1 = __riscv_vfmax_vf_f32m8(vacc1, params->scalar.min, vl);
    vacc2 = __riscv_vfmax_vf_f32m8(vacc2, params->scalar.min, vl);
    vacc3 = __riscv_vfmax_vf_f32m8(vacc3, params->scalar.min, vl);

    __riscv_vse32_v_f32m8(c0, vacc0, vl); c0 += vl;
    __riscv_vse32_v_f32m8(c1, vacc1, vl); c1 += vl;
    __riscv_vse32_v_f32m8(c2, vacc2, vl); c2 += vl;
    __riscv_vse32_v_f32m8(c3, vacc3, vl); c3 += vl;

    a0 = (const float*) ((uintptr_t) a0 - kc);
    a1 = (const float*) ((uintptr_t) a1 - kc);
    a2 = (const float*) ((uintptr_t) a2 - kc);
    a3 = (const float*) ((uintptr_t) a3 - kc);

    nc -= vl;
  } while (nc != 0);
}