void test_rvv(
    const uint32_t* input,
    uint32_t* output,
    size_t input_stride,
    size_t output_stride,
    size_t block_width,
    size_t block_height) XNN_OOB_READS
{
  assert(block_width == 1 || output_stride >= block_height * sizeof(uint32_t));
  assert(block_height == 1 || input_stride >= block_width * sizeof(uint32_t));

  size_t c = 0;
  while (block_width > 0) {
    size_t vl = __riscv_vsetvl_e32m8(block_width);
    
    const uint8_t* i_row = (const uint8_t*)input + c * sizeof(uint32_t);
    uint8_t* o_col = (uint8_t*)output + c * output_stride;
    
    for (size_t r = 0; r < block_height; ++r) {
      vuint32m8_t v = __riscv_vle32_v_u32m8((const uint32_t*)i_row, vl);
      __riscv_vsse32_v_u32m8((uint32_t*)o_col, output_stride, v, vl);
      
      i_row += input_stride;
      o_col += sizeof(uint32_t);
    }
    
    c += vl;
    block_width -= vl;
  }
}