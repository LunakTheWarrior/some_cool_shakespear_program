"""Check SPL pyramid geometry, motion, and the real terminal presentation."""

import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest

PLAY, LAUNCHER = [os.path.abspath(p) for p in sys.argv[1:3]]
del sys.argv[1:3]
WIDTH, HEIGHT = 65, 23
FRAME_BYTES = (WIDTH + 1) * HEIGHT
PALETTE = set(" .:-=+*#@\n")
ENTER = b"\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H"
LEAVE = b"\x1b[?25h\x1b[?1049l"


def native_frames(count, start=0):
    result = subprocess.run([PLAY], input=f"{count}\n{start}\n", text=True,
                            capture_output=True, timeout=10)
    if result.returncode or result.stderr:
        raise AssertionError(f"SPL exit={result.returncode}, stderr={result.stderr!r}")
    packets = result.stdout.split("\f")
    if packets[-1] != "":
        raise AssertionError("missing final frame delimiter")
    return packets[:-1]


def bounds(frame):
    points = [(x, y) for y, row in enumerate(frame.splitlines())
              for x, char in enumerate(row) if char != " "]
    return (min(x for x, y in points), max(x for x, y in points),
            min(y for x, y in points), max(y for x, y in points))


def pose(phase):
    # Match the documented fixed-point rotation, not the clipping implementation.
    cosine, sine = 10000, 0
    for _ in range(phase % 64):
        cosine, sine = (int((9952*cosine - 980*sine)/10000),
                        int((9952*sine + 980*cosine)/10000))
    offset_x = int(24*sine/10000) / 4
    offset_y = int(8*int((cosine*cosine-sine*sine)/10000)/10000) / 4
    return cosine/10000, sine/10000, offset_x, offset_y


def reference_intersection(x, y, phase):
    """Floating-point convex-solid reference in physical world coordinates."""
    cosine, sine, offset_x, offset_y = pose(phase)
    x, y = x-offset_x, y-offset_y
    origin = (cosine*x - sine*0.6*y, 0.8*y, sine*x + cosine*0.6*y)
    direction = (-0.8*sine, -0.6, 0.8*cosine)
    entry, exit = 24.0, -24.0
    for normal in [(2, -1, 0), (-2, -1, 0), (0, -1, 2), (0, -1, -2), (0, 1, 0)]:
        slope = sum(n*d for n, d in zip(normal, direction))
        remaining = 12-sum(n*p for n, p in zip(normal, origin))
        if abs(slope) < 1e-10:
            if remaining < 0:
                return False, float("inf")
        elif slope > 0:
            entry = min(entry, remaining/slope)
        else:
            exit = max(exit, remaining/slope)
    return exit <= entry+1e-10, abs(entry-exit)


class Pyramid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = native_frames(65)

    def test_complete_frames_and_palette(self):
        self.assertEqual(len(self.frames), 65)
        for frame in self.frames:
            self.assertEqual(len(frame), FRAME_BYTES)
            self.assertEqual(len(frame.splitlines()), HEIGHT)
            self.assertEqual({len(row) for row in frame.splitlines()}, {WIDTH})
            self.assertLessEqual(set(frame), PALETTE)
            self.assertGreaterEqual(len(set(frame)-{" ", "\n"}), 2)

    def test_silhouette_against_independent_3d_geometry(self):
        for phase in [0, 7, 16, 33, 48]:
            for row, line in enumerate(self.frames[phase].splitlines()):
                for col, pixel in enumerate(line):
                    expected, gap = reference_intersection(col-32, 2*(row-11), phase)
                    # SPL clips depths to 1/64 of a world unit. Permit only
                    # grazing intersections within that rounding tolerance.
                    if (pixel != " ") != expected:
                        self.assertLessEqual(gap, 1/32, (phase, col, row, gap))

    def test_rotation_changes_the_projected_width(self):
        straight, diagonal = bounds(self.frames[0]), bounds(self.frames[8])
        self.assertGreater(diagonal[1]-diagonal[0], straight[1]-straight[0]+5)

    def test_pyramid_sways_horizontally_and_bobs(self):
        right, left = bounds(self.frames[16]), bounds(self.frames[48])
        self.assertGreater((right[0]+right[1]-left[0]-left[1])/2, 8)
        self.assertNotEqual(bounds(self.frames[0])[2], right[2])

    def test_complete_rotation_repeats_without_drift(self):
        self.assertEqual(self.frames[0], self.frames[64])
        self.assertGreater(len(set(self.frames[:64])), 50)

    def test_pyramid_stays_inside_the_view(self):
        for frame in self.frames:
            left, right, top, bottom = bounds(frame)
            self.assertGreater(left, 0)
            self.assertLess(right, WIDTH-1)
            self.assertGreater(top, 0)
            self.assertLess(bottom, HEIGHT-1)

    def test_start_frame_and_frame_limit(self):
        self.assertEqual(native_frames(3, 8), self.frames[8:11])


class Launcher(unittest.TestCase):
    def run_plain(self, *args):
        result = subprocess.run([LAUNCHER, *args], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_redirected_output_defaults_to_one_plain_frame(self):
        self.assertEqual(self.run_plain(), native_frames(1)[0])

    def test_plain_frames_preserve_the_spl_output(self):
        self.assertEqual(self.run_plain("--plain", "--frames", "3", "--start-frame", "8"),
                         "".join(native_frames(3, 8)))

    def test_start_frame_wraps_at_one_rotation(self):
        self.assertEqual(self.run_plain("--start-frame", "64"), native_frames(1)[0])

    def test_invalid_options_fail_before_rendering(self):
        for args in [("--frames", "0"), ("--start-frame", "-1"),
                     ("--fps", "0"), ("--fps", "nan")]:
            with self.subTest(args=args):
                result = subprocess.run([LAUNCHER, *args], capture_output=True,
                                        text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def terminal_run(self, args=(), stop_signal=None):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        process = subprocess.Popen([LAUNCHER, *args], stdin=subprocess.DEVNULL,
                                   stdout=slave, stderr=subprocess.PIPE)
        os.close(slave)
        output = bytearray()
        started = time.monotonic()
        deadline = started + 10
        interrupted = False
        try:
            while time.monotonic() < deadline:
                if stop_signal and not interrupted and len(output) > FRAME_BYTES:
                    process.send_signal(stop_signal)
                    interrupted = True
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        data = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            break
                        raise
                    if not data:
                        break
                    output.extend(data)
            self.assertEqual(process.wait(timeout=2), 0)
            self.assertEqual(process.stderr.read(), b"")
            if stop_signal:
                self.assertTrue(interrupted)
            return bytes(output), time.monotonic()-started
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stderr.close()
            os.close(master)

    def test_real_terminal_frames_are_paced_and_restore_the_screen(self):
        output, elapsed = self.terminal_run(("--frames", "3", "--fps", "20"))
        self.assertTrue(output.startswith(ENTER))
        self.assertTrue(output.endswith(LEAVE))
        self.assertEqual(output.count(b"\x1b[H"), 4)
        self.assertGreaterEqual(elapsed, 0.09)

    def test_ctrl_c_restores_the_terminal(self):
        output, _ = self.terminal_run(stop_signal=signal.SIGINT)
        self.assertTrue(output.startswith(ENTER))
        self.assertTrue(output.endswith(LEAVE))

    def test_sigterm_restores_the_terminal(self):
        output, _ = self.terminal_run(stop_signal=signal.SIGTERM)
        self.assertTrue(output.endswith(LEAVE))


if __name__ == "__main__":
    unittest.main()
