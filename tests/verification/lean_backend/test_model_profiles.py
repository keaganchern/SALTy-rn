from __future__ import annotations

import pytest

from workflow.verification.lean_backend.model_profiles import PrefixTailProfile


def test_prefix_tail_rejects_non_power_of_two_load_width() -> None:
    with pytest.raises(ValueError, match="power-of-two load"):
        PrefixTailProfile(
            element_c_type="int8_t",
            load_lanes=7,
            store_widths=(4, 2),
        )


def test_prefix_tail_rejects_unimplemented_power_of_two_shape() -> None:
    with pytest.raises(ValueError, match="supports exactly"):
        PrefixTailProfile(
            element_c_type="int8_t",
            load_lanes=16,
            store_widths=(8, 4, 2, 1),
        )
