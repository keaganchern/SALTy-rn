"""Tests of the differential harness's failure detection and reproducibility."""
import json
import copy
import random
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

from differential import (KERNEL_NAMES, SOURCES, Runner, case_output_size, compare,
                          incomplete_case, make_cases, original_source, validate_case)
import kernel_cases


class DifferentialHarnessTests(unittest.TestCase):
    def setUp(self):
        self.cases = [dict(kernel="f32-vadd", n=1), dict(kernel="f32-vadd", n=2)]
        self.output = bytes(range(12))

    def test_exact_match_and_corruption_location(self):
        self.assertIsNone(compare(self.cases, self.output, self.output))
        changed = self.output[:6] + b"\xff" + self.output[7:]
        index, reason = compare(self.cases, self.output, changed)
        self.assertEqual(index, 1)
        self.assertIn("output byte 2", reason)

    def test_missing_and_extra_output_are_failures(self):
        for a, b in [(b"", b""), (self.output, self.output[:-1]),
                     (self.output[:-1], self.output),
                     (self.output + b"x", self.output + b"x")]:
            with self.subTest(a=a, b=b):
                self.assertIsNotNone(compare(self.cases, a, b))

    def test_crash_prefix_identifies_incomplete_case(self):
        self.assertEqual(incomplete_case(self.cases, b""), 0)
        self.assertEqual(incomplete_case(self.cases, self.output[:4]), 1)

    def test_seed_and_replay_preserve_exact_inputs(self):
        cases = make_cases("qs8-vadd-minmax", 123, 2, "finite")
        self.assertEqual(cases, make_cases("qs8-vadd-minmax", 123, 2, "finite"))
        self.assertNotEqual(cases[-1]["input_hex"], make_cases("qs8-vadd-minmax", 124, 2, "finite")[-1]["input_hex"])
        for case in cases:
            self.assertEqual(validate_case(case), validate_case(json.loads(json.dumps(case))))
        invalid = dict(cases[0], input_hex=cases[0]["input_hex"][:-2])
        with self.assertRaises(ValueError):
            validate_case(invalid)

    def test_fp_grid_covers_nan_priority_and_invalid_product(self):
        cases = make_cases("intrinsic-vfmaq_f32", 1, 2, "ieee")
        operands = {tuple(lane[0] for lane in c["operands"]) for c in cases}
        for triple in [
            ("7fc12345", "7f800000", "00000000"),  # qNaN + infinity * 0
            ("7f812345", "7f800000", "00000000"),  # sNaN takes precedence
            ("00000000", "7fc12345", "ffc23456"),  # competing quiet payloads
            ("7fc12345", "ff823456", "7f812345"),  # signaling operand priority
        ]:
            self.assertIn(triple, operands)
        for case in cases:
            validate_case(case)
        reduction = make_cases("intrinsic-vaddvq_f32", 1, 0, "ieee")
        self.assertTrue(any(c["operands"][0] == ["7fc12345", "3f800000", "ff823456", "7fc12345"]
                            for c in reduction))

    def test_exit_status_and_timeout_are_not_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = Runner(Path(temp), 0.2)
            failed = runner.run([sys.executable, "-c", "raise SystemExit(3)"])
            self.assertEqual(failed.returncode, 3)
            timed_out = runner.run([sys.executable, "-c", "import time; time.sleep(5)"])
            self.assertEqual(timed_out.returncode, 124)
            with self.assertRaises(RuntimeError):
                runner.checked([sys.executable, "-c", "raise SystemExit(3)"])

    def test_every_repository_kernel_has_executable_cases(self):
        self.assertEqual(set(KERNEL_NAMES), {p.stem for p in SOURCES.glob("*.c")})
        self.assertEqual(len(KERNEL_NAMES), 40)
        for name in KERNEL_NAMES:
            with self.subTest(kernel=name):
                cases = make_cases(name, 123, 2, "finite")
                self.assertEqual(len(cases), 52)
                self.assertEqual(cases, make_cases(name, 123, 2, "finite"))
                self.assertNotEqual(cases[-1]["input_hex"], make_cases(name, 124, 2, "finite")[-1]["input_hex"])
                for case in cases:
                    self.assertGreater(case_output_size(case), 0)
                    self.assertEqual(validate_case(case), validate_case(json.loads(json.dumps(case))))

    def test_buffer_metadata_and_truncated_replays_are_rejected(self):
        case = make_cases("f32-argmaxpool", 1, 0, "finite")[0]
        for field in ["config", "buffers", "input_hex"]:
            invalid = copy.deepcopy(case)
            if field == "config": invalid[field][0] += 1
            elif field == "buffers": invalid[field][0]["size"] += 1
            else: invalid[field] = invalid[field][:-2]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_case(invalid)

    def test_multiple_outputs_and_stride_padding_are_compared(self):
        for name in ["f32-argmaxpool", "f32-raddstoreexpminusmax", "x32-transposec", "x32-packw-gemm-goi"]:
            case = make_cases(name, 1, 0, "finite")[3]
            size = case_output_size(case)
            expected = bytes(size)
            self.assertIsNone(compare([case], expected, expected))
            # Last byte includes the second result or strided/packed padding.
            changed = expected[:-1]+b"\xff"
            self.assertIsNotNone(compare([case], expected, changed))
            self.assertIsNotNone(compare([case], expected[:-1], expected[:-1]))
            self.assertEqual(incomplete_case([case, case], expected), 1)

    def test_original_body_is_preserved_with_or_without_parameters(self):
        for name in KERNEL_NAMES:
            path = SOURCES / (name+".c")
            original = path.read_text()
            body = original[original.index("void test_neon("):]
            self.assertTrue(original_source(path).endswith(body), name)

    def test_buffer_driver_serializes_outputs_and_checks_inputs_and_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "kernel.c").write_text("/* Driver test: no intrinsic substitutes. */\n")
            (directory / "adapter.h").write_text('''
static void invoke(uint32_t c[32], Buffer b[8]) {
  b[1].data[0] = 1; b[2].data[0] = 2;
  if (c[0] == 1) b[0].data[0] ^= 1;
  if (c[0] == 2) b[2].data[b[2].size] ^= 1;
}
''')
            driver = Path(__file__).parent / "differential/buffer_driver.c"
            exe = directory / "driver"
            subprocess.run(["cc", "-std=c11", "-I", str(directory), str(driver), "-o", str(exe)],
                           check=True, capture_output=True)
            for mode in range(3):
                b = kernel_cases.CaseBuilder("f32-argmaxpool", 1, 0, "zero", "finite", random.Random(1))
                b.c[0] = mode
                b.add("input", b"abc"); b.out("values", 3); b.out("indices", 2)
                result = subprocess.run([str(exe)], input=validate_case(b.finish()), capture_output=True)
                if mode == 0:
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b"\x01\xa5\xa5\x02\xa5")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"case 0:", result.stderr)
                    self.assertIn(b"input buffer modified" if mode == 1 else b"buffer guard modified", result.stderr)


if __name__ == "__main__":
    unittest.main()
