void test_rvv(
    size_t output_pixels,
    size_t pooling_elements,
    size_t channels,
    const float** input,
    size_t input_offset,
    size_t input_pixel_stride,
    float* output,
    uint32_t* index,
    size_t input_increment,
    size_t output_increment,
    size_t index_increment) XNN_OOB_READS
{
  assert(output_pixels != 0);
  assert(pooling_elements != 0);
  assert(channels != 0);

  do {
    // Accumulators start out null, after each pass the accumulator is set to
    // the output.
    const float* ab = NULL;
    const uint32_t* ib = NULL;
    const float** id = input;

    uint32_t idx0 = 0;

    assert(!ab);
    assert(!ib);

    int k = (int) pooling_elements;
    for (; k > 0; k -= 9) {
      const float* i0 = *id++;
      const float* i1 = 1 < k ? *id++ : i0;
      const float* i2 = 2 < k ? *id++ : i0;
      const float* i3 = 3 < k ? *id++ : i0;
      const float* i4 = 4 < k ? *id++ : i0;
      const float* i5 = 5 < k ? *id++ : i0;
      const float* i6 = 6 < k ? *id++ : i0;
      const float* i7 = 7 < k ? *id++ : i0;
      const float* i8 = 8 < k ? *id++ : i0;
      i0 = (const float*) ((uintptr_t) i0 + input_offset);
      i1 = (const float*) ((uintptr_t) i1 + input_offset);
      i2 = (const float*) ((uintptr_t) i2 + input_offset);
      i3 = (const float*) ((uintptr_t) i3 + input_offset);
      i4 = (const float*) ((uintptr_t) i4 + input_offset);
      i5 = (const float*) ((uintptr_t) i5 + input_offset);
      i6 = (const float*) ((uintptr_t) i6 + input_offset);
      i7 = (const float*) ((uintptr_t) i7 + input_offset);
      i8 = (const float*) ((uintptr_t) i8 + input_offset);

      float* o = output;
      uint32_t* i = index;
      const float* current_ab = ab;
      const uint32_t* current_ib = ib;
      size_t c = channels;
      
      while (c > 0) {
        size_t vl = __riscv_vsetvl_e32m8(c);

        vfloat32m8_t vi0 = __riscv_vle32_v_f32m8(i0, vl); i0 += vl;
        vfloat32m8_t vi1 = __riscv_vle32_v_f32m8(i1, vl); i1 += vl;
        vfloat32m8_t vi2 = __riscv_vle32_v_f32m8(i2, vl); i2 += vl;
        vfloat32m8_t vi3 = __riscv_vle32_v_f32m8(i3, vl); i3 += vl;
        vfloat32m8_t vi4 = __riscv_vle32_v_f32m8(i4, vl); i4 += vl;
        vfloat32m8_t vi5 = __riscv_vle32_v_f32m8(i5, vl); i5 += vl;
        vfloat32m8_t vi6 = __riscv_vle32_v_f32m8(i6, vl); i6 += vl;
        vfloat32m8_t vi7 = __riscv_vle32_v_f32m8(i7, vl); i7 += vl;
        vfloat32m8_t vi8 = __riscv_vle32_v_f32m8(i8, vl); i8 += vl;

        vfloat32m8_t vmax;
        vuint32m8_t vidx;
        if (current_ab) {
          vmax = __riscv_vle32_v_f32m8(current_ab, vl); current_ab += vl;
          vidx = __riscv_vle32_v_u32m8(current_ib, vl); current_ib += vl;

          vbool4_t vm0 = __riscv_vmfgt_vv_f32m8_b4(vi0, vmax, vl);
          vmax = __riscv_vmerge_vvm_f32m8(vmax, vi0, vm0, vl);
          vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0, vm0, vl);
        } else {
          vmax = vi0;
          vidx = __riscv_vmv_v_x_u32m8(idx0, vl);
        }

        vbool4_t vm1 = __riscv_vmfgt_vv_f32m8_b4(vi1, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi1, vm1, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 1, vm1, vl);

        vbool4_t vm2 = __riscv_vmfgt_vv_f32m8_b4(vi2, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi2, vm2, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 2, vm2, vl);

        vbool4_t vm3 = __riscv_vmfgt_vv_f32m8_b4(vi3, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi3, vm3, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 3, vm3, vl);

        vbool4_t vm4 = __riscv_vmfgt_vv_f32m8_b4(vi4, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi4, vm4, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 4, vm4, vl);

        vbool4_t vm5 = __riscv_vmfgt_vv_f32m8_b4(vi5, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi5, vm5, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 5, vm5, vl);

        vbool4_t vm6 = __riscv_vmfgt_vv_f32m8_b4(vi6, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi6, vm6, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 6, vm6, vl);

        vbool4_t vm7 = __riscv_vmfgt_vv_f32m8_b4(vi7, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi7, vm7, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 7, vm7, vl);

        vbool4_t vm8 = __riscv_vmfgt_vv_f32m8_b4(vi8, vmax, vl);
        vmax = __riscv_vmerge_vvm_f32m8(vmax, vi8, vm8, vl);
        vidx = __riscv_vmerge_vxm_u32m8(vidx, idx0 + 8, vm8, vl);

        __riscv_vse32_v_f32m8(o, vmax, vl); o += vl;
        __riscv_vse32_v_u32m8(i, vidx, vl); i += vl;

        c -= vl;
      }
      idx0 += 9;
      ab = output;
      ib = index;
    }

    input = (const float**) ((uintptr_t) input + input_increment);
    input_offset += input_pixel_stride;
    output = (float*) ((uintptr_t) output + output_increment);
    index = (uint32_t*) ((uintptr_t) index + index_increment);
  } while (--output_pixels != 0);
}