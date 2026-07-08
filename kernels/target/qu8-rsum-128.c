void test_rvv(
    size_t batch,
    const uint8_t* input,
    uint32_t* output,
    const struct xnn_qs8_rsum_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(input != NULL);
  assert(output != NULL);
  assert(params != NULL);

  // e32m8 has the same VLMAX as e8m2 (VLEN/4 elements).
  size_t vlmax = __riscv_vsetvlmax_e32m8();
  vuint32m8_t vacc = __riscv_vmv_v_x_u32m8(0, vlmax);

  for (; batch > 0; ) {
    size_t vl = __riscv_vsetvl_e8m2(batch);
    vuint8m2_t vt = __riscv_vle8_v_u8m2(input, vl);
    
    // Zero-extend uint8 to uint32
    vuint32m8_t vt32 = __riscv_vzext_vf4_u32m8(vt, vl);
    
    // Accumulate using tail-undisturbed policy (_tu).
    // This ensures that when vl < vlmax (in the final iteration), the inactive 
    // lanes in the accumulator preserve their partial sums from previous iterations 
    // rather than being clobbered by tail-agnostic behavior.
    vacc = __riscv_vadd_vv_u32m8_tu(vacc, vacc, vt32, vl);
    
    input += vl;
    batch -= vl;
  }

  // Reduce the vector accumulator to a scalar sum
  vuint32m1_t red = __riscv_vmv_v_x_u32m1(0, __riscv_vsetvlmax_e32m1());
  red = __riscv_vredsum_vs_u32m8_u32m1(vacc, red, vlmax);
  *output += __riscv_vmv_x_s_u32m1_u32(red);
}