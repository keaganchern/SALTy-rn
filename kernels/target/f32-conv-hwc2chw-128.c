void test_rvv(
    size_t input_height,
    size_t input_width,
    size_t output_y_start,
    size_t output_y_end,
    const float* input,
    const float* zero,
    const float* weights,
    float* output,
    size_t input_padding_top,
    size_t output_channels,
    size_t output_height_stride,
    size_t output_channel_stride,
    const struct xnn_f32_minmax_params* restrict params) XNN_OOB_READS
{
  assert(input_width != 0);
  assert(output_y_end > output_y_start);
  assert(input_padding_top <= 1);
  assert(output_channels != 0);

  const size_t input_height_stride = input_width * 3 /* channels */ * sizeof(float);
  const size_t output_width = (input_width + 1) / 2;

  // Adjustment for padding
  const float* i0 = (const float*) ((uintptr_t) input + input_height_stride * (output_y_start * 2 - input_padding_top));
  const float* i1 = (const float*) ((uintptr_t) i0 + input_height_stride);
  const float* i2 = (const float*) ((uintptr_t) i1 + input_height_stride);
  const float* i3 = (const float*) ((uintptr_t) i2 + input_height_stride);
  const float* i4 = (const float*) ((uintptr_t) i3 + input_height_stride);
  float* output0 = (float*) ((uintptr_t) output + output_height_stride * output_y_start);
  float* output1 = (float*) ((uintptr_t) output0 + output_height_stride);

  if XNN_UNPREDICTABLE(output_y_start < input_padding_top) {
    i0 = zero;
  }

  for (size_t output_y = output_y_start; output_y < output_y_end; output_y += 2) {
    const size_t input_y2 = output_y * 2 + 2 - input_padding_top;
    const size_t input_y4 = input_y2 + 2;
    if XNN_UNPREDICTABLE(input_y2 >= input_height) {
      i2 = zero;
    }
    if XNN_UNPREDICTABLE(input_y4 > input_height) {
      i3 = zero;
    }
    if XNN_UNPREDICTABLE(input_y4 >= input_height) {
      i4 = zero;
    }

    const float* i_ptrs[5] = {i0, i1, i2, i3, i4};

    const float* w = weights;
    size_t c = output_channels;
    float* o0_c = output0;
    float* o1_c = output1;

    if XNN_UNPREDICTABLE(output_y + 2 > output_y_end) {
      o1_c = o0_c;
    }

    // VLA stripmine loop over output channels
    while (c > 0) {
      size_t vl = __riscv_vsetvl_e32m8(c);

      float* o0 = o0_c;
      float* o1 = o1_c;

      for (size_t ox = 0; ox < output_width; ox++) {
        // Load bias
        vfloat32m8_t vo0 = __riscv_vle32_v_f32m8(w, vl);
        vfloat32m8_t vo1 = vo0;

        // 3x3 spatial convolution over 3 input channels
        for (size_t fX = 0; fX < 3; fX++) {
          intptr_t ix = 2 * ox + fX - 1;
          int valid = (ix >= 0 && (size_t)ix < input_width);
          intptr_t ix_3 = ix * 3;

          for (size_t fC = 0; fC < 3; fC++) {
            intptr_t input_idx = ix_3 + fC;

            for (size_t fY = 0; fY < 3; fY++) {
              // Weights are packed as: bias, then [fX][fC][fY]
              size_t weight_idx = 1 + fX * 9 + fC * 3 + fY;
              vfloat32m8_t weight = __riscv_vle32_v_f32m8(w + weight_idx * vl, vl);

              // Out-of-bounds pixels are treated as 0.0f
              float in0 = valid ? i_ptrs[fY][input_idx] : 0.0f;
              float in1 = valid ? i_ptrs[fY + 2][input_idx] : 0.0f;

              vo0 = __riscv_vfmacc_vf_f32m8(vo0, in0, weight, vl);
              vo1 = __riscv_vfmacc_vf_f32m8(vo1, in1, weight, vl);
            }
          }
        }

        // Clamp
        vo0 = __riscv_vfmax_vf_f32m8(vo0, params->scalar.min, vl);
        vo1 = __riscv_vfmax_vf_f32m8(vo1, params->scalar.min, vl);
        vo0 = __riscv_vfmin_vf_f32m8(vo0, params->scalar.max, vl);
        vo1 = __riscv_vfmin_vf_f32m8(vo1, params->scalar.max, vl);

        // Strided store to planar output layout
        __riscv_vsse32_v_f32m8(o1, output_channel_stride, vo1, vl);
        __riscv_vsse32_v_f32m8(o0, output_channel_stride, vo0, vl);

        o1 += 1;
        o0 += 1;
      }

      // Advance weights by 28 vectors (1 bias + 27 weights)
      w += 28 * vl;
      o0_c = (float*) ((uintptr_t) o0_c + vl * output_channel_stride);
      o1_c = (float*) ((uintptr_t) o1_c + vl * output_channel_stride);
      c -= vl;
    }

    // Move output pointers forward to the next two rows
    output0 = (float*) ((uintptr_t) output1 + output_height_stride);
    output1 = (float*) ((uintptr_t) output0 + output_height_stride);
    
    // Move input pointers forward to the next four rows
    i0 = i4;
    i1 = (const float*) ((uintptr_t) i0 + input_height_stride);
    i2 = (const float*) ((uintptr_t) i1 + input_height_stride);
    i3 = (const float*) ((uintptr_t) i2 + input_height_stride);
    i4 = (const float*) ((uintptr_t) i3 + input_height_stride);
  }
}