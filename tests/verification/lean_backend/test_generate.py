from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workflow.verification.lean_backend.emit_lean import LeanEmissionError
from workflow.verification.lean_backend.generate import _main


ROOT = Path(__file__).resolve().parents[3]
NEON = ROOT / "kernels/source/qs8-vadd-minmax.c"


def test_emission_failure_does_not_partially_replace_outputs() -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "input_a += 8;",
        "input_a += 7;",
        1,
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
        directory = Path(temporary)
        source = directory / "bad-pointer-update.c"
        source.write_text(mutated, encoding="utf-8")
        manifest = directory / "manifest.json"
        models = directory / "Models.lean"
        manifest.write_text("old manifest", encoding="ascii")
        models.write_text("old models", encoding="ascii")

        with pytest.raises(LeanEmissionError, match="pointer/count updates"):
            _main(
                [
                    "--repository-root",
                    str(ROOT),
                    "--source",
                    str(source),
                    "--output",
                    str(manifest),
                    "--lean-out",
                    str(models),
                ]
            )

        assert manifest.read_text(encoding="ascii") == "old manifest"
        assert models.read_text(encoding="ascii") == "old models"
