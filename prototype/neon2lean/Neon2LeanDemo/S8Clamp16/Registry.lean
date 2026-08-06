import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.S8Clamp16

open Neon2LeanDemo.Production

private def i8 : ValueTag := .scalar (.int 8 .signed)
private def u64 : ValueTag := .scalar (.int 64 .unsigned)
private def fixed16 : ValueTag := .vector (.fixed 16) (.int 8 .signed)
private def scalableM1 : ValueTag := .vector (.scalable .m1) (.int 8 .signed)

def registryId : String := "saltyrn.s8-clamp16.integer.v1"

/-- Reviewed operation registry. Generated manifests only select entries by exact spelling. -/
def registry : TrustedOperationRegistry
  | "vld1q_s8" =>
      some
        { architecture := .neon
          family := .memory
          operandTypes := [.pointer]
          resultType := some fixed16
          rvvConfigShape := none
          opcode := .neonLoad16S8
          effect := .read }
  | "vdupq_n_s8" =>
      some
        { architecture := .neon
          family := .integer
          operandTypes := [i8]
          resultType := some fixed16
          rvvConfigShape := none
          opcode := .neonSplat16S8
          effect := .pure }
  | "vmaxq_s8" =>
      some
        { architecture := .neon
          family := .integer
          operandTypes := [fixed16, fixed16]
          resultType := some fixed16
          rvvConfigShape := none
          opcode := .neonSignedMaxS8
          effect := .pure }
  | "vminq_s8" =>
      some
        { architecture := .neon
          family := .integer
          operandTypes := [fixed16, fixed16]
          resultType := some fixed16
          rvvConfigShape := none
          opcode := .neonSignedMinS8
          effect := .pure }
  | "vst1q_s8" =>
      some
        { architecture := .neon
          family := .memory
          operandTypes := [.pointer, fixed16]
          resultType := none
          rvvConfigShape := none
          opcode := .neonStore16S8
          effect := .write }
  | "__riscv_vsetvl_e8m1" =>
      some
        { architecture := .rvv
          family := .control
          operandTypes := [u64]
          resultType := some u64
          rvvConfigShape := none
          opcode := .rvvSetVLE8M1
          effect := .control }
  | "__riscv_vle8_v_i8m1" =>
      some
        { architecture := .rvv
          family := .memory
          operandTypes := [.pointer, u64]
          resultType := some scalableM1
          rvvConfigShape := some { sew := 8, lmul := .m1 }
          opcode := .rvvLoadS8M1
          effect := .read }
  | "__riscv_vmax_vx_i8m1" =>
      some
        { architecture := .rvv
          family := .integer
          operandTypes := [scalableM1, i8, u64]
          resultType := some scalableM1
          rvvConfigShape := some { sew := 8, lmul := .m1 }
          opcode := .rvvSignedMaxScalarS8M1
          effect := .pure }
  | "__riscv_vmin_vx_i8m1" =>
      some
        { architecture := .rvv
          family := .integer
          operandTypes := [scalableM1, i8, u64]
          resultType := some scalableM1
          rvvConfigShape := some { sew := 8, lmul := .m1 }
          opcode := .rvvSignedMinScalarS8M1
          effect := .pure }
  | "__riscv_vse8_v_i8m1" =>
      some
        { architecture := .rvv
          family := .memory
          operandTypes := [.pointer, scalableM1, u64]
          resultType := none
          rvvConfigShape := some { sew := 8, lmul := .m1 }
          opcode := .rvvStoreS8M1
          effect := .write }
  | _ => none

end Neon2LeanDemo.S8Clamp16
