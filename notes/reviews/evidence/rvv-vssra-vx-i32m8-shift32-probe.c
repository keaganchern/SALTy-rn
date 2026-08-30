#include <riscv_vector.h>

#include <stddef.h>
#include <stdint.h>

unsigned int run_vssra(unsigned int input, size_t shift) {
  const size_t vl = __riscv_vsetvl_e32m8(1);
  vint32m8_t value = __riscv_vmv_v_x_i32m8((int32_t) input, vl);
  value = __riscv_vssra_vx_i32m8(value, shift, __RISCV_VXRM_RNU, vl);
  int32_t output = 0;
  __riscv_vse32_v_i32m8(&output, value, vl);
  return (unsigned int) output;
}
