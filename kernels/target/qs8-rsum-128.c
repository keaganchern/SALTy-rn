void test_rvv(
    size_t batch,
    const int8_t* input,
    int32_t* output,
    const struct xnn_qs8_rsum_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(input != NULL);
  assert(output != NULL);
  assert(params != NULL);

  // Use LMUL=8 for int32 to maximize elements processed per iteration.
  // This corresponds to LMUL=2 for the int8 input.
  size_t vlmax = __riscv_vsetvlmax_e32m8();
  
  // Initialize the accumulator vector with zeros for all VLMAX elements.
  vint32m8_t vacc = __riscv_vmv_v_x_i32m8(0, vlmax);

  for (; batch > 0; ) {
    size_t vl = __riscv_vsetvl_e8m2(batch);
    
    // Load int8 elements
    vint8m2_t vt = __riscv_vle8_v_i8m2(input, vl);
    
    // Sign-extend directly from int8 to int32
    vint32m8_t vt32 = __riscv_vsext_vf4_i32m8(vt, vl);
    
    // Accumulate into vacc. 
    // We use the tail-undisturbed (_tu) policy so that in the final iteration 
    // (where vl < vlmax), the previously accumulated sums in the tail elements 
    // of vacc are preserved rather than clobbered.
    vacc = __riscv_vadd_vv_i32m8_tu(vacc, vacc, vt32, vl);
    
    input += vl;
    batch -= vl;
  }

  // Perform a single horizontal reduction over the full VLMAX vector.
  // Because we used _tu, the tail elements from the last iteration safely 
  // retain their partial sums and are correctly included in the final total.
  vint32m1_t vres = __riscv_vmv_v_x_i32m1(0, vlmax);
  vres = __riscv_vredsum_vs_i32m8_i32m1(vacc, vres, vlmax);
  int32_t sum = __riscv_vmv_x_s_i32m1_i32(vres);

  *output += sum;
}