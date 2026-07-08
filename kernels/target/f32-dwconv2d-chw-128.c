void test_rvv(
    size_t input_height,
    size_t input_width,
    const float* input,
    const float* weights,
    const float* zero,
    float* output,
    uint32_t padding_top,
    const struct xnn_f32_minmax_params* restrict params) XNN_OOB_READS
{
  assert(input_height != 0);
  assert(input_width != 0);
  assert(input_width % sizeof(float) == 0);
  assert(padding_top == 1);

  const float vmin = params->scalar.min;
  const float vmax = params->scalar.max;

  const float w0 = weights[0];
  const float w1 = weights[1];
  const float w2 = weights[2];
  const float w3 = weights[3];
  const float w4 = weights[4];
  const float w5 = weights[5];
  const float w6 = weights[6];
  const float w7 = weights[7];
  const float w8 = weights[8];
  const float w9 = weights[9];

  const float* i0 = zero;
  const float* i1 = input;
  const float* i2 = (const float*) ((uintptr_t) i1 + input_width);
  const float* i3 = (const float*) ((uintptr_t) i2 + input_width);
  const float* i4 = (const float*) ((uintptr_t) i3 + input_width);

  float* o0 = output;
  float* o1 = (float*) ((uintptr_t) o0 + input_width);
  float* o2 = (float*) ((uintptr_t) o1 + input_width);

  size_t output_height = input_height;
  do {
    if XNN_UNPREDICTABLE(output_height < 2) {
      i2 = zero;
      o1 = o0;
    }
    if XNN_UNPREDICTABLE(output_height < 3) {
      i3 = zero;
      o2 = o1;
    }
    if XNN_UNPREDICTABLE(output_height < 4) {
      i4 = zero;
    }

    const float* i0_row = i0;
    const float* i1_row = i1;
    const float* i2_row = i2;
    const float* i3_row = i3;
    const float* i4_row = i4;

    float* o0_row = o0;
    float* o1_row = o1;
    float* o2_row = o2;

    size_t n = input_width / sizeof(float);
    
    float prev_last_0 = 0.0f;
    float prev_last_1 = 0.0f;
    float prev_last_2 = 0.0f;
    float prev_last_3 = 0.0f;
    float prev_last_4 = 0.0f;

    while (n > 0) {
      size_t vl = __riscv_vsetvl_e32m4(n);

      // Load current-row vectors for all 5 input rows
      vfloat32m4_t curr0 = __riscv_vle32_v_f32m4(i0_row, vl);
      vfloat32m4_t curr1 = __riscv_vle32_v_f32m4(i1_row, vl);
      vfloat32m4_t curr2 = __riscv_vle32_v_f32m4(i2_row, vl);
      vfloat32m4_t curr3 = __riscv_vle32_v_f32m4(i3_row, vl);
      vfloat32m4_t curr4 = __riscv_vle32_v_f32m4(i4_row, vl);

      // Left neighbors: shift up, carry last element of the previous chunk (0 at left pad)
      vfloat32m4_t prev0 = __riscv_vfslide1up_vf_f32m4(curr0, prev_last_0, vl);
      vfloat32m4_t prev1 = __riscv_vfslide1up_vf_f32m4(curr1, prev_last_1, vl);
      vfloat32m4_t prev2 = __riscv_vfslide1up_vf_f32m4(curr2, prev_last_2, vl);
      vfloat32m4_t prev3 = __riscv_vfslide1up_vf_f32m4(curr3, prev_last_3, vl);
      vfloat32m4_t prev4 = __riscv_vfslide1up_vf_f32m4(curr4, prev_last_4, vl);
      prev_last_0 = __riscv_vfmv_f_s_f32m4_f32(__riscv_vslidedown_vx_f32m4(curr0, vl - 1, vl));
      prev_last_1 = __riscv_vfmv_f_s_f32m4_f32(__riscv_vslidedown_vx_f32m4(curr1, vl - 1, vl));
      prev_last_2 = __riscv_vfmv_f_s_f32m4_f32(__riscv_vslidedown_vx_f32m4(curr2, vl - 1, vl));
      prev_last_3 = __riscv_vfmv_f_s_f32m4_f32(__riscv_vslidedown_vx_f32m4(curr3, vl - 1, vl));
      prev_last_4 = __riscv_vfmv_f_s_f32m4_f32(__riscv_vslidedown_vx_f32m4(curr4, vl - 1, vl));

      // Right neighbors: shift down, insert first element of the next chunk (0 at right edge)
      float next_first_0 = (n > vl) ? i0_row[vl] : 0.0f;
      float next_first_1 = (n > vl) ? i1_row[vl] : 0.0f;
      float next_first_2 = (n > vl) ? i2_row[vl] : 0.0f;
      float next_first_3 = (n > vl) ? i3_row[vl] : 0.0f;
      float next_first_4 = (n > vl) ? i4_row[vl] : 0.0f;
      vfloat32m4_t next0 = __riscv_vfslide1down_vf_f32m4(curr0, next_first_0, vl);
      vfloat32m4_t next1 = __riscv_vfslide1down_vf_f32m4(curr1, next_first_1, vl);
      vfloat32m4_t next2 = __riscv_vfslide1down_vf_f32m4(curr2, next_first_2, vl);
      vfloat32m4_t next3 = __riscv_vfslide1down_vf_f32m4(curr3, next_first_3, vl);
      vfloat32m4_t next4 = __riscv_vfslide1down_vf_f32m4(curr4, next_first_4, vl);

      // Accumulate in NEON's tap-grouped order (curr row-triplet, then prev, then next)
      // so the FP summation order — hence rounding — is bit-identical to the gold.
      vfloat32m4_t vo0 = __riscv_vfmv_v_f_f32m4(w0, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w2, curr0, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w5, curr1, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w8, curr2, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w1, prev0, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w4, prev1, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w7, prev2, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w3, next0, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w6, next1, vl);
      vo0 = __riscv_vfmacc_vf_f32m4(vo0, w9, next2, vl);

      vfloat32m4_t vo1 = __riscv_vfmv_v_f_f32m4(w0, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w2, curr1, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w5, curr2, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w8, curr3, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w1, prev1, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w4, prev2, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w7, prev3, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w3, next1, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w6, next2, vl);
      vo1 = __riscv_vfmacc_vf_f32m4(vo1, w9, next3, vl);

      vfloat32m4_t vo2 = __riscv_vfmv_v_f_f32m4(w0, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w2, curr2, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w5, curr3, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w8, curr4, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w1, prev2, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w4, prev3, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w7, prev4, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w3, next2, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w6, next3, vl);
      vo2 = __riscv_vfmacc_vf_f32m4(vo2, w9, next4, vl);

      // Clamp
      vo0 = __riscv_vfmax_vf_f32m4(vo0, vmin, vl);
      vo1 = __riscv_vfmax_vf_f32m4(vo1, vmin, vl);
      vo2 = __riscv_vfmax_vf_f32m4(vo2, vmin, vl);

      vo0 = __riscv_vfmin_vf_f32m4(vo0, vmax, vl);
      vo1 = __riscv_vfmin_vf_f32m4(vo1, vmax, vl);
      vo2 = __riscv_vfmin_vf_f32m4(vo2, vmax, vl);

      // Store o2,o1,o0 (o0 LAST) — matches NEON so the valid row wins when small
      // output_height aliases o0==o1==o2 (else RVV's o2-last store keeps a zero-row result).
      __riscv_vse32_v_f32m4(o2_row, vo2, vl);
      __riscv_vse32_v_f32m4(o1_row, vo1, vl);
      __riscv_vse32_v_f32m4(o0_row, vo0, vl);

      i0_row += vl;
      i1_row += vl;
      i2_row += vl;
      i3_row += vl;
      i4_row += vl;

      o0_row += vl;
      o1_row += vl;
      o2_row += vl;

      n -= vl;
    }

    i0 = i3;
    i1 = i4;
    i2 = (const float*) ((uintptr_t) i1 + input_width);
    i3 = (const float*) ((uintptr_t) i2 + input_width);
    i4 = (const float*) ((uintptr_t) i3 + input_width);

    o0 = o2;
    o1 = (float*) ((uintptr_t) o0 + input_width);
    o2 = (float*) ((uintptr_t) o1 + input_width);

    output_height = doz(output_height, 3);
  } while (output_height != 0);
}