/* Parsed together with the pinned s8_vmax_example.h facade. */
void test_neon(
    size_t batch,
    const int8_t* input,
    int8_t* output,
    const struct salt_s8_vmax_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % 16 == 0);
  assert(input != NULL);
  assert(output != NULL);

  const int8x16_t vthreshold = vdupq_n_s8(params->scalar.threshold);

  for (; batch >= 16; batch -= 16) {
    int8x16_t vx = vld1q_s8(input); input += 16;
    vx = vmaxq_s8(vx, vthreshold);
    vst1q_s8(output, vx); output += 16;
  }
}
