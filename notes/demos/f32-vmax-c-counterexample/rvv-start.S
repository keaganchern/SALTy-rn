  .text
  .globl _start
_start:
  li sp, 0x80010000

  /* Enable floating-point and vector state in mstatus. */
  li t0, 0x6600
  csrs mstatus, t0

  call run_rvv_original

  /*
   * The C result remains in a0.  Add one only after the call so a zero result
   * becomes an observable nonzero register write in Spike's commit log.
   */
  addi a0, a0, 1
  ebreak
