#!/usr/bin/env bash
set -euo pipefail

WSP_EXPECTED="a8522fee9b6eda285998a5ff4a45d6bc4eb991b3"
CORE_EXPECTED="260bc468e5adffea7ce68d8f97fac3e27e4c50b2"

: "${WSP_DIR:?Set WSP_DIR to the wam-silent-payments checkout}"
: "${WAM_CORE_DIR:?Set WAM_CORE_DIR to the wam-coin checkout}"
: "${WAMD:?Set WAMD to the exact daemon binary built from the pinned Core target}"

WSP_DIR="$(cd "$WSP_DIR" && pwd)"
WAM_CORE_DIR="$(cd "$WAM_CORE_DIR" && pwd)"
WAMD="$(cd "$(dirname "$WAMD")" && pwd)/$(basename "$WAMD")"

head_sha() {
  git -C "$1" rev-parse HEAD
}

assert_clean() {
  if [[ -n "$(git -C "$1" status --porcelain)" ]]; then
    echo "DIRTY_TREE: $1" >&2
    exit 2
  fi
}

WSP_ACTUAL="$(head_sha "$WSP_DIR")"
CORE_ACTUAL="$(head_sha "$WAM_CORE_DIR")"

[[ "$WSP_ACTUAL" == "$WSP_EXPECTED" ]] || {
  echo "WSP_SHA_MISMATCH expected=$WSP_EXPECTED actual=$WSP_ACTUAL" >&2
  exit 2
}

[[ "$CORE_ACTUAL" == "$CORE_EXPECTED" ]] || {
  echo "CORE_SHA_MISMATCH expected=$CORE_EXPECTED actual=$CORE_ACTUAL" >&2
  exit 2
}

assert_clean "$WSP_DIR"
assert_clean "$WAM_CORE_DIR"

[[ -f "$WAMD" ]] || {
  echo "WAMD_NOT_FOUND: $WAMD" >&2
  exit 2
}

WAMD_SHA256="$(python3 - "$WAMD" <<'PY'
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

echo "WSP_SHA=$WSP_ACTUAL"
echo "WAM_CORE_SHA=$CORE_ACTUAL"
echo "WAMD=$WAMD"
echo "WAMD_SHA256=$WAMD_SHA256"

cd "$WSP_DIR"

if [[ ! -d .venv-phase1 ]]; then
  python3 -m venv .venv-phase1
fi

# shellcheck disable=SC1091
source .venv-phase1/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-build-isolation . ./integration-deps/wam-sdk

export WAMD
export WAMD_SHA256

python scripts/qualify.py

echo
echo "PHASE1_LOCAL_QUALIFICATION_FINISHED"
echo "Evidence: $WSP_DIR/reports/qualification.json"
