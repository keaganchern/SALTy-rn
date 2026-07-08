void test_rvv(
    size_t channels,
    size_t output_width,
    const float** input,
    const float* weights,
    float* output,
    intptr_t input_stride,
    size_t output_increment,
    size_t input_offset,
    size_t input_pixel_stride,
    const float* zero,
    const struct xnn_f32_minmax_params* restrict params) XNN_OOB_READS
{
  assert(channels != 0);
  assert(output_width != 0);

  do {
    const float* i0 = input[0];
    assert(i0 != NULL);
    if XNN_UNPREDICTABLE(i0 != zero) {
      i0 = (const float*) ((uintptr_t) i0 + input_offset);
    }
    const float* i1 = input[1];
    assert(i1 != NULL);
    if XNN_UNPREDICTABLE(i1 != zero) {
      i1 = (const float*) ((uintptr_t) i1 + input_offset);
    }
    const float* i2 = input[2];
    assert(i2 != NULL);
    if XNN_UNPREDICTABLE(i2 != zero) {
      i2 = (const float*) ((uintptr_t) i2 + input_offset);
    }

    input = (const float**) ((uintptr_t) input + input_stride);

    size_t c = channels;
    const float* w = weights;
    for (; c > 0; ) {
      size_t vl = __riscv_vsetvl_e32m8(c);

      vfloat32m8_t vacc0123p0 = __riscv_vle32_v_f32m8(w, vl); w += vl;

      const vfloat32m8_t vi0x0123 = __riscv_vle32_v_f32m8(i0, vl); i0 += vl;
      const vfloat32m8_t vk0x0123 = __riscv_vle32_v_f32m8(w, vl); w += vl;
      vacc0123p0 = __riscv_vfmacc_vv_f32m8(vacc0123p0, vi0x0123, vk0x0123, vl);

      const vfloat32m8_t vi1x0123 = __riscv_vle32_v_f32m8(i1, vl); i1 += vl;
      const vfloat32m8_t vk1x0123 = __riscv_vle32_v_f32m8(w, vl); w += vl;
      vfloat32m8_t vacc0123p1 = __riscv_vfmul_vv_f32m8(vi1x0123, vk1x0123, vl);

      const vfloat32m8_t vi2x0123 = __riscv_vle32_v_f32m8(i2, vl); i2 += vl;
      const vfloat32m8_t vk2x0123 = __riscv_vle32_v_f32m8(w, vl); w += vl;
      vacc0123p0 = __riscv_vfmacc_vv_f32m8(vacc0123p0, vi2x0123, vk2x0123, vl);

      // Add up all accumulators to vacc0123p0
      vacc0123p0 = __riscv_vfadd_vv_f32m8(vacc0123p0, vacc0123p1, vl);

      vfloat32m8_t vacc0123 = __riscv_vfmax_vf_f32m8(vacc0123p0, params->scalar.min, vl);
      vacc0123 = __riscv_vfmin_vf_f32m8(vacc0123, params->scalar.max, vl);

      __riscv_vse32_v_f32m8(output, vacc0123, vl); output += vl;
      
      c -= vl;
    }

    input_offset += input_pixel_stride;
    output = (float*) ((uintptr_t) output + output_increment);
  } while (--output_width != 0);
}