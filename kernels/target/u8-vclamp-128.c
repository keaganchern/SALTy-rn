void test_rvv(
    size_t batch,
    const uint8_t* input,
    uint8_t* output,
    const struct xnn_u8_minmax_params* restrict params)
{
  assert(batch != 0);
  assert(batch % sizeof(uint8_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const uint8_t min = (uint8_t) params->scalar.min;
  const uint8_t max = (uint8_t) params->scalar.max;

  size_t vl;
  for (; batch > 0; batch -= vl) {
    vl = __riscv_vsetvl_e8m8(batch);
    
    vuint8m8_t vacc = __riscv_vle8_v_u8m8(input, vl);
    input += vl;

    vacc = __riscv_vmaxu_vx_u8m8(vacc, min, vl);
    vacc = __riscv_vminu_vx_u8m8(vacc, max, vl);

    __riscv_vse8_v_u8m8(output, vacc, vl);
    output += vl;
  }
}