Vendored source from https://github.com/krayon/shakespearelang at commit
`70f60d8669fb241ff830924c0ed2ea0bc751f444` (SPL 1.2.1 mirror).
Only the compiler, runtime, word lists, and license files are included.

Upstream authors: Karl Hasselström and Jon Åslund. See COPYING for GPL-2.0-or-later.

Local changes:

- `makescanner.c`: allocate `strlen(argv[1]) + 1` bytes for the include path,
  including its terminating NUL. The original overruns its allocation and aborts
  on this system's fortified libc.
- `BUILD.bazel`: generate the parser with Bison and scanner with Flex, then build
  the original compiler and runtime using rules_cc.

The SPL grammar and arithmetic semantics are unchanged.
