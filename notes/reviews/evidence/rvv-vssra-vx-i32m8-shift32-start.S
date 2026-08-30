  .text
  .globl _start
_start:
  li sp, 0x80010000
  li t0, 0x600
  csrs mstatus, t0
  li a0, 1
  li a1, 32
  call run_vssra
  ebreak
