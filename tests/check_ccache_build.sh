#!/usr/bin/env bash
# Optional build regression test; run directly, outside `bazel test`.
set -euo pipefail
cd "$(dirname "$0")/.."
bazel_bin="$(command -v "${BAZEL:-bazel}")"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/spl-ccache-check.XXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/poison" "$scratch/wrapped"

# Simulate a host that selects ccache both through CC and compiler PATH shims.
# This shim must never be invoked when the project defaults are in effect.
cat > "$scratch/poison/gcc" <<'SH'
#!/usr/bin/env bash
echo 'ERROR: inherited compiler cache wrapper was selected' >&2
exit 86
SH

# Also test an intentional compiler override that still routes through a cache
# wrapper. It must receive the disable flag for probes AND compile/link actions.
cat > "$scratch/wrapped/gcc" <<'SH'
#!/usr/bin/env bash
if [[ "${CCACHE_DISABLE:-}" != 1 ]]; then
    echo 'ERROR: compiler cache was not disabled' >&2
    exit 87
fi
exec /usr/bin/gcc "$@"
SH
chmod +x "$scratch/poison/gcc" "$scratch/wrapped/gcc"

CC="$scratch/poison/gcc" PATH="$scratch/poison:$PATH" \
    "$bazel_bin" --batch --output_base="$scratch/output" \
    test //... --test_output=errors --nocache_test_results \
    --symlink_prefix="$scratch/links/"

CC="$scratch/poison/gcc" PATH="$scratch/poison:$PATH" \
    "$bazel_bin" --batch --output_base="$scratch/output" \
    test //... --test_output=errors --nocache_test_results \
    --symlink_prefix="$scratch/links/" --repo_env="CC=$scratch/wrapped/gcc"
