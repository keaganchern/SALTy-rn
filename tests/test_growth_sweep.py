import itertools
import os
import sys
import time

import pytest

from src.workflow.verification.engine.growth_sweep import PLANS, Plan, classify, execute_shape, fixture_for, frontier


@pytest.mark.parametrize('dimensions', [1, 2, 3])
def test_frontiers_cover_cube_once(dimensions):
    plan = Plan('test', tuple((f'd{i}', i + 1) for i in range(dimensions)))
    seen = []
    for level in range(1, 5):
        shell = list(frontier(plan, level))
        assert len(shell) == level**dimensions - (level-1)**dimensions
        for shape in shell:
            assert max(shape[f'd{i}'] // (i+1) for i in range(dimensions)) == level
        seen += [tuple(shape.values()) for shape in shell]
    assert len(seen) == len(set(seen)) == 4**dimensions
    assert set(seen) == set(itertools.product(*(range(i+1, 4*(i+1)+1, i+1) for i in range(dimensions))))


def test_bounded_rows_and_padding_are_fully_checked():
    gemm = next(p for p in PLANS if p.name == 'f32-gemm-minmax')
    assert len(list(frontier(gemm, 2))) == 12
    assert {s['mr'] for s in frontier(gemm, 2)} == {1,2,3,4}
    assert all(s['kc'] % 4 == 0 for s in frontier(gemm, 2))
    pack = next(p for p in PLANS if p.name == 'x32-packw-gemm-goi')
    assert {s['extra_bytes'] for s in frontier(pack, 1)} == {0,8}


@pytest.mark.parametrize('code,events,status', [
    (0, [{'status':'SOLVING'}, {'status':'VERIFIED'}], 'VERIFIED'),
    (0, [{'status':'ALL_VERIFIED'}], 'ERROR'),
    (0, [{'status':'TIMEOUT'}, {'status':'ALL_VERIFIED'}], 'ERROR'),
    (-9, [{'status':'SOLVING'}, {'status':'VERIFIED'}], 'ERROR'),
    (2, [{'status':'SOLVING'}, {'status':'TIMEOUT'}], 'TIMEOUT'),
    (1, [{'status':'SOLVING'}, {'status':'COUNTEREXAMPLE'}], 'COUNTEREXAMPLE'),
])
def test_no_false_pass_from_missing_or_failed_result(code, events, status):
    assert classify(code, events) == status


def test_hard_deadline_works_without_stdout():
    start = time.monotonic()
    result = execute_shape([sys.executable, '-c', 'import time; time.sleep(30)'], 0.1, os.environ.copy())
    assert result['status'] == 'TIMEOUT'
    assert result['hard_deadline']
    assert time.monotonic() - start < 2


def test_growth_fixtures_are_nonvacuous_and_support_multiple_tiles():
    dw = next(p for p in PLANS if p.name == 'f32-dwconv-minmax')
    *_, spec, _ = fixture_for(dw)
    assert spec.params[1]['scalar.min'] != spec.params[1]['scalar.max']
    assert spec.dual_weights['weights']['rvv_packed']
    assert spec.dual_weights['weights']['neon_tile'] == '4'
    assert spec.strides['input_stride'] == '3 * sizeof(void*)'
    ig = next(p for p in PLANS if p.name == 'f32-igemm-minmax')
    *_, spec, _ = fixture_for(ig)
    assert spec.strides['cn_stride'] == '8 * sizeof(float)'
