void test_rvv(
    size_t rows,
    size_t channels,
    const int8_t* input,
    size_t input_stride,
    const int8_t* zero,
    int32_t* output,
    const struct xnn_qs8_rsum_params* restrict params) XNN_OOB_READS
{
  assert(rows != 0);
  assert(channels != 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t input_increment = 7 * input_stride;

  while (channels > 0) {
    size_t vl = __riscv_vsetvl_e8m2(channels);

    vint32m8_t vacc = __riscv_vmv_v_x_i32m8(0, vl);

    int r = rows;
    const int8_t* i0 = input;
    const int8_t* i1 = (const int8_t*) ((uintptr_t) input + 1 * input_stride);
    const int8_t* i2 = (const int8_t*) ((uintptr_t) input + 2 * input_stride);
    const int8_t* i3 = (const int8_t*) ((uintptr_t) input + 3 * input_stride);
    const int8_t* i4 = (const int8_t*) ((uintptr_t) input + 4 * input_stride);
    const int8_t* i5 = (const int8_t*) ((uintptr_t) input + 5 * input_stride);
    const int8_t* i6 = (const int8_t*) ((uintptr_t) input + 6 * input_stride);

    while (r > 0) {
      vint16m4_t vacc16 = __riscv_vmv_v_x_i16m4(0, vl);
      int current_batch = r < 252 ? r : 252;
      r -= current_batch;

      for (; current_batch > 0; current_batch -= 7) {
        if XNN_UNPREDICTABLE(current_batch < 2) {
          i1 = zero;
        }
        if XNN_UNPREDICTABLE(current_batch <= 2) {
          i2 = zero;
        }
        if XNN_UNPREDICTABLE(current_batch < 4) {
          i3 = zero;
        }
        if XNN_UNPREDICTABLE(current_batch <= 4) {
          i4 = zero;
        }
        if XNN_UNPREDICTABLE(current_batch < 6) {
          i5 = zero;
        }
        if XNN_UNPREDICTABLE(current_batch <= 6) {
          i6 = zero;
        }

        vint8m2_t vin0 = __riscv_vle8_v_i8m2(i0, vl);
        vint8m2_t vin1 = __riscv_vle8_v_i8m2(i1, vl);
        vint8m2_t vin2 = __riscv_vle8_v_i8m2(i2, vl);
        vint8m2_t vin3 = __riscv_vle8_v_i8m2(i3, vl);
        vint8m2_t vin4 = __riscv_vle8_v_i8m2(i4, vl);
        vint8m2_t vin5 = __riscv_vle8_v_i8m2(i5, vl);
        vint8m2_t vin6 = __riscv_vle8_v_i8m2(i6, vl);

        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin0, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin1, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin2, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin3, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin4, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin5, vl);
        vacc16 = __riscv_vwadd_wv_i16m4(vacc16, vin6, vl);

        i0 = (const int8_t*) ((uintptr_t) i0 + input_increment);
        i1 = (const int8_t*) ((uintptr_t) i1 + input_increment);
        i2 = (const int8_t*) ((uintptr_t) i2 + input_increment);
        i3 = (const int8_t*) ((uintptr_t) i3 + input_increment);
        i4 = (const int8_t*) ((uintptr_t) i4 + input_increment);
        i5 = (const int8_t*) ((uintptr_t) i5 + input_increment);
        i6 = (const int8_t*) ((uintptr_t) i6 + input_increment);
      }
      vacc = __riscv_vwadd_wv_i32m8(vacc, vacc16, vl);
    }

    vint32m8_t vo = __riscv_vle32_v_i32m8(output, vl);
    vo = __riscv_vadd_vv_i32m8(vo, vacc, vl);
    __riscv_vse32_v_i32m8(output, vo, vl);

    input += vl;
    output += vl;
    channels -= vl;
  }
}