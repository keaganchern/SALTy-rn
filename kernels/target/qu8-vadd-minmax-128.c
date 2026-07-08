void test_rvv(
    size_t batch,
    const uint8_t* input_a,
    const uint8_t* input_b,
    uint8_t* output,
    const struct xnn_qu8_add_minmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(uint8_t) == 0);
  assert(input_a != NULL);
  assert(input_b != NULL);
  assert(output != NULL);

  const int16_t a_zero_point = (int16_t)params->scalar.a_zero_point;
  const int16_t b_zero_point = (int16_t)params->scalar.b_zero_point;
  const int32_t a_multiplier = params->scalar.a_multiplier;
  const int32_t b_multiplier = params->scalar.b_multiplier;
  const size_t shift = (size_t)params->scalar.shift;
  const int16_t output_zero_point = params->scalar.output_zero_point;
  const uint8_t output_min = params->scalar.output_min;
  const uint8_t output_max = params->scalar.output_max;

  while (batch > 0) {
    size_t vl = __riscv_vsetvl_e8m2(batch);

    vuint8m2_t va = __riscv_vle8_v_u8m2(input_a, vl);
    vuint8m2_t vb = __riscv_vle8_v_u8m2(input_b, vl);

    // Widen uint8 -> uint16, reinterpret to int16, then subtract zero point
    vint16m4_t va_16 = __riscv_vreinterpret_v_u16m4_i16m4(__riscv_vzext_vf2_u16m4(va, vl));
    vint16m4_t vxa = __riscv_vsub_vx_i16m4(va_16, a_zero_point, vl);

    vint16m4_t vb_16 = __riscv_vreinterpret_v_u16m4_i16m4(__riscv_vzext_vf2_u16m4(vb, vl));
    vint16m4_t vxb = __riscv_vsub_vx_i16m4(vb_16, b_zero_point, vl);

    // Widen int16 -> int32 and multiply
    vint32m8_t vxa_32 = __riscv_vsext_vf2_i32m8(vxa, vl);
    vint32m8_t vacc = __riscv_vmul_vx_i32m8(vxa_32, a_multiplier, vl);

    // Widen int16 -> int32 and multiply-accumulate
    vint32m8_t vxb_32 = __riscv_vsext_vf2_i32m8(vxb, vl);
    vacc = __riscv_vmacc_vx_i32m8(vacc, b_multiplier, vxb_32, vl);

    // Rounding shift right
    vacc = __riscv_vssra_vx_i32m8(vacc, shift, __RISCV_VXRM_RNU, vl);

    // Saturating narrow int32 -> int16
    vint16m4_t vacc16 = __riscv_vnclip_wi_i16m4(vacc, 0, __RISCV_VXRM_RNU, vl);
    
    // Saturating add output zero point
    vacc16 = __riscv_vsadd_vx_i16m4(vacc16, output_zero_point, vl);

    // Saturating narrow signed int16 -> unsigned uint8 (vqmovun_s16 equivalent)
    vacc16 = __riscv_vmax_vx_i16m4(vacc16, (int16_t)0, vl);
    vuint16m4_t vacc16_u = __riscv_vreinterpret_v_i16m4_u16m4(vacc16);
    vuint8m2_t vout = __riscv_vnclipu_wi_u8m2(vacc16_u, 0, __RISCV_VXRM_RNU, vl);

    // Clamp to min/max
    vout = __riscv_vmaxu_vx_u8m2(vout, output_min, vl);
    vout = __riscv_vminu_vx_u8m2(vout, output_max, vl);

    __riscv_vse8_v_u8m2(output, vout, vl);

    input_a += vl;
    input_b += vl;
    output += vl;
    batch -= vl;
  }
}