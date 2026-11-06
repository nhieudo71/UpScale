import unittest
from pathlib import Path

from upscale.domain.models import ErrorCode, UpscaleError, UpscaleRequest
from upscale.domain.rules import (
    check_output_limit,
    classify_engine_failure,
    output_candidates,
    output_size,
    parse_progress,
)


class ParseProgressTests(unittest.TestCase):
    def test_comma_and_dot(self) -> None:
        self.assertEqual(parse_progress("25,00%"), 25.0)
        self.assertEqual(parse_progress("25.50%"), 25.5)

    def test_integer_and_spaces(self) -> None:
        self.assertEqual(parse_progress("  100 %"), 100.0)

    def test_non_progress_lines(self) -> None:
        self.assertIsNone(parse_progress("[0 NVIDIA GeForce RTX 3050] queueC=2"))
        self.assertIsNone(parse_progress(""))

    def test_clamped(self) -> None:
        self.assertEqual(parse_progress("150%"), 100.0)


class OutputLimitTests(unittest.TestCase):
    def test_size(self) -> None:
        self.assertEqual(output_size(220, 220, 4), (880, 880))

    def test_zero_means_unlimited(self) -> None:
        check_output_limit(100000, 100000, 4, 0)

    def test_over_limit(self) -> None:
        with self.assertRaises(UpscaleError) as ctx:
            check_output_limit(1000, 1000, 4, 10_000_000)
        self.assertEqual(ctx.exception.code, ErrorCode.OUTPUT_TOO_LARGE)
        self.assertIn("4000 x 4000", ctx.exception.message)

    def test_at_limit_is_allowed(self) -> None:
        check_output_limit(1000, 1000, 4, 16_000_000)


class ClassifyTests(unittest.TestCase):
    def test_oom(self) -> None:
        self.assertEqual(classify_engine_failure("vkAllocateMemory failed -2"), ErrorCode.OUT_OF_VRAM)

    def test_other(self) -> None:
        self.assertEqual(classify_engine_failure("boom"), ErrorCode.ENGINE_FAILED)
        self.assertEqual(classify_engine_failure(""), ErrorCode.ENGINE_FAILED)


class OutputNameTests(unittest.TestCase):
    def test_sequence(self) -> None:
        gen = output_candidates(Path("D:/Anh/cat.jpg"), 4)
        self.assertEqual([next(gen).name for _ in range(3)], ["cat_x4.png", "cat_x4_2.png", "cat_x4_3.png"])

    def test_same_folder(self) -> None:
        self.assertEqual(next(output_candidates(Path("D:/Anh/cat.jpg"), 2)).parent, Path("D:/Anh"))


class RequestValidationTests(unittest.TestCase):
    def test_bad_scale(self) -> None:
        with self.assertRaises(ValueError):
            UpscaleRequest("a.png", scale=3)

    def test_bad_model(self) -> None:
        with self.assertRaises(ValueError):
            UpscaleRequest("a.png", model="x")

    def test_bad_gpu(self) -> None:
        with self.assertRaises(ValueError):
            UpscaleRequest("a.png", gpu_id=-1)


if __name__ == "__main__":
    unittest.main()
