// void sum_u8(uint64_t n, const uint8_t *p, uint32_t *out)
// Input p is 16-byte aligned; out is 4-byte aligned, disjoint from input.
// All n are allowed subject to readable input/address-space bounds.
// No padding read, lookup table, 2048-byte block, or persistent u16 accumulator.
.text
.global sum_u8
.type sum_u8, %function
sum_u8:
    movi v0.2d, #0
.Lcheck:
    cmp x0, #16
    b.lo .Ltail
    ldr q2, [x1], #16
    movi v1.2d, #0
    uadalp v1.8h, v2.16b
    uadalp v0.4s, v1.8h
    sub x0, x0, #16
    b .Lcheck
.Ltail:
    addv s0, v0.4s
    fmov w9, s0
    cbz x0, .Lfinish
.Lbyte:
    ldrb w8, [x1], #1
    add w9, w9, w8
    subs x0, x0, #1
    b.ne .Lbyte
.Lfinish:
    ldr w8, [x2]
    add w8, w8, w9
    str w8, [x2]
    ret
.size sum_u8, .-sum_u8
