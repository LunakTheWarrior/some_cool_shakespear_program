# I Only Danced This Pyramid Because You Asked Me To

An animated 3D ASCII pyramid written in the **Shakespeare Programming Language
(SPL)**, starring a Norwegian cast with prickly compliments and reluctant affection.

[`main.spl`](main.spl) computes the rotation, movement, ray intersections, face
lighting, and every frame's characters. A small [Python launcher](tools/animate.py)
paces the frames and manages the terminal screen and cursor. The original
SPL compiler translates the play into C and links it to its runtime.

## Build and run

On Linux, install Bazel 8.1.1 (or Bazelisk), a C compiler, Bison, Flex and its
development library, and Python 3. On Debian/Ubuntu the non-Bazel dependencies
are available with:

```sh
sudo apt-get install build-essential bison flex libfl-dev python3
```

On Fedora:

```sh
sudo dnf install gcc gcc-c++ bison flex libfl-devel python3
```

The project `.bazelrc` selects `/usr/bin/gcc` directly, bypassing compiler
wrappers in `PATH` and an inherited `CC`. It also sets `CCACHE_DISABLE=1` for
toolchain configuration and build actions, so ccache wrappers do not try to
write their cache inside Bazel's sandbox. Bazel provides its own build cache.
These defaults apply to `bazel build`, `bazel run`, and `bazel test`.

To select another compiler explicitly, override the project default:

```sh
bazel build //:ascii3d --repo_env=CC=/usr/bin/clang
```

Run the animated pyramid directly, with no input prompt:

```sh
bazelisk run //:ascii3d
```

It rotates, sways left and right, and bobs up and down at a target of 15 frames
per second. Press **Ctrl+C** to stop. The launcher restores the cursor and the
previous terminal screen on exit. Use an ANSI terminal at least **65 columns
by 24 rows**. The pyramid frame itself is 65 by 23 characters.

You can adjust the pace or run a finite animation:

```sh
bazelisk run //:ascii3d -- --fps 25
bazelisk run //:ascii3d -- --frames 128
```

Redirecting output produces one plain frame by default. Explicit `--frames`
prints that many frames consecutively. Plain output has no terminal escapes
or timing delays:

```sh
bazelisk run //:ascii3d -- --plain --start-frame 8
bazelisk run //:ascii3d -- --plain --frames 3 > pyramid.txt
```

The earlier static sphere, torus, and cube remain available in
[`gallery.spl`](gallery.spl):

```sh
printf 's' | bazelisk run //:gallery
printf 't' | bazelisk run //:gallery
printf 'c' | bazelisk run //:gallery
```

The first Bazel build downloads the pinned rules_cc and rules_shell modules;
the SPL compiler source is already vendored. Flex and Bison are host tools
invoked by build actions, so the build is intended for a local Linux machine
with those dependencies installed.

## Tests

```sh
bazel test //... --test_output=errors
```

To additionally check host compiler-wrapper compatibility in an isolated build:

```sh
bash tests/check_ccache_build.sh
```

This regression check simulates a broken compiler wrapper in both `CC` and
`PATH`, then an explicitly selected wrapper that requires `CCACHE_DISABLE=1`.
Both builds run the full suite. It uses the installed Bazel and system GCC;
ccache itself is not required for this simulation.

The suite includes 30 checks:

- [`tests/test_animation.py`](tests/test_animation.py) exercises 65 frames from
  the SPL pyramid, checks silhouettes against an independent floating-point 3D
  reference, verifies rotation and movement, frame limits, repeatability, frame
  dimensions, and keeping the solid inside the view. It also checks the launcher
  using real pseudoterminals: frame timing, alternate-screen handling, and cleanup
  after Ctrl+C and SIGTERM.
- [`tests/arithmetic.spl`](tests/arithmetic.spl) and
  [`tests/control_flow.spl`](tests/control_flow.spl) exercise SPL integer arithmetic,
  stacks, and conditional scene jumps.
- [`tests/test_renderer.py`](tests/test_renderer.py) preserves the original
  gallery checks, including analytic sphere geometry, shading, the torus hole,
  the cube's faces, and reviewed snapshots in [`tests/golden`](tests/golden).
- [`tests/test_compiler.py`](tests/test_compiler.py) checks Roman-numeral headers
  and jumps, mixed case and whitespace, and identical translation of the pyramid
  using scanners generated in Flex's default and POSIX modes.

## How the pyramid works

The square pyramid has its apex at `(0, -12, 0)` and a base of half-width 12 at
`y = 12`. Its four sloped sides satisfy `2|x| - y <= 12` and
`2|z| - y <= 12`; the base satisfies `y <= 12`.

For each screen cell, the play intersects an orthographic ray with these five
half-spaces. Their depth intervals overlap exactly where the pyramid is visible.
The closest entering plane supplies the visible face and its normal. Direct
plane intersections avoid marching through empty space and give clean edges.
SPL stores intersection depths in units of 1/64, using only integer arithmetic.

The view has a fixed 3–4–5 tilt, while the pyramid turns about its vertical axis.
Sine and cosine are maintained in fixed point with scale 10000. Each frame
rotates them using `(9952, 980) / 10000`, approximately 5.625 degrees. Resetting
the rotation after 64 frames prevents cumulative drift. Sideways movement follows
the sine; vertical bobbing follows the double-angle cosine. The whole animation
cycle repeats exactly. Rows represent two world units and columns one to
compensate for typical terminal character proportions.

Surface normals rotate with the pyramid. A light toward the viewer's upper
left selects face shades from `.:-=+*#@`. These calculations, the pixel loops,
and the animation loop are SPL dialogue.

The native play reads two integer lines: the frame count (`0` means continuous)
and how many initial rotation steps to skip. It emits fixed-size frames ending
in a form-feed byte. For example, this runs the native SPL program without the
terminal presenter:

```sh
printf '1\n8\n' | bazelisk run //:pyramid_play
```

The launcher supplies this protocol, reads completed frames, and displays them
with cursor-home sequences in an alternate terminal screen. It handles timing
and signals; it contains no geometry, rotation, shading, or motion calculations.

SPL stores integers in named characters. A positive noun is worth 1 and each
adjective doubles it: `a tiny furry cat` is 4. Questions set a truth flag, and
conditional scene jumps implement branches and loops.

| Character | Role |
| --- | --- |
| Ingrid | Director who assigns values to the other actor on stage |
| Astrid, Sigrid | Screen column and row |
| Eira, Frida | Fixed-point cosine and sine |
| Tove, Ylva | Horizontal sway and vertical bob |
| Hilde, Silje | Translated world coordinates |
| Anja, Bente, Grete, Heidi | Rotated side-plane slopes |
| Inger, Lene, Mette | Plane offsets |
| Maja, Thea, Runa | Near, far, and candidate intersection depths |
| Solveig, Hanne | Current plane and closest visible face |
| Hedda, Sunniva, Tuva | Clipping and rotation temporaries |
| Vilde, Liv | Surface brightness and output glyph |
| Nora, Kari, Marit, Oda | Frame count, limit, skipped frames, rotation phase |

The compiler word list supports these thirty Norwegian names alongside the
original Shakespearean cast. Each stage change leaves Ingrid with exactly one
other character, so second-person assignment is unambiguous. Every cast member
gets a retort; character descriptions and scene titles carry the English banter.

## Bazel integration

[`bazel/spl.bzl`](bazel/spl.bzl) provides `spl_translate` and `spl_binary`:

```starlark
load("//bazel:spl.bzl", "spl_binary")

spl_binary(
    name = "my_play",
    src = "my_play.spl",
)
```

The translation action runs the original `spl2c` compiler, declares its generated
C output, and feeds it to rules_cc's `cc_binary`. Bazel builds the compiler for
the execution configuration, and links the SPL runtime into each program.
You can also build the translator directly with
`bazel build //third_party/spl:spl2c`.

Compiler provenance, the local allocation fix, and GPL licensing are documented
in [`third_party/spl/README.md`](third_party/spl/README.md). Upstream documentation:
[Shakespeare language and compiler](https://krayon.github.io/shakespearelang/docs/shakespeare.html).
