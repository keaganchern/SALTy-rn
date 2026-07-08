void test_rvv(
  size_t g,
  size_t nc,
  size_t kc,
  size_t nr,
  size_t kr,
  size_t sr,
  const uint32_t* weights,
  const uint32_t* bias,
  const void* scale,
  uint32_t* packed_weights,
  size_t extra_bytes,
  const void* params)
{
  assert(g != 0);
  assert(nc != 0);
  assert(kc != 0);
  assert(nr == 2);
  assert(kr == 1);
  assert(sr == 1);
  assert(weights != NULL);
  assert(packed_weights != NULL);

  do {
    // NC main loop multiple of 2
    const uint32_t* w0 = weights;
    size_t n = nc;

    for (; n >= 2; n -= 2) {
      if XNN_LIKELY(bias != NULL) {
        vuint32m1_t vb0 = __riscv_vle32_v_u32m1(bias, 2); bias += 2;
        __riscv_vse32_v_u32m1(packed_weights, vb0, 2); packed_weights += 2;
      } else {
        vuint32m1_t vzero = __riscv_vmv_v_x_u32m1(0, 2);
        __riscv_vse32_v_u32m1(packed_weights, vzero, 2); packed_weights += 2;
      }

      const uint32_t* w1 = w0 + kc;

      // KC main loop
      size_t k = kc;
      while (k > 0) {
        size_t vl = __riscv_vsetvl_e32m4(k);
        vuint32m4_t vw0 = __riscv_vle32_v_u32m4(w0, vl);
        vuint32m4_t vw1 = __riscv_vle32_v_u32m4(w1, vl);
        
        vuint32m4x2_t vw;
        vw = __riscv_vset_v_u32m4_u32m4x2(vw, 0, vw0);
        vw = __riscv_vset_v_u32m4_u32m4x2(vw, 1, vw1);
        
        __riscv_vsseg2e32_v_u32m4x2(packed_weights, vw, vl);
        
        w0 += vl;
        w1 += vl;
        packed_weights += 2 * vl;
        k -= vl;
      }

      packed_weights = (uint32_t*) ((uintptr_t) packed_weights + extra_bytes);
      w0 = w1;
    }

    if XNN_UNLIKELY(n != 0) {
      // NC remainder of 1
      if XNN_LIKELY(bias != NULL) {
        *packed_weights = *bias++;
      } else {
        vuint32m1_t vzero = __riscv_vmv_v_x_u32m1(0, 2);
        __riscv_vse32_v_u32m1(packed_weights, vzero, 2);
      }
      packed_weights += 2;
      
      size_t k = kc;
      while (k > 0) {
        size_t vl = __riscv_vsetvl_e32m4(k);
        vuint32m4_t vw0 = __riscv_vle32_v_u32m4(w0, vl);
        
        __riscv_vsse32_v_u32m4(packed_weights, 2 * sizeof(uint32_t), vw0, vl);
        
        w0 += vl;
        packed_weights += 2 * vl;
        k -= vl;
      }
      packed_weights = (uint32_t*) ((uintptr_t) packed_weights + extra_bytes);
    }
    weights += nc * kc;
  } while (--g != 0);
}