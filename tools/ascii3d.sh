#!/usr/bin/env bash
set -euo pipefail

# Standard runfiles initialization, including manifest-only installations.
set +e
source "${RUNFILES_DIR:-/dev/null}/bazel_tools/tools/bash/runfiles/runfiles.bash" 2>/dev/null ||
  source "$(grep -sm1 '^bazel_tools/tools/bash/runfiles/runfiles.bash ' "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -d ' ' -f 2-)" 2>/dev/null ||
  source "$0.runfiles/bazel_tools/tools/bash/runfiles/runfiles.bash" 2>/dev/null ||
  source "$(grep -sm1 '^bazel_tools/tools/bash/runfiles/runfiles.bash ' "$0.runfiles_manifest" | cut -d ' ' -f 2-)" 2>/dev/null ||
  { echo 'Cannot locate the Bazel runfiles library.' >&2; exit 1; }
set -e

exec python3 "$(rlocation "_main/tools/animate.py")" \
    "$(rlocation "_main/pyramid_play")" "$@"
