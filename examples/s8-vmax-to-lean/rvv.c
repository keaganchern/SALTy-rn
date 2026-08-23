/* Parsed together with the pinned s8_vmax_example.h facade. */
void test_rvv(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct salt_s8_vmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(input != NULL);
  assert(output != NULL);

  const int8_t threshold = params->scalar.threshold;

  while (batch > 0) {
    const size_t vl = __riscv_vsetvl_e8m8(batch);
    vint8m8_t vx = __riscv_vle8_v_i8m8(input, vl);
    vx = __riscv_vmax_vx_i8m8(vx, threshold, vl);
    __riscv_vse8_v_i8m8(output, vx, vl);
    input += vl;
    output += vl;
    batch -= vl;
  }
}
