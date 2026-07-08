void test_rvv(
    size_t batch,
    const float* input,
    uint16_t* output,
    const void* params)
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const uint32_t vexp_bias = UINT32_C(0x07800000);
  const float vscale_to_inf = 0x1.0p+112f;
  const uint32_t vexpw_max = UINT32_C(0x7F800000);
  const float vscale_to_zero = 0x1.0p-110f;
  const uint32_t vbias_min = UINT32_C(0x40000000);
  const uint16_t vexph_mask = UINT16_C(0x7C00);
  const uint16_t vmanth_mask = UINT16_C(0x0FFF);
  const uint16_t vsignh_mask = UINT16_C(0x8000);
  const uint16_t vnanh = UINT16_C(0x7E00);

  size_t n = batch / sizeof(float);
  while (n > 0) {
    size_t vl = __riscv_vsetvl_e32m8(n);

    vfloat32m8_t vx = __riscv_vle32_v_f32m8(input, vl);

    vfloat32m8_t vabsx = __riscv_vfabs_v_f32m8(vx, vl);
    vuint32m8_t vabsx_u32 = __riscv_vreinterpret_v_f32m8_u32m8(vabsx);

    vuint32m8_t vbias = __riscv_vadd_vx_u32m8(vabsx_u32, vexp_bias, vl);

    vfloat32m8_t vf = __riscv_vfmul_vf_f32m8(vabsx, vscale_to_inf, vl);
    vbool4_t vnanmaskw = __riscv_vmsgtu_vx_u32m8_b4(vabsx_u32, vexpw_max, vl);

    vbias = __riscv_vand_vx_u32m8(vbias, vexpw_max, vl);
    vf = __riscv_vfmul_vf_f32m8(vf, vscale_to_zero, vl);

    vbias = __riscv_vmaxu_vx_u32m8(vbias, vbias_min, vl);

    vfloat32m8_t vbias_f32 = __riscv_vreinterpret_v_u32m8_f32m8(vbias);
    vf = __riscv_vfadd_vv_f32m8(vf, vbias_f32, vl);

    vuint32m8_t vf_u32 = __riscv_vreinterpret_v_f32m8_u32m8(vf);
    vuint32m8_t vx_u32 = __riscv_vreinterpret_v_f32m8_u32m8(vx);

    vuint16m4_t vexph = __riscv_vnsrl_wx_u16m4(vf_u32, 13, vl);
    vuint16m4_t vmanth = __riscv_vnsrl_wx_u16m4(vf_u32, 0, vl);
    vuint16m4_t vsignh = __riscv_vnsrl_wx_u16m4(vx_u32, 16, vl);

    vexph = __riscv_vand_vx_u16m4(vexph, vexph_mask, vl);
    vmanth = __riscv_vand_vx_u16m4(vmanth, vmanth_mask, vl);
    vsignh = __riscv_vand_vx_u16m4(vsignh, vsignh_mask, vl);

    vuint16m4_t vh = __riscv_vadd_vv_u16m4(vmanth, vexph, vl);

    vh = __riscv_vmerge_vxm_u16m4(vh, vnanh, vnanmaskw, vl);

    vh = __riscv_vor_vv_u16m4(vh, vsignh, vl);

    __riscv_vse16_v_u16m4(output, vh, vl);

    input += vl;
    output += vl;
    n -= vl;
  }
}