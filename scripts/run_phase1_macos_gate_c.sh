#!/usr/bin/env bash
set -euo pipefail

WSP_EXPECTED="dcf1aecc00a64bfad3151fa202c3e07d47d83e69"
CORE_EXPECTED="260bc468e5adffea7ce68d8f97fac3e27e4c50b2"

: "${WSP_DIR:?Set WSP_DIR to the pinned wam-silent-payments checkout}"
: "${WAM_CORE_DIR:?Set WAM_CORE_DIR to the pinned wam-coin checkout}"
: "${WAMD:?Set WAMD to the exact daemon binary}"
: "${WAMD_SHA256:?Set WAMD_SHA256 to the exact daemon digest}"

[[ "$(uname -s)" == "Darwin" ]] || {
  echo "MACOS_REQUIRED" >&2
  exit 2
}

WSP_DIR="$(cd "$WSP_DIR" && pwd)"
WAM_CORE_DIR="$(cd "$WAM_CORE_DIR" && pwd)"
WAMD="$(cd "$(dirname "$WAMD")" && pwd)/$(basename "$WAMD")"

[[ "$(git -C "$WSP_DIR" rev-parse HEAD)" == "$WSP_EXPECTED" ]] || {
  echo "WSP_SHA_MISMATCH" >&2
  exit 2
}
[[ "$(git -C "$WAM_CORE_DIR" rev-parse HEAD)" == "$CORE_EXPECTED" ]] || {
  echo "CORE_SHA_MISMATCH" >&2
  exit 2
}
[[ -z "$(git -C "$WSP_DIR" status --porcelain)" ]] || {
  echo "WSP_DIRTY_TREE" >&2
  exit 2
}
[[ -z "$(git -C "$WAM_CORE_DIR" status --porcelain)" ]] || {
  echo "CORE_DIRTY_TREE" >&2
  exit 2
}
[[ -f "$WAMD" ]] || {
  echo "WAMD_NOT_FOUND" >&2
  exit 2
}

ACTUAL_SHA="$(python3 - "$WAMD" <<'PY'
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
[[ "$ACTUAL_SHA" == "$WAMD_SHA256" ]] || {
  echo "WAMD_SHA256_MISMATCH expected=$WAMD_SHA256 actual=$ACTUAL_SHA" >&2
  exit 2
}

cd "$WSP_DIR"
mkdir -p reports/phase1-macos

PYTHON=""
for p in python3.12 python3.13 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
  then
    PYTHON="$p"
    break
  fi
done
[[ -n "$PYTHON" ]] || { echo "PYTHON_3_11_REQUIRED" >&2; exit 2; }

if [[ ! -d .venv-phase1-macos ]]; then
  "$PYTHON" -m venv .venv-phase1-macos
fi
# shellcheck disable=SC1091
source .venv-phase1-macos/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-build-isolation . ./integration-deps/wam-sdk

run_gate() {
  local name="$1"
  shift
  local log="reports/phase1-macos/${name}.log"
  printf '\n==> %s\n' "$name"
  set +e
  "$@" 2>&1 | tee "$log"
  local rc=${PIPESTATUS[0]}
  set -e
  printf '%s\n' "$rc" > "reports/phase1-macos/${name}.exit"
  if [[ "$rc" -ne 0 ]]; then
    echo "GATE_FAILED: $name" >&2
    return "$rc"
  fi
}

run_gate selftest python -m devtools.selftest

run_gate contract   python -m wam_sp.conformance test     --contract-only     --output reports/phase1-macos/contract.json

# Differential testing is portable and provides an independent derivation oracle.
run_gate differential   python -m devtools.differential     --cases 10000     --output reports/phase1-macos/differential.json

# Current-Core compatibility-critical gates. These create private datadirs and
# use loopback/isolation; they do not attach to an existing wallet.
run_gate real-node   python -m devtools.real_node     --wamd "$WAMD"     --sha256 "$WAMD_SHA256"     --output reports/phase1-macos/real-node.json

run_gate interop   python -m devtools.interop     --wamd "$WAMD"     --sha256 "$WAMD_SHA256"

run_gate regtest   python -m devtools.regtest     --wamd "$WAMD"     --sha256 "$WAMD_SHA256"

python - "$WSP_DIR" "$WAM_CORE_DIR" "$WAMD" "$WAMD_SHA256" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys

wsp = Path(sys.argv[1])
core = Path(sys.argv[2])
wamd = Path(sys.argv[3])
digest = sys.argv[4]
r = wsp / "reports" / "phase1-macos"

def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

gates = {}
for exit_file in sorted(r.glob("*.exit")):
    name = exit_file.stem
    code = int(exit_file.read_text().strip())
    log = r / f"{name}.log"
    gates[name] = {
        "exit_code": code,
        "log_sha256": sha256(log) if log.exists() else None,
    }

for json_file in ("contract.json", "differential.json", "real-node.json"):
    p = r / json_file
    if p.exists():
        gates.setdefault(json_file.removesuffix(".json"), {})["report_sha256"] = sha256(p)

report = {
    "schema": 1,
    "platform": "macOS",
    "wsp_commit": git_head(wsp),
    "wam_core_commit": git_head(core),
    "wamd_path": str(wamd),
    "wamd_sha256": digest,
    "gates": gates,
    "result": "PASS" if gates and all(v.get("exit_code", 0) == 0 for v in gates.values()) else "FAIL",
    "note": "Atheris fuzzing is intentionally excluded from the macOS Gate C run; Linux fuzz evidence is tracked separately.",
}
out = r / "gate-c-evidence.json"
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
PY

echo
echo "PHASE1_MACOS_GATE_C_PASS"
echo "Evidence: $WSP_DIR/reports/phase1-macos/gate-c-evidence.json"
