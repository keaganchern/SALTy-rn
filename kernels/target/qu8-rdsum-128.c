void test_rvv(
    size_t rows,
    size_t channels,
    const uint8_t* input,
    size_t input_stride,
    const uint8_t* zero,
    uint32_t* output,
    const struct xnn_qs8_rsum_params* restrict params)
{
  assert(rows != 0);
  assert(channels != 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t input_increment = 7 * input_stride;

  while (channels > 0) {
    size_t vl = __riscv_vsetvl_e32m8(channels);

    const uint8_t* i0 = input;
    const uint8_t* i1 = (const uint8_t*) ((uintptr_t) input + 1 * input_stride);
    const uint8_t* i2 = (const uint8_t*) ((uintptr_t) input + 2 * input_stride);
    const uint8_t* i3 = (const uint8_t*) ((uintptr_t) input + 3 * input_stride);
    const uint8_t* i4 = (const uint8_t*) ((uintptr_t) input + 4 * input_stride);
    const uint8_t* i5 = (const uint8_t*) ((uintptr_t) input + 5 * input_stride);
    const uint8_t* i6 = (const uint8_t*) ((uintptr_t) input + 6 * input_stride);

    vuint32m8_t vacc = __riscv_vmv_v_x_u32m8(0, vl);

    int r = rows;
    while (r > 0) {
      vuint16m4_t vacc16 = __riscv_vmv_v_x_u16m4(0, vl);
      int current_batch = r < 252 ? r : 252;
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

        vuint8m2_t vin0 = __riscv_vle8_v_u8m2(i0, vl);
        vuint8m2_t vin1 = __riscv_vle8_v_u8m2(i1, vl);
        vuint8m2_t vin2 = __riscv_vle8_v_u8m2(i2, vl);
        vuint8m2_t vin3 = __riscv_vle8_v_u8m2(i3, vl);
        vuint8m2_t vin4 = __riscv_vle8_v_u8m2(i4, vl);
        vuint8m2_t vin5 = __riscv_vle8_v_u8m2(i5, vl);
        vuint8m2_t vin6 = __riscv_vle8_v_u8m2(i6, vl);

        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin0, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin1, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin2, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin3, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin4, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin5, vl);
        vacc16 = __riscv_vwaddu_wv_u16m4(vacc16, vin6, vl);

        i0 = (const uint8_t*) ((uintptr_t) i0 + input_increment);
        i1 = (const uint8_t*) ((uintptr_t) i1 + input_increment);
        i2 = (const uint8_t*) ((uintptr_t) i2 + input_increment);
        i3 = (const uint8_t*) ((uintptr_t) i3 + input_increment);
        i4 = (const uint8_t*) ((uintptr_t) i4 + input_increment);
        i5 = (const uint8_t*) ((uintptr_t) i5 + input_increment);
        i6 = (const uint8_t*) ((uintptr_t) i6 + input_increment);
      }
      vacc = __riscv_vwaddu_wv_u32m8(vacc, vacc16, vl);
      r = r < 252 ? 0 : r - 252;
    }

    vuint32m8_t vout = __riscv_vle32_v_u32m8(output, vl);
    vout = __riscv_vadd_vv_u32m8(vout, vacc, vl);
    __riscv_vse32_v_u32m8(output, vout, vl);

    input = (const uint8_t*) ((uintptr_t) input + vl * sizeof(uint8_t));
    output += vl;
    channels -= vl;
  }
}