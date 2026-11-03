"""Exercise native executables compiled from real Shakespeare source."""

from pathlib import Path
import subprocess
import sys
import unittest

RENDERER, ARITHMETIC, CONTROL_FLOW = (str(Path(p).resolve()) for p in sys.argv[1:4])
del sys.argv[1:4]
GOLDEN = Path(__file__).resolve().parent / "golden"
PALETTE = set(" .:-=+*#@\n")


def run(program, input_text=""):
    result = subprocess.run(
        [program], input=input_text, capture_output=True, text=True, timeout=10,
    )
    if result.returncode or result.stderr:
        raise AssertionError(
            f"{program}: exit {result.returncode}; stderr={result.stderr!r}"
        )
    return result.stdout


class ShakespeareSemantics(unittest.TestCase):
    def test_integer_arithmetic_in_spl(self):
        # Square, floor sqrt, C-style signed division, product, remainder.
        self.assertEqual(run(ARITHMETIC), "9 3 -3 4 2\n")

    def test_stack_and_conditional_loop_in_spl(self):
        self.assertEqual(run(CONTROL_FLOW), "321123\n")


class Renderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = {shape: run(RENDERER, key) for shape, key in
                      [("sphere", "s"), ("torus", "t"), ("cube", "c")]}

    def test_dimensions_and_ascii_palette(self):
        for shape, frame in self.frames.items():
            with self.subTest(shape=shape):
                self.assertTrue(frame.endswith("\n"))
                self.assertEqual(len(frame.splitlines()), 25)
                self.assertEqual({len(row) for row in frame.splitlines()}, {49})
                self.assertLessEqual(set(frame), PALETTE)

    def test_reviewed_golden_frames(self):
        for shape, frame in self.frames.items():
            with self.subTest(shape=shape):
                self.assertEqual(frame, (GOLDEN / f"{shape}.txt").read_text())

    def test_sphere_silhouette_matches_analytic_projection(self):
        for row, line in enumerate(self.frames["sphere"].splitlines()):
            y = 2 * (row - 12)
            for col, pixel in enumerate(line):
                x = col - 24
                self.assertEqual(pixel != " ", x*x + y*y <= 18*18,
                                 f"sphere at ({x}, {y})")

    def test_sphere_has_directional_shading(self):
        rows = self.frames["sphere"].splitlines()
        palette = " .:-=+*#@"
        self.assertGreater(palette.index(rows[9][18]), palette.index(rows[15][30]))
        self.assertGreaterEqual(len(set(self.frames["sphere"]) - {" ", "\n"}), 6)

    def test_torus_has_a_hole_and_two_visible_sides(self):
        center = self.frames["torus"].splitlines()[12]
        self.assertEqual(center[24], " ")
        self.assertNotEqual(center[12], " ")
        self.assertNotEqual(center[36], " ")
        self.assertGreaterEqual(len(set(self.frames["torus"]) - {" ", "\n"}), 5)

    def test_cube_has_three_shaded_faces(self):
        self.assertEqual(set(self.frames["cube"]) - {" ", "\n"}, {"=", "+", "@"})
        self.assertNotEqual(self.frames["cube"].splitlines()[12][24], " ")

    def test_shapes_are_distinct(self):
        self.assertEqual(len(set(self.frames.values())), 3)

    def test_eof_defaults_to_sphere(self):
        self.assertEqual(run(RENDERER), self.frames["sphere"])

    def test_unknown_input_defaults_to_sphere(self):
        self.assertEqual(run(RENDERER, "?"), self.frames["sphere"])

    def test_only_first_input_character_selects_shape(self):
        self.assertEqual(run(RENDERER, "torus\n"), self.frames["torus"])


if __name__ == "__main__":
    unittest.main()
