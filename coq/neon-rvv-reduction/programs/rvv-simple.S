# Same u8 -> u32 sum kernel, using LMUL=1 instead of LMUL=8.
# n remains arbitrary; vsetvli chooses vl from n on EVERY iteration.
# uint64_t n in a0, uint8_t *input in a1, uint32_t *output in a2.
.option rvc
.text
.global sum_u8
.type sum_u8, @function
sum_u8:
    vsetvli a4, zero, e32, m1, ta, ma
    vmv.v.i v8, 0
    beqz a0, .Lfinish
.Lloop:
    vsetvli a5, a0, e32, m1, tu, ma
    vle8.v v2, (a1)
    sub a0, a0, a5
    add a1, a1, a5
    vzext.vf4 v16, v2
    vadd.vv v8, v8, v16
    bnez a0, .Lloop
.Lfinish:
    vsetvli a5, zero, e32, m1, ta, ma
    vmv.v.i v1, 0
    vsetvli a4, zero, e32, m1, ta, ma
    lw a3, 0(a2)
    vredsum.vs v8, v8, v1
    vmv.x.s a5, v8
    addw a5, a5, a3
    sw a5, 0(a2)
    ret
.size sum_u8, .-sum_u8
