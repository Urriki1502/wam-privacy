#!/usr/bin/env python3
import json
import pathlib
import re
import sys

if len(sys.argv) != 4:
    raise SystemExit("usage: check_phase14c_benchmark.py <json> <time-log> <output-json>")

profile_path = pathlib.Path(sys.argv[1])
time_path = pathlib.Path(sys.argv[2])
out_path = pathlib.Path(sys.argv[3])

profile = json.loads(profile_path.read_text())
time_text = time_path.read_text(errors="replace")

m = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", time_text)
if not m:
    raise SystemExit("missing GNU time peak RSS evidence")
peak_rss_kb = int(m.group(1))

ceilings = {
    "setup_ms": 300_000,
    "prove_ms": 900_000,
    "verify_avg_ms": 120_000,
    "verify_max_ms": 180_000,
    "proof_bytes": 4 * 1024 * 1024,
    "envelope_bytes": 4 * 1024 * 1024 + 2048,
    "peak_rss_kb": 6_000_000,
}

observed = dict(profile)
observed["peak_rss_kb"] = peak_rss_kb

violations = []
for key, ceiling in ceilings.items():
    value = observed[key]
    if value > ceiling:
        violations.append({"metric": key, "observed": value, "ceiling": ceiling})

result = {
    "schema": 1,
    "runner_scope": "github-hosted ubuntu-24.04 qualification baseline",
    "observed": observed,
    "ceilings": ceilings,
    "violations": violations,
    "result": "PASS" if not violations else "FAIL",
    "claim_boundary": (
        "CI qualification ceiling only; not a production latency, throughput, "
        "capacity, or hardware sizing claim."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(0 if not violations else 2)
