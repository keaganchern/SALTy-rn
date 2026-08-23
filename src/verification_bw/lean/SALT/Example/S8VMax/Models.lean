-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Example.S8VMax

def neonSourceSha256 : String :=
  "fa1d4cdfcdfa9f19312377664f7524cb3c4f48f052cb13f7ddaecedbe3ab2ade"
def rvvSourceSha256 : String :=
  "3b204e9cb0ac317bd8a2123daa552e2a13faffc075905a2886ce180a39805b33"
def neonPreprocessedSha256 : String :=
  "89ccace9e5a75e65a5ed2ad359129651f956861e26dcab971837e65aa57db16b"
def rvvPreprocessedSha256 : String :=
  "5b6c8dcf07364bf3737645e46a6528dee2667f31b2e65988559e9c7a2c7fc6c3"
def parseFacadeSha256 : String :=
  "eff6d9864387e1b66d1b6980dcae589ac17dc7d8bf65e650bfee350a1c5655c4"
def registrySha256 : String :=
  "90987bb3357264eb6175e2b0d77197d4d441b94c9e0f35dec2bbdd46cb8a8a7d"

structure S8VMaxParams where
  threshold : BitVec 8
  deriving Repr, DecidableEq

def neonBlock16FromIntrinsics (p : S8VMaxParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vthreshold_0 := List.replicate 16 ((p.threshold).truncate 8)
  let vx_0 := (input).take 16
  let vx_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vx_0) (vthreshold_0)
  (vx_1)

def rvvChunkFromIntrinsics (p : S8VMaxParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_1 := SALT.Intrinsics.RVV.vmax_vx (vx_0) ((p.threshold).truncate 8)
  vx_1

end SALT.Example.S8VMax
