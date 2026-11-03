"""Pace and present frames produced by SPL; all geometry stays in main.spl."""

import argparse
import math
import shutil
import signal
import subprocess
import sys
import time

WIDTH, HEIGHT = 65, 23
FRAME_BYTES = (WIDTH + 1) * HEIGHT
ENTER_SCREEN = "\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H"
LEAVE_SCREEN = "\x1b[?25h\x1b[?1049l"


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def frame_rate(value):
    number = float(value)
    if not math.isfinite(number) or not 1 <= number <= 60:
        raise argparse.ArgumentTypeError("must be between 1 and 60")
    return number


def interrupt(_signum, _frame):
    raise KeyboardInterrupt


def animate(program, args):
    terminal = sys.stdout.isatty() and not args.plain
    count = args.frames if args.frames is not None else (0 if terminal else 1)
    if terminal:
        columns, rows = shutil.get_terminal_size()
        if columns < WIDTH or rows < HEIGHT + 1:
            raise ValueError(f"animation needs a terminal at least {WIDTH}x{HEIGHT + 1}")

    child = None
    entered_screen = False
    try:
        child = subprocess.Popen([program], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        child.stdin.write(f"{count}\n{args.start_frame % 64}\n".encode("ascii"))
        child.stdin.close()
        if terminal:
            # Mark this first so interruption during setup still restores the screen.
            entered_screen = True
            sys.stdout.write(ENTER_SCREEN)
            sys.stdout.flush()

        shown = 0
        next_tick = time.monotonic()
        while not count or shown < count:
            packet = child.stdout.read(FRAME_BYTES + 1)
            if len(packet) != FRAME_BYTES + 1 or packet[-1:] != b"\f":
                raise RuntimeError("the SPL renderer ended without a complete frame")
            frame = packet[:-1].decode("ascii")
            if terminal:
                # Cursor positioning overwrites the previous frame without scrolling.
                sys.stdout.write("\x1b[H" + frame)
            else:
                sys.stdout.write(frame)
            sys.stdout.flush()
            shown += 1
            if terminal and (not count or shown < count):
                next_tick = max(next_tick + 1 / args.fps, time.monotonic())
                time.sleep(max(0, next_tick - time.monotonic()))

        if child.wait(timeout=5):
            raise RuntimeError("the SPL renderer failed")
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if child.stdout is not None:
                child.stdout.close()
        if entered_screen:
            sys.stdout.write(LEAVE_SCREEN)
            sys.stdout.flush()


def main():
    program = sys.argv[1]
    parser = argparse.ArgumentParser(
        description="A moving, rotating pyramid rendered in Shakespeare. Ctrl+C stops it."
    )
    parser.add_argument("--frames", type=positive_int,
                        help="stop after this many frames (default: continuous on a terminal)")
    parser.add_argument("--fps", type=frame_rate, default=15,
                        help="terminal frame rate, 1–60 (default: 15)")
    parser.add_argument("--start-frame", type=nonnegative_int, default=0,
                        help="start at this step of the 64-frame rotation cycle")
    parser.add_argument("--plain", action="store_true",
                        help="print plain frames without animation controls or delays")
    args = parser.parse_args(sys.argv[2:])
    signal.signal(signal.SIGTERM, interrupt)
    try:
        animate(program, args)
    except KeyboardInterrupt:
        return 0
    except BrokenPipeError:
        # A consumer such as head may close the pipe before the animation ends.
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ascii3d: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
