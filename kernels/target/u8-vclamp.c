void test_rvv(
    size_t batch,
    const uint8_t* input,
    uint8_t* output,
    const struct xnn_u8_minmax_params* params)
{
  assert(batch != 0);
  assert(batch % sizeof(uint8_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  const uint8_t voutput_min = (uint8_t) params->scalar.min;
  const uint8_t voutput_max = (uint8_t) params->scalar.max;

  size_t batch64 = batch & ~((size_t)63);
  while (batch64 > 0) {
    size_t vl = __riscv_vsetvl_e8m8(batch64);
    
    vuint8m8_t vacc = __riscv_vle8_v_u8m8(input, vl);
    
    vacc = __riscv_vmaxu_vx_u8m8(vacc, voutput_min, vl);
    vacc = __riscv_vminu_vx_u8m8(vacc, voutput_max, vl);
    
    __riscv_vse8_v_u8m8(output, vacc, vl);
    
    input += vl;
    output += vl;
    batch -= vl;
    batch64 -= vl;
  }

  while (batch > 0) {
    size_t vl = __riscv_vsetvl_e8m8(batch);
    
    vuint8m8_t vacc = __riscv_vle8_v_u8m8(input, vl);
    
    vacc = __riscv_vminu_vx_u8m8(vacc, voutput_max, vl);
    vacc = __riscv_vmaxu_vx_u8m8(vacc, voutput_min, vl);
    
    __riscv_vse8_v_u8m8(output, vacc, vl);
    
    input += vl;
    output += vl;
    batch -= vl;
  }
}