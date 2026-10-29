"""Regression coverage for post-search proof generation and acceptance."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.workflow.config import Config
from src.workflow.optimize import bridge
from src.workflow.verification.orchestrator import VerificationResult, verify_rvv_pair
from src.workflow.verification.engine.emit import generate_harness


SOURCE = '''#include <stddef.h>
#include <riscv_vector.h>
void test_rvv(size_t n, const float* input, float* output) {
  while (n) {
    size_t vl = __riscv_vsetvl_e32m1(n);
    vfloat32m1_t v = __riscv_vle32_v_f32m1(input, vl);
    __riscv_vse32_v_f32m1(output, v, vl);
    input += vl; output += vl; n -= vl;
  }
}
'''


def test_rvv_harness_uses_both_bodies_and_exact_bits(tmp_path):
    ref, candidate = tmp_path / 'ref.c', tmp_path / 'candidate.c'
    ref.write_text(SOURCE)
    candidate.write_text(SOURCE.replace('output, v, vl', 'output, __riscv_vfneg_v_f32m1(v, vl), vl'))
    harness = generate_harness(str(ref), str(candidate), 'f32-vmul', reference_isa='rvv')
    assert 'neon_kernel::test_rvv(' in harness
    assert 'rvv_kernel ::test_rvv(' in harness
    assert '__riscv_vfneg_v_f32m1' in harness
    assert 'ElementKind::UINT, 0)' in harness
    assert '#include <riscv_vector.h>' not in harness


def test_legacy_neon_generation(tmp_path):
    ref, candidate = tmp_path / 'ref.c', tmp_path / 'candidate.c'
    ref.write_text(SOURCE.replace('test_rvv', 'test_neon'))
    candidate.write_text(SOURCE)
    assert 'neon_kernel::test_neon(' in generate_harness(str(ref), str(candidate), 'copy')


def test_wrapper_pins_workload_and_isa():
    with patch('src.workflow.verification.orchestrator.verify_kernel') as verify:
        verify_rvv_pair('baseline.c', 'candidate.c', batch=13, vlen=512)
        assert verify.call_args.kwargs == dict(reference_isa='rvv', min_batch=13,
                                               max_batch=13, vlen=512)
    with pytest.raises(ValueError):
        verify_rvv_pair('a', 'b', batch=0, vlen=512)


@pytest.mark.parametrize('verdict,maximum,accepted', [
    ('ALL_PASSED', 13, True), ('ALL_PASSED', 12, False),
    ('PARTIAL', 13, False), ('COUNTEREXAMPLE', 13, False),
    ('COMPILE_ERROR', 0, False), ('EMPTY_RANGE', 0, False),
])
def test_acceptance_preserves_baseline_and_rejected_output(tmp_path, verdict, maximum, accepted):
    cfg = Config(kernels_dir=tmp_path, verification_batch=13, vlen=512)
    cfg.target_dir.mkdir()
    baseline = cfg.target_dir / 'copy-512.c'
    baseline.write_text(SOURCE)
    out_dir = tmp_path / 'run'
    out_dir.mkdir()
    (out_dir / 'best_candidate_so_far.c').write_text(SOURCE.replace('test_rvv', 'test'))
    previous = tmp_path / 'target_optimized' / 'copy-512.c'
    previous.parent.mkdir()
    previous.write_text('previous verified result')
    result = VerificationResult('copy', verdict, max_verified_batch=maximum)
    with patch.object(bridge, 'SALTY_SOL_DIR', tmp_path / 'sols'), \
         patch.object(bridge, '_run_autocomp', return_value=out_dir), \
         patch('src.workflow.verification.orchestrator.verify_rvv_pair', return_value=result) as verify:
        optimized = bridge.optimize_kernel('copy', 0, cfg)
    assert optimized.success is accepted
    assert baseline.read_text() == SOURCE
    assert previous.read_text() == (SOURCE if accepted else 'previous verified result')
    assert verify.call_args.kwargs['vlen'] == cfg.autocomp_vlen
    assert verify.call_args.kwargs['batch'] == 13
    assert Path(verify.call_args.args[0]).read_text() == SOURCE
    assert json.loads((out_dir / 'verification.json').read_text())['verdict'] == verdict


def test_no_workload_stops_before_search(tmp_path):
    with patch.object(bridge, '_run_autocomp') as search:
        result = bridge.optimize_kernel('copy', 0, Config(kernels_dir=tmp_path))
    assert not result.success
    search.assert_not_called()


@pytest.mark.parametrize('mutation,exception', [
    (lambda s: s.replace('size_t n', 'int n'), ValueError),
    (lambda s: s.replace('float* output', 'float* other'), NotImplementedError),
    (lambda s: s.replace('__riscv_vse32_v_f32m1(output, v, vl);', '*output = 0;'), NotImplementedError),
])
def test_unsupported_or_mismatched_candidate_is_rejected(tmp_path, mutation, exception):
    ref, candidate = tmp_path / 'ref.c', tmp_path / 'candidate.c'
    ref.write_text(SOURCE)
    candidate.write_text(mutation(SOURCE))
    with pytest.raises(exception):
        generate_harness(str(ref), str(candidate), 'copy', reference_isa='rvv')


def test_multiple_outputs_are_conjoined(tmp_path):
    ref = tmp_path / 'ref.c'
    ref.write_text(SOURCE.replace('float* output)', 'float* output, float* second)'))
    harness = generate_harness(str(ref), str(ref), 'copy', reference_isa='rvv')
    assert 'Term eq = ctx.land_(' in harness
    assert '_b_second_neon, _b_second_rvv' in harness


def test_neon_shape_fixture_is_not_used_for_rvv_proof(tmp_path):
    ref = tmp_path / 'ref.c'
    ref.write_text(SOURCE)
    with patch('src.workflow.verification.engine.emit._match_fixture', return_value=object()):
        with pytest.raises(NotImplementedError, match='explicit shape fixture'):
            generate_harness(str(ref), str(ref), 'copy', reference_isa='rvv')


@pytest.mark.skipif(not (bridge.PROJECT_ROOT / 'third_party/cvc5/install/include/cvc5/cvc5.h').exists(),
                    reason='cvc5 C++ installation required')
@pytest.mark.parametrize('different', [False, True])
def test_solver_accepts_lmul_change_and_rejects_changed_output(tmp_path, different):
    ref, candidate = tmp_path / 'ref.c', tmp_path / 'candidate.c'
    ref.write_text(SOURCE)
    code = SOURCE.replace('m1', 'm2')
    if different:
        code = code.replace('output, v, vl', 'output, __riscv_vfneg_v_f32m2(v, vl), vl')
    candidate.write_text(code)
    result = verify_rvv_pair(str(ref), str(candidate), batch=17, vlen=128,
                             time_budget=30, backend='cvc5', build_dir=tmp_path / 'build')
    assert result.verdict == ('COUNTEREXAMPLE' if different else 'ALL_PASSED')
