#!/usr/bin/env bash
set -euo pipefail

CORE_REPO="https://github.com/wamcoin-core-dev/wam-coin.git"
CORE_SHA="260bc468e5adffea7ce68d8f97fac3e27e4c50b2"
WSP_REPO="https://github.com/Urriki1502/wam-silent-payments.git"
WSP_SHA="a8522fee9b6eda285998a5ff4a45d6bc4eb991b3"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
WORKSPACE="${WAM_PHASE1_WORKSPACE:-$HOME/wam-phase1-gate-c}"
CORE_DIR="$WORKSPACE/wam-coin"
WSP_DIR="$WORKSPACE/wam-silent-payments"

die() { printf '\nERROR: %s\n\n' "$*" >&2; exit 2; }
note() { printf '\n==> %s\n' "$*"; }

[[ "$(uname -s)" == "Darwin" ]] || die "This bootstrap is for macOS only."

command -v git >/dev/null || die "git is required."
command -v brew >/dev/null || die "Homebrew is required. Install it first from brew.sh."
xcode-select -p >/dev/null 2>&1 || die "Xcode Command Line Tools are required. Run: xcode-select --install"

for t in cmake autoconf automake libtool pkg-config; do
  command -v "$t" >/dev/null || die "Missing $t. Run: brew install cmake autoconf automake libtool pkg-config"
done

PYTHON=""
for p in python3.12 python3.13 python3; do
  if command -v "$p" >/dev/null 2>&1; then
    if "$p" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    then
      PYTHON="$p"
      break
    fi
  fi
done
[[ -n "$PYTHON" ]] || die "Python 3.11+ is required. Recommended: brew install python@3.12"

mkdir -p "$WORKSPACE"

clone_exact() {
  local url="$1" dir="$2" sha="$3"
  if [[ ! -d "$dir/.git" ]]; then
    note "Cloning $url"
    git clone "$url" "$dir"
  fi
  git -C "$dir" fetch --tags origin
  git -C "$dir" checkout --detach "$sha"
  local actual
  actual="$(git -C "$dir" rev-parse HEAD)"
  [[ "$actual" == "$sha" ]] || die "Pin mismatch in $dir: $actual"
  [[ -z "$(git -C "$dir" status --porcelain)" ]] || die "Dirty checkout: $dir"
}

clone_exact "$CORE_REPO" "$CORE_DIR" "$CORE_SHA"
clone_exact "$WSP_REPO" "$WSP_DIR" "$WSP_SHA"

note "Preparing exact WAM Core source"
(
  cd "$CORE_DIR"
  bash scripts/fetch-upstream.sh

  # fetch-upstream.sh creates RandomX first. On Apple Silicon, remove that
  # intermediate build so build_macos.sh recreates it using its ARM-aware path
  # (no x86 ARCH option). Source remains pinned and untouched.
  if [[ "$(uname -m)" == "arm64" ]]; then
    rm -rf build/randomx/build
  fi

  JOBS="${JOBS:-$(sysctl -n hw.ncpu 2>/dev/null || echo 4)}"     bash scripts/build_macos.sh
)

WAMD="$CORE_DIR/out/macos-$(uname -m)/wamd"
[[ -f "$WAMD" ]] || die "Expected daemon not found: $WAMD"

note "Verifying built daemon"
file "$WAMD"
"$WAMD" --version | head -5 || true

WAMD_SHA256="$("$PYTHON" - "$WAMD" <<'PY'
import hashlib
import pathlib
import sys
p = pathlib.Path(sys.argv[1])
h = hashlib.sha256()
with p.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
)"

cat > "$WORKSPACE/gate-c-env.sh" <<EOF
export WSP_DIR="$WSP_DIR"
export WAM_CORE_DIR="$CORE_DIR"
export WAMD="$WAMD"
export WAMD_SHA256="$WAMD_SHA256"
EOF
chmod 600 "$WORKSPACE/gate-c-env.sh"

cat <<EOF

BUILD READY

Core:  $CORE_SHA
WSP:   $WSP_SHA
wamd:  $WAMD
sha256:$WAMD_SHA256

Environment file:
  $WORKSPACE/gate-c-env.sh

Next command:
  source "$WORKSPACE/gate-c-env.sh"
  bash "$HERE/scripts/run_phase1_macos_gate_c.sh"

EOF
