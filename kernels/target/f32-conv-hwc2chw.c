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
  const size_t output_channel_increment = output_channel_stride * 4 - output_width * sizeof(float);

  // Adjustment for padding processed below
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
    if XNN_UNPREDICTABLE(output_y + 2 > output_y_end) {
      output1 = output0;
    }

    const float* w = weights;
    size_t c = output_channels;
    float* o0c0 = output0;
    float* o1c0 = output1;
    float* o0c1 = (float*) ((uintptr_t) o0c0 + output_channel_stride);
    float* o1c1 = (float*) ((uintptr_t) o1c0 + output_channel_stride);
    float* o0c2 = (float*) ((uintptr_t) o0c1 + output_channel_stride);
    float* o1c2 = (float*) ((uintptr_t) o1c1 + output_channel_stride);
    float* o0c3 = (float*) ((uintptr_t) o0c2 + output_channel_stride);
    float* o1c3 = (float*) ((uintptr_t) o1c2 + output_channel_stride);
    do {
      if XNN_UNPREDICTABLE(c < 2) {
        o0c1 = o0c0;
        o1c1 = o1c0;
      }
      if XNN_UNPREDICTABLE(c <= 2) {
        o0c2 = o0c1;
        o1c2 = o1c1;
      }
      if XNN_UNPREDICTABLE(c < 4) {
        o0c3 = o0c2;
        o1c3 = o1c2;
      }

      size_t ow = output_width;
      size_t ow_done = 0;
      
      // Base pointers shifted back by 1 pixel (3 channels) to ensure all indexed offsets are non-negative
      const float* i0_base = (const float*)((uintptr_t)i0 - 3 * sizeof(float));
      const float* i1_base = (const float*)((uintptr_t)i1 - 3 * sizeof(float));
      const float* i2_base = (const float*)((uintptr_t)i2 - 3 * sizeof(float));
      const float* i3_base = (const float*)((uintptr_t)i3 - 3 * sizeof(float));
      const float* i4_base = (const float*)((uintptr_t)i4 - 3 * sizeof(float));

      float* current_o0c0 = o0c0;
      float* current_o0c1 = o0c1;
      float* current_o0c2 = o0c2;
      float* current_o0c3 = o0c3;
      float* current_o1c0 = o1c0;
      float* current_o1c1 = o1c1;
      float* current_o1c2 = o1c2;
      float* current_o1c3 = o1c3;

      while (ow > 0) {
        // Isolate the final odd-width pixel: NEON omits its right-column FMAs.
        size_t chunk_width = ((input_width & 1) && ow > 1) ? ow - 1 : ow;
        size_t vl = __riscv_vsetvl_e32m1(chunk_width);
        vfloat32m1_t v_zero = __riscv_vfmv_v_f_f32m1(0.0f, vl);

        vuint32m1_t vj = __riscv_vid_v_u32m1(vl);
        vuint32m1_t v_j_plus_done = __riscv_vadd_vx_u32m1(vj, ow_done, vl);
        
        // v_idx_base_pos = 2 * (j + ow_done)
        vuint32m1_t v_idx_base_pos = __riscv_vmul_vx_u32m1(v_j_plus_done, 2, vl);
        // v_offset_base_pos = v_idx_base_pos * 3 channels * sizeof(float)
        vuint32m1_t v_offset_base_pos = __riscv_vmul_vx_u32m1(v_idx_base_pos, 12, vl);

        // True signed index for bounds checking: 2 * (j + ow_done) - 1
        vint32m1_t v_idx_base = __riscv_vsub_vx_i32m1(__riscv_vreinterpret_v_u32m1_i32m1(v_idx_base_pos), 1, vl);

        vfloat32m1_t v_o0c0 = __riscv_vfmv_v_f_f32m1(w[0], vl);
        vfloat32m1_t v_o0c1 = __riscv_vfmv_v_f_f32m1(w[1], vl);
        vfloat32m1_t v_o0c2 = __riscv_vfmv_v_f_f32m1(w[2], vl);
        vfloat32m1_t v_o0c3 = __riscv_vfmv_v_f_f32m1(w[3], vl);

        vfloat32m1_t v_o1c0 = __riscv_vfmv_v_f_f32m1(w[0], vl);
        vfloat32m1_t v_o1c1 = __riscv_vfmv_v_f_f32m1(w[1], vl);
        vfloat32m1_t v_o1c2 = __riscv_vfmv_v_f_f32m1(w[2], vl);
        vfloat32m1_t v_o1c3 = __riscv_vfmv_v_f_f32m1(w[3], vl);

        for (int dx = 0; dx < 3; dx++) {
          // The NEON odd-width tail omits right-column arithmetic entirely.
          // Zero padding alone would still evaluate 0 * Inf (or NaN).
          if ((input_width & 1) && ow == 1 && dx == 2) continue;
          vint32m1_t v_idx = __riscv_vadd_vx_i32m1(v_idx_base, dx, vl);
          vbool32_t mask = __riscv_vmand_mm_b32(
              __riscv_vmsge_vx_i32m1_b32(v_idx, 0, vl),
              __riscv_vmslt_vx_i32m1_b32(v_idx, input_width, vl),
              vl
          );

          for (int c_in = 0; c_in < 3; c_in++) {
            int32_t scalar_offset = (dx * 3 + c_in) * 4;
            // Per-lane offset is (lane+ow_done)*24 + scalar_offset: a fixed 24-byte stride,
            // so a strided load + mask-merge replaces the indexed gather (same values).
            const ptrdiff_t v_off = (ptrdiff_t)ow_done * 24 + scalar_offset;
            const ptrdiff_t v_str = 24;
            vfloat32m1_t v_in0 = __riscv_vmerge_vvm_f32m1(v_zero, __riscv_vlse32_v_f32m1((const float*)((uintptr_t)i0_base + v_off), v_str, vl), mask, vl);
            vfloat32m1_t v_in1 = __riscv_vmerge_vvm_f32m1(v_zero, __riscv_vlse32_v_f32m1((const float*)((uintptr_t)i1_base + v_off), v_str, vl), mask, vl);
            vfloat32m1_t v_in2 = __riscv_vmerge_vvm_f32m1(v_zero, __riscv_vlse32_v_f32m1((const float*)((uintptr_t)i2_base + v_off), v_str, vl), mask, vl);
            vfloat32m1_t v_in3 = __riscv_vmerge_vvm_f32m1(v_zero, __riscv_vlse32_v_f32m1((const float*)((uintptr_t)i3_base + v_off), v_str, vl), mask, vl);
            vfloat32m1_t v_in4 = __riscv_vmerge_vvm_f32m1(v_zero, __riscv_vlse32_v_f32m1((const float*)((uintptr_t)i4_base + v_off), v_str, vl), mask, vl);

            for (int ky = 0; ky < 3; ky++) {
              vfloat32m1_t v_in_row0 = (ky == 0) ? v_in0 : (ky == 1) ? v_in1 : v_in2;
              vfloat32m1_t v_in_row1 = (ky == 0) ? v_in2 : (ky == 1) ? v_in3 : v_in4;

              // NEON c3x4 plane order = kc*9 + ch*3 + kr (= dx*9 + c_in*3 + ky); aligns weight
              // reads with the gold so the shared symbolic weight buffer matches on both sides.
              int w_idx = (dx * 9 + c_in * 3 + ky) * 4;
              float w0 = w[4 + w_idx + 0];
              float w1 = w[4 + w_idx + 1];
              float w2 = w[4 + w_idx + 2];
              float w3 = w[4 + w_idx + 3];

              v_o0c0 = __riscv_vfmacc_vf_f32m1(v_o0c0, w0, v_in_row0, vl);
              v_o0c1 = __riscv_vfmacc_vf_f32m1(v_o0c1, w1, v_in_row0, vl);
              v_o0c2 = __riscv_vfmacc_vf_f32m1(v_o0c2, w2, v_in_row0, vl);
              v_o0c3 = __riscv_vfmacc_vf_f32m1(v_o0c3, w3, v_in_row0, vl);

              v_o1c0 = __riscv_vfmacc_vf_f32m1(v_o1c0, w0, v_in_row1, vl);
              v_o1c1 = __riscv_vfmacc_vf_f32m1(v_o1c1, w1, v_in_row1, vl);
              v_o1c2 = __riscv_vfmacc_vf_f32m1(v_o1c2, w2, v_in_row1, vl);
              v_o1c3 = __riscv_vfmacc_vf_f32m1(v_o1c3, w3, v_in_row1, vl);
            }
          }
        }

        v_o0c0 = __riscv_vfmax_vf_f32m1(v_o0c0, params->scalar.min, vl);
        v_o0c1 = __riscv_vfmax_vf_f32m1(v_o0c1, params->scalar.min, vl);
        v_o0c2 = __riscv_vfmax_vf_f32m1(v_o0c2, params->scalar.min, vl);
        v_o0c3 = __riscv_vfmax_vf_f32m1(v_o0c3, params->scalar.min, vl);

        v_o1c0 = __riscv_vfmax_vf_f32m1(v_o1c0, params->scalar.min, vl);
        v_o1c1 = __riscv_vfmax_vf_f32m1(v_o1c1, params->scalar.min, vl);
        v_o1c2 = __riscv_vfmax_vf_f32m1(v_o1c2, params->scalar.min, vl);
        v_o1c3 = __riscv_vfmax_vf_f32m1(v_o1c3, params->scalar.min, vl);

        v_o0c0 = __riscv_vfmin_vf_f32m1(v_o0c0, params->scalar.max, vl);
        v_o0c1 = __riscv_vfmin_vf_f32m1(v_o0c1, params->scalar.max, vl);
        v_o0c2 = __riscv_vfmin_vf_f32m1(v_o0c2, params->scalar.max, vl);
        v_o0c3 = __riscv_vfmin_vf_f32m1(v_o0c3, params->scalar.max, vl);

        v_o1c0 = __riscv_vfmin_vf_f32m1(v_o1c0, params->scalar.max, vl);
        v_o1c1 = __riscv_vfmin_vf_f32m1(v_o1c1, params->scalar.max, vl);
        v_o1c2 = __riscv_vfmin_vf_f32m1(v_o1c2, params->scalar.max, vl);
        v_o1c3 = __riscv_vfmin_vf_f32m1(v_o1c3, params->scalar.max, vl);

        // Store row 1 BEFORE row 0: when there is a single output row the caller
        // aliases output1==output0, so the LAST store must be the valid row 0
        // (matches the NEON gold; storing o0 last fixes the row-1-overwrites-row-0 bug).
        __riscv_vse32_v_f32m1(current_o1c0, v_o1c0, vl); current_o1c0 += vl;
        __riscv_vse32_v_f32m1(current_o1c1, v_o1c1, vl); current_o1c1 += vl;
        __riscv_vse32_v_f32m1(current_o1c2, v_o1c2, vl); current_o1c2 += vl;
        __riscv_vse32_v_f32m1(current_o1c3, v_o1c3, vl); current_o1c3 += vl;

        __riscv_vse32_v_f32m1(current_o0c0, v_o0c0, vl); current_o0c0 += vl;
        __riscv_vse32_v_f32m1(current_o0c1, v_o0c1, vl); current_o0c1 += vl;
        __riscv_vse32_v_f32m1(current_o0c2, v_o0c2, vl); current_o0c2 += vl;
        __riscv_vse32_v_f32m1(current_o0c3, v_o0c3, vl); current_o0c3 += vl;

        ow -= vl;
        ow_done += vl;
      }

      o0c0 = (float*) ((uintptr_t) current_o0c0 + output_channel_increment);
      o0c1 = (float*) ((uintptr_t) current_o0c1 + output_channel_increment);
      o0c2 = (float*) ((uintptr_t) current_o0c2 + output_channel_increment);
      o0c3 = (float*) ((uintptr_t) current_o0c3 + output_channel_increment);
      o1c0 = (float*) ((uintptr_t) current_o1c0 + output_channel_increment);
      o1c1 = (float*) ((uintptr_t) current_o1c1 + output_channel_increment);
      o1c2 = (float*) ((uintptr_t) current_o1c2 + output_channel_increment);
      o1c3 = (float*) ((uintptr_t) current_o1c3 + output_channel_increment);

      w += 112;
      c = (c > 4) ? c - 4 : 0;
    } while (c != 0);

    output0 = (float*) ((uintptr_t) output1 + output_height_stride);
    output1 = (float*) ((uintptr_t) output0 + output_height_stride);

    i0 = i4;
    i1 = (const float*) ((uintptr_t) i0 + input_height_stride);
    i2 = (const float*) ((uintptr_t) i1 + input_height_stride);
    i3 = (const float*) ((uintptr_t) i2 + input_height_stride);
    i4 = (const float*) ((uintptr_t) i3 + input_height_stride);
  }
}
