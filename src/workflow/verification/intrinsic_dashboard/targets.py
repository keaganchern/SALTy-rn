"""Single-source metadata for the dashboard's designated proof cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .model import ClaimScope


@dataclass(frozen=True, slots=True)
class ProofTarget:
    module: str
    models_path: str
    proof_path: str
    contract_path: str
    claim_scope: ClaimScope


PROOF_CASES: Mapping[str, ProofTarget] = {
    "qs8-vadd-minmax": ProofTarget(
        module="SALT.Generated.QS8VAddMinmax.Proof",
        models_path="src/verification_bw/lean/SALT/Generated/QS8VAddMinmax/Models.lean",
        proof_path="src/verification_bw/lean/SALT/Generated/QS8VAddMinmax/Proof.lean",
        contract_path="src/verification_bw/lean/SALT/Kernel/QS8/Params.lean",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
    ),
    "s8-vclamp": ProofTarget(
        module="SALT.Generated.S8VClamp.AllLengths",
        models_path="src/verification_bw/lean/SALT/Generated/S8VClamp/Models.lean",
        proof_path="src/verification_bw/lean/SALT/Generated/S8VClamp/AllLengths.lean",
        contract_path="src/verification_bw/lean/SALT/Kernel/S8VClamp/Contract.lean",
        claim_scope=ClaimScope.ARBITRARY_LENGTH_VALUE,
    ),
    "qs8-vcvt": ProofTarget(
        module="SALT.Generated.QS8VCvt.Proof",
        models_path="src/verification_bw/lean/SALT/Generated/QS8VCvt/Models.lean",
        proof_path="src/verification_bw/lean/SALT/Generated/QS8VCvt/Proof.lean",
        contract_path="src/verification_bw/lean/SALT/Kernel/QS8VCvt/Contract.lean",
        claim_scope=ClaimScope.ARBITRARY_LENGTH_VALUE,
    ),
    "qs8-vlrelu": ProofTarget(
        module="SALT.Generated.QS8VLReLU.Proof",
        models_path="src/verification_bw/lean/SALT/Generated/QS8VLReLU/Models.lean",
        proof_path="src/verification_bw/lean/SALT/Generated/QS8VLReLU/Proof.lean",
        contract_path="src/verification_bw/lean/SALT/Kernel/QS8VLReLU/Contract.lean",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
    ),
    "qu8-vadd-minmax": ProofTarget(
        module="SALT.Generated.QU8VAddMinmax.Proof",
        models_path="src/verification_bw/lean/SALT/Generated/QU8VAddMinmax/Models.lean",
        proof_path="src/verification_bw/lean/SALT/Generated/QU8VAddMinmax/Proof.lean",
        contract_path="src/verification_bw/lean/SALT/Kernel/QU8VAddMinmax/Contract.lean",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
    ),
}
