"""Regression coverage for Roman numeral headers and jumps across Flex modes."""

from pathlib import Path
import subprocess
import sys
import unittest

COMPILERS = [str(Path(p).resolve()) for p in sys.argv[1:3]]
del sys.argv[1:3]


def roman(value):
    result = ""
    for number, letters in [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
                            (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        count, value = divmod(value, number)
        result += letters * count
    return result


NUMERALS = [roman(n) for n in list(range(1, 41)) +
            [49, 50, 89, 90, 99, 100, 399, 400, 499, 500, 899, 900,
             999, 1000, 1999, 2999, 3999, 4000]]
PREAMBLE = "A Test of the Numbered Stage.\nHamlet, the director.\nRomeo, a friend.\n"


class Compiler(unittest.TestCase):
    def compile_play(self, compiler, source):
        # The upstream translator emits a Latin-1 copyright comment in its C.
        result = subprocess.run([compiler], input=source, encoding="latin-1",
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")  # Partial header matches cause warnings.
        self.assertIn("int main", result.stdout)
        return result.stdout

    def test_scene_headers_and_jumps(self):
        source = PREAMBLE + "Act I: A beginning.\n"
        for i, numeral in enumerate(NUMERALS):
            source += f"Scene {numeral}: A quiet place.\n"
            if i == 0:
                source += "[Enter Hamlet and Romeo]\n"
            following = NUMERALS[(i + 1) % len(NUMERALS)]
            source += f"Hamlet:\n Let us proceed to Scene {following}.\n"
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler):
                output = self.compile_play(compiler, source)
                for numeral in NUMERALS:
                    self.assertIn(f"act_i_scene_{numeral.lower()}:", output)
                    self.assertIn(f"goto act_i_scene_{numeral.lower()};", output)

    def test_act_headers_and_jumps(self):
        source = PREAMBLE
        for i, numeral in enumerate(NUMERALS):
            source += f"Act {numeral}: Another act.\nScene I: A quiet place.\n"
            if i == 0:
                source += "[Enter Hamlet and Romeo]\n"
            following = NUMERALS[(i + 1) % len(NUMERALS)]
            source += f"Hamlet:\n Let us proceed to Act {following}.\n"
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler):
                output = self.compile_play(compiler, source)
                for numeral in NUMERALS:
                    self.assertIn(f"act_{numeral.lower()}:", output)
                    self.assertIn(f"goto act_{numeral.lower()};", output)

    def test_mixed_case_and_whitespace(self):
        source = PREAMBLE + """
AcT i: A beginning.
ScEnE i: A quiet place.
[Enter Hamlet and Romeo]
Hamlet:
 Let us proceed to ScEnE\tIiI.
ScEnE\tIiI: A second place.
Hamlet:
 Let us return to AcT\tI.
"""
        for compiler in COMPILERS:
            with self.subTest(compiler=compiler):
                output = self.compile_play(compiler, source)
                self.assertIn("goto act_i_scene_iii;", output)
                self.assertIn("act_i_scene_iii:", output)
                self.assertIn("goto act_i;", output)

    def test_renderer_translation_is_identical_across_modes(self):
        source = Path("main.spl").read_text()
        outputs = [self.compile_play(compiler, source) for compiler in COMPILERS]
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
