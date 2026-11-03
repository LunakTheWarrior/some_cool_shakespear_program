# I Only Rendered This Because You Asked Me To

A 3D ASCII renderer written in the **Shakespeare Programming Language (SPL)**.
The executable renders a shaded sphere, tilted torus, or rotated cube into a
49-column by 25-row terminal frame.

The geometry, ray traversal, rotations, normals, lighting, glyph selection, and
output loops are all in [`main.spl`](main.spl). The compiler translates the play
to C and links it to its original runtime. Python is used to check test results.

## Build and run

On Linux, install Bazel 8.1.1 (or Bazelisk), a C compiler, Bison, Flex and its
development library, and Python 3. On Debian/Ubuntu the non-Bazel dependencies
are available with:

```sh
sudo apt-get install build-essential bison flex libfl-dev python3
```

Build once and select a shape with its initial letter:

```sh
bazel build //:ascii3d
printf 's' | ./bazel-bin/ascii3d    # sphere
printf 't' | ./bazel-bin/ascii3d    # torus
printf 'c' | ./bazel-bin/ascii3d    # cube
```

Or build and run together:

```sh
printf 't' | bazel run //:ascii3d
```

The play reads one character from standard input. At a terminal, type a letter
and press Enter. EOF and unrecognized characters select the sphere:

```sh
./bazel-bin/ascii3d </dev/null
```

There are no command-line arguments or terminal escape sequences. The output
is one static frame with a trailing newline, so it also works when redirected
to a file. Coordinates and view rotations are fixed in the play.

The first Bazel build downloads the pinned rules_cc and rules_shell modules;
the SPL compiler source is already vendored. Flex and Bison are host tools
invoked by build actions, so the build is intended for a local Linux machine
with those dependencies installed.

## Tests

```sh
bazel test //... --test_output=errors
```

The suite runs 12 checks against the compiled SPL executables:

- [`tests/arithmetic.spl`](tests/arithmetic.spl) exercises square, integer square
  root, signed division, multiplication, and remainder.
- [`tests/control_flow.spl`](tests/control_flow.spl) counts down through a
  conditional scene jump and recalls the values from a character's stack.
- [`tests/test_renderer.py`](tests/test_renderer.py) checks those plays' answers,
  frame dimensions and ASCII palette, reviewed golden frames, the sphere's
  analytic silhouette and light direction, the torus hole, the cube's three
  face shades, distinct shapes, EOF behavior, and input selection.

Snapshots in [`tests/golden`](tests/golden) preserve all spaces, including those
at the end of each row. Geometric assertions check the output independently
of the snapshots. Every subprocess has a timeout to catch broken SPL loops.

## How the play works

Each terminal cell casts an orthographic ray from depth +24 toward -24 in
quarter-unit steps. The first sample inside the selected solid supplies that
cell's glyph. No hit produces a space. Horizontal cells advance by one world
unit; rows advance by two, compensating for typical terminal character proportions.

The sphere has radius 18. The torus has major radius 12 and tube radius 5,
tilted using a 3–4–5 rotation in the vertical/depth plane. The cube has half-side
10 and uses two 3–4–5 rotations to expose three faces. Fixed-point arithmetic
preserves fractional rotated coordinates without floating-point SPL values.

The sphere and torus use surface normals and a light toward the viewer's upper
left; the cube uses constant brightness per face. Brightness selects from
`.:-=+*#@`. Sampling and integer normals give intentionally discrete shading.

SPL stores integers in Shakespearean characters. A noun is worth +1 or -1,
each adjective doubles it, and dialogue performs arithmetic. For instance,
`a tiny furry cat` is 4, and `the square of Astrid` computes x². Questions set
a truth flag, and `If so, let us proceed to Scene V` implements a branch.

| Character | Role |
| --- | --- |
| Ingrid | Director who assigns values to the other actor on stage |
| Astrid, Sigrid | Horizontal and vertical coordinates |
| Solveig | Ray depth, stored in quarter units |
| Nora | Shape selection character |
| Liv | Output glyph |
| Frida, Maja, Thea | Rotated coordinates |
| Eira, Hedda, Sunniva | Radial distance and temporary calculations |
| Runa, Tuva, Hanne | Normals or squared cube coordinates |
| Vilde | Surface brightness |

The Norwegian cast trades prickly compliments and reluctant affection in English.
Scene titles and character descriptions carry the banter; executable dialogue
uses the SPL vocabulary. The compiler word list includes these sixteen extra
character names alongside the original Shakespearean cast. Each stage change
leaves Ingrid with exactly one other character, so second-person assignment is unambiguous.
Characters retain their values offstage.

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
