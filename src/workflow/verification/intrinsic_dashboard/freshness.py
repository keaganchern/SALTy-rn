"""Deterministic generated-model freshness checks for dashboard claim gates."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..lean_backend.binding import registry_content_digest
from ..lean_backend.case_emit import emit_case_pair
from ..lean_backend.emit_lean import emit_qs8_vadd_minmax_pair
from ..lean_backend.frontend import (
    ClangError,
    FrontendError,
    UnsupportedConstructError,
    parse_kernel,
)
from ..lean_backend.generate import _extract_pair
from ..lean_backend.generate_cases import (
    generate_case_obligations,
    generate_case_modules,
    generated_module_path,
    generated_obligation_path,
)
from ..lean_backend.model_profiles import SCALE_UP_MODELS
from ..lean_backend.profiles import FRONTEND_PROFILES
from ..lean_backend.scaleup_catalog import SCALEUP_CATALOGS


GENERATED_CASES = (
    "qs8-vadd-minmax",
    "s8-vclamp",
    "qs8-vcvt",
    "qs8-vlrelu",
    "qu8-vadd-minmax",
)


@dataclass(frozen=True, slots=True)
class _SemanticMutation:
    case_id: str
    anchor: str
    replacement: str


_SEMANTIC_MUTATIONS = (
    _SemanticMutation(
        case_id="qs8-vadd-minmax",
        anchor=(
            "    vout0123456789ABCDEF = "
            "vmaxq_s8(vout0123456789ABCDEF, voutput_min);\n\n"
            "    vout0123456789ABCDEF = "
            "vminq_s8(vout0123456789ABCDEF, voutput_max);"
        ),
        replacement=(
            "    vout0123456789ABCDEF = "
            "vminq_s8(vout0123456789ABCDEF, voutput_min);\n\n"
            "    vout0123456789ABCDEF = "
            "vminq_s8(vout0123456789ABCDEF, voutput_max);"
        ),
    ),
    _SemanticMutation(
        case_id="s8-vclamp",
        anchor=(
            "    vacc0 = vmaxq_s8(vacc0, voutput_min);\n"
            "    vacc1 = vmaxq_s8(vacc1, voutput_min);\n"
            "    vacc2 = vmaxq_s8(vacc2, voutput_min);\n"
            "    vacc3 = vmaxq_s8(vacc3, voutput_min);"
        ),
        replacement=(
            "    vacc0 = vminq_s8(vacc0, voutput_min);\n"
            "    vacc1 = vmaxq_s8(vacc1, voutput_min);\n"
            "    vacc2 = vmaxq_s8(vacc2, voutput_min);\n"
            "    vacc3 = vmaxq_s8(vacc3, voutput_min);"
        ),
    ),
    _SemanticMutation(
        case_id="qs8-vcvt",
        anchor=(
            "  const int16x8_t vmultiplier = "
            "vdupq_n_s16(-params->scalar.multiplier);"
        ),
        replacement=(
            "  const int16x8_t vmultiplier = " "vdupq_n_s16(params->scalar.multiplier);"
        ),
    ),
    _SemanticMutation(
        case_id="qs8-vlrelu",
        anchor=(
            "    const int16x8_t vmultiplier = "
            "vbslq_s16(vmask, vpositive_multiplier, vnegative_multiplier);\n"
            "    vacc = vqrdmulhq_s16(vacc, vmultiplier);\n"
            "    vacc = vqaddq_s16(vacc, voutput_zero_point);\n"
            "    const int8x8_t vy = vqmovn_s16(vacc);"
        ),
        replacement=(
            "    const int16x8_t vmultiplier = "
            "vbslq_s16(vmask, vnegative_multiplier, vpositive_multiplier);\n"
            "    vacc = vqrdmulhq_s16(vacc, vmultiplier);\n"
            "    vacc = vqaddq_s16(vacc, voutput_zero_point);\n"
            "    const int8x8_t vy = vqmovn_s16(vacc);"
        ),
    ),
    _SemanticMutation(
        case_id="qu8-vadd-minmax",
        anchor=(
            "    vout01234567 = vmax_u8(vout01234567, voutput_min);\n\n"
            "    vout01234567 = vmin_u8(vout01234567, voutput_max);"
        ),
        replacement=(
            "    vout01234567 = vmin_u8(vout01234567, voutput_min);\n\n"
            "    vout01234567 = vmin_u8(vout01234567, voutput_max);"
        ),
    ),
)


def _generated_model_path(repository_root: Path, case_id: str) -> Path:
    if case_id == "qs8-vadd-minmax":
        return (
            repository_root
            / "src/verification_bw/lean/SALT/Generated/QS8VAddMinmax/Models.lean"
        )
    return generated_module_path(repository_root, case_id)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resource_directory_identity(resource_directory: Path) -> str:
    """Hash the resolved Clang resource path and its complete file tree."""

    root = resource_directory.resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError(f"Clang resource directory is not a directory: {root}")

    digest = hashlib.sha256()
    encoded_root = str(root).encode("utf-8")
    digest.update(len(encoded_root).to_bytes(8, "big"))
    digest.update(encoded_root)
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        if path.is_symlink():
            target = path.readlink().as_posix().encode("utf-8")
            resolved_target = path.resolve(strict=True)
            try:
                resolved_target.relative_to(root)
            except ValueError as error:
                raise RuntimeError(
                    f"Clang resource symlink escapes its root: {path}"
                ) from error
            digest.update(b"L")
            digest.update(len(target).to_bytes(8, "big"))
            digest.update(target)
        elif path.is_dir():
            digest.update(b"D")
        elif path.is_file():
            digest.update(b"F")
            content_sha256 = _sha256_file(path).encode("ascii")
            digest.update(content_sha256)
        else:
            raise RuntimeError(f"unsupported Clang resource entry: {path}")
    return digest.hexdigest()


def _clang_producer_identity(clang: str) -> bytes:
    executable_name = shutil.which(clang)
    if executable_name is None:
        raise RuntimeError(f"cannot resolve Clang producer: {clang}")
    executable = Path(executable_name).resolve(strict=True)
    if not executable.is_file():
        raise RuntimeError(f"Clang producer is not a file: {executable}")

    version = subprocess.run(
        (str(executable), "--version"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if version.returncode != 0 or not version.stdout:
        raise RuntimeError(f"cannot read Clang version: {executable}")
    resource = subprocess.run(
        (str(executable), "--print-resource-dir"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if resource.returncode != 0:
        raise RuntimeError(f"cannot read Clang resource directory: {executable}")
    resource_lines = resource.stdout.decode("utf-8").splitlines()
    if len(resource_lines) != 1 or not resource_lines[0].strip():
        raise RuntimeError(f"malformed Clang resource directory: {executable}")
    resource_directory = Path(resource_lines[0].strip())
    resource_identity = _resource_directory_identity(resource_directory)

    fields = (
        ("resolved-executable", str(executable).encode("utf-8")),
        ("binary-sha256", _sha256_file(executable).encode("ascii")),
        ("version-output", version.stdout),
        ("resource-directory-sha256", resource_identity.encode("ascii")),
    )
    identity = bytearray()
    for name, value in fields:
        encoded_name = name.encode("ascii")
        identity.extend(len(encoded_name).to_bytes(8, "big"))
        identity.extend(encoded_name)
        identity.extend(len(value).to_bytes(8, "big"))
        identity.extend(value)
    return bytes(identity)


def clang_producer_digest(clang: str = "clang") -> str:
    """Return a content identity for the resolved Clang and resource headers."""

    return hashlib.sha256(_clang_producer_identity(clang)).hexdigest()


def generation_watch_digest(repository_root: Path, *, clang: str = "clang") -> str:
    """Hash every watched generator input/output and the Clang producer identity."""

    root = repository_root.resolve()
    backend = root / "src/workflow/verification/lean_backend"
    paths = {path for path in backend.rglob("*.py") if path.is_file()}
    paths.update(path for path in (backend / "facade").rglob("*.h") if path.is_file())
    paths.add(Path(__file__).resolve())
    for case_id in GENERATED_CASES:
        paths.add(root / "kernels/source" / f"{case_id}.c")
        paths.add(root / "kernels/target" / f"{case_id}.c")
        paths.add(_generated_model_path(root, case_id))
        if (
            case_id in SCALE_UP_MODELS
            and SCALE_UP_MODELS[case_id].unary_prefix_tail_obligation is not None
        ):
            paths.add(generated_obligation_path(root, case_id))
    missing = sorted(path for path in paths if not path.is_file())
    if missing:
        raise FileNotFoundError(f"generated-model input is missing: {missing}")

    digest = hashlib.sha256()
    producer = _clang_producer_identity(clang)
    digest.update(len(producer).to_bytes(8, "big"))
    digest.update(producer)
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _generated_semantics(module_text: str) -> str:
    """Remove source/provenance hashes before comparing generated semantics."""

    lines = module_text.splitlines(keepends=True)
    semantic_lines: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("def ") and "Sha256 : String :=" in line:
            if index + 1 >= len(lines):
                raise ValueError("truncated generated SHA-256 definition")
            literal = lines[index + 1].strip()
            if (
                len(literal) != 66
                or not literal.startswith('"')
                or not literal.endswith('"')
                or any(
                    character not in "0123456789abcdef" for character in literal[1:-1]
                )
            ):
                raise ValueError("malformed generated SHA-256 definition")
            index += 2
            continue
        semantic_lines.append(line)
        index += 1
    return "".join(semantic_lines)


def _emit_model_with_neon_source(
    repository_root: Path,
    case_id: str,
    neon_source: Path,
    *,
    clang: str,
) -> str:
    if case_id == "qs8-vadd-minmax":
        _, neon, rvv = _extract_pair(
            repository_root=repository_root,
            source=neon_source,
            clang=clang,
        )
        return emit_qs8_vadd_minmax_pair(neon, rvv).module_text

    frontend_profile = FRONTEND_PROFILES[case_id]
    catalog = SCALEUP_CATALOGS[case_id]
    neon = parse_kernel(neon_source, clang=clang, profile=frontend_profile.neon)
    rvv = parse_kernel(
        repository_root / "kernels" / "target" / f"{case_id}.c",
        clang=clang,
        profile=frontend_profile.rvv,
    )
    emission = emit_case_pair(
        neon,
        rvv,
        profile=SCALE_UP_MODELS[case_id],
        neon_registry=catalog.registry,
        rvv_registry=catalog.registry,
        registry_sha256=registry_content_digest(
            f"{case_id}-intrinsics", catalog.registry
        ),
    )
    return emission.emitted.module_text


def check_semantic_mutation_sensitivity(
    repository_root: Path, *, clang: str = "clang"
) -> Mapping[str, bool]:
    """Check that one exact semantic mutation is observable for every case.

    Each mutation changes only the Neon side.  It passes only when the restricted
    frontend explicitly rejects the changed syntax or the generated semantic Lean
    (with provenance hashes removed) differs from the unmutated model.
    """

    root = repository_root.resolve()
    result = {case_id: False for case_id in GENERATED_CASES}
    mutations = {mutation.case_id: mutation for mutation in _SEMANTIC_MUTATIONS}
    if tuple(mutations) != GENERATED_CASES:
        return result

    for case_id in GENERATED_CASES:
        mutation = mutations[case_id]
        source_path = root / "kernels" / "source" / f"{case_id}.c"
        try:
            original = _emit_model_with_neon_source(
                root, case_id, source_path, clang=clang
            )
            source = source_path.read_text(encoding="ascii")
            if source.count(mutation.anchor) != 1:
                continue
            changed_source = source.replace(mutation.anchor, mutation.replacement, 1)
            with tempfile.TemporaryDirectory(
                prefix=f"saltyrn-{case_id}-mutation-"
            ) as temporary_directory:
                mutated_path = Path(temporary_directory) / source_path.name
                mutated_path.write_text(changed_source, encoding="ascii")
                try:
                    changed = _emit_model_with_neon_source(
                        root, case_id, mutated_path, clang=clang
                    )
                except UnsupportedConstructError:
                    result[case_id] = True
                    continue
                except ClangError:
                    continue
                except FrontendError:
                    result[case_id] = True
                    continue
            result[case_id] = _generated_semantics(changed) != _generated_semantics(
                original
            )
        except (OSError, UnicodeError, RuntimeError, ValueError):
            result[case_id] = False
    return result


def check_generated_models(
    repository_root: Path, *, clang: str = "clang"
) -> Mapping[str, bool]:
    """Regenerate in memory and compare each checked-in model byte-for-byte."""

    root = repository_root.resolve()
    result = {case_id: False for case_id in GENERATED_CASES}

    try:
        _, neon, rvv = _extract_pair(repository_root=root, clang=clang)
        expected = emit_qs8_vadd_minmax_pair(neon, rvv).module_text
        path = _generated_model_path(root, "qs8-vadd-minmax")
        result["qs8-vadd-minmax"] = (
            path.is_file() and path.read_text(encoding="ascii") == expected
        )
    except (OSError, UnicodeError, RuntimeError, ValueError):
        result["qs8-vadd-minmax"] = False

    for case_id in GENERATED_CASES[1:]:
        try:
            expected = generate_case_modules(
                repository_root=root, cases=(case_id,), clang=clang
            )[case_id]
            path = _generated_model_path(root, case_id)
            model_current = (
                path.is_file() and path.read_text(encoding="ascii") == expected
            )
            obligations = generate_case_obligations(cases=(case_id,))
            obligation_current = True
            for obligation_case, obligation_text in obligations.items():
                obligation_path = generated_obligation_path(root, obligation_case)
                obligation_current = obligation_current and (
                    obligation_path.is_file()
                    and obligation_path.read_text(encoding="ascii")
                    == obligation_text
                )
            result[case_id] = model_current and obligation_current
        except (OSError, UnicodeError, RuntimeError, ValueError):
            result[case_id] = False
    return result
