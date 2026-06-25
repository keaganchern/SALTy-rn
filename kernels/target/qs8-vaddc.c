#include <riscv_vector.h>
#include <stddef.h>
#include <stdint.h>
#include <assert.h>

void test_rvv(
    size_t batch,
    const int8_t* input_a,
    const int8_t* input_b,
    int8_t* output,
    const struct xnn_qs8_add_minmax_params* params)
{
  assert(batch != 0);
  assert(batch % sizeof(int8_t) == 0);
  assert(input_a != NULL);
  assert(input_b != NULL);
  assert(output != NULL);

  const int32_t vxb = (int32_t) *input_b - (int32_t) params->scalar.b_zero_point;
  const int32_t vb = params->scalar.b_multiplier;
  const int32_t vbias_val = vxb * vb;

  for (; batch > 0; ) {
    size_t vl = __riscv_vsetvl_e8m2(batch);

    vint8m2_t va = __riscv_vle8_v_i8m2(input_a, vl);
    input_a += vl;

    vint16m4_t vxa = __riscv_vwsub_vx_i16m4(va, (int8_t)params->scalar.a_zero_point, vl);

    vint32m8_t vxa32 = __riscv_vsext_vf2_i32m8(vxa, vl);
    vint32m8_t vbias_vec = __riscv_vmv_v_x_i32m8(vbias_val, vl);
    vint32m8_t vacc = __riscv_vmacc_vx_i32m8(vbias_vec, params->scalar.a_multiplier, vxa32, vl);

    vacc = __riscv_vssra_vx_i32m8(vacc, params->scalar.shift, __RISCV_VXRM_RNU, vl);

    vint16m4_t vacc16 = __riscv_vnclip_wx_i16m4(vacc, 0, __RISCV_VXRM_RNU, vl);
    vacc16 = __riscv_vsadd_vx_i16m4(vacc16, (int16_t)params->scalar.output_zero_point, vl);

    vint8m2_t vout = __riscv_vnclip_wx_i8m2(vacc16, 0, __RISCV_VXRM_RNU, vl);

    vout = __riscv_vmax_vx_i8m2(vout, (int8_t)params->scalar.output_min, vl);
    vout = __riscv_vmin_vx_i8m2(vout, (int8_t)params->scalar.output_max, vl);

    __riscv_vse8_v_i8m2(output, vout, vl);
    output += vl;
    batch -= vl;
  }
}