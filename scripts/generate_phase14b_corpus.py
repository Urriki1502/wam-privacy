#!/usr/bin/env python3
"""Generate deterministic Phase 14B parser fuzz corpus and hash manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

MAGIC = b"W10D"
FORMAT_VERSION = 2
CIRCUIT_ID = 0x0A04
PUBLIC_INPUT_COUNT = 9
MAX_PROOF_BYTES = 4 * 1024 * 1024


def canonical_structural_envelope() -> bytes:
    out = bytearray()
    out += MAGIC
    out += struct.pack("<H", FORMAT_VERSION)
    out += struct.pack("<H", CIRCUIT_ID)
    out += bytes(32)
    out += bytes([PUBLIC_INPUT_COUNT])
    out += bytes(PUBLIC_INPUT_COUNT * 32)
    proof = b"FUZZ"
    out += struct.pack("<I", len(proof))
    out += proof
    return bytes(out)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    base = canonical_structural_envelope()
    seeds: dict[str, bytes] = {
        "00-empty": b"",
        "01-magic": MAGIC,
        "02-header": base[:41],
        "03-canonical-structural": base,
        "04-truncated": base[:-1],
        "05-trailing": base + b"\x00",
    }

    bad_count = bytearray(base)
    bad_count[40] = 0
    seeds["06-bad-count"] = bytes(bad_count)

    noncanonical = bytearray(base)
    noncanonical[41:73] = b"\xff" * 32
    seeds["07-noncanonical-field"] = bytes(noncanonical)

    oversize = bytearray(base[: 41 + PUBLIC_INPUT_COUNT * 32])
    oversize += struct.pack("<I", MAX_PROOF_BYTES + 1)
    seeds["08-oversized-declared-proof"] = bytes(oversize)

    bad_version = bytearray(base)
    bad_version[4:6] = struct.pack("<H", FORMAT_VERSION + 1)
    seeds["09-unsupported-version"] = bytes(bad_version)

    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for name, data in sorted(seeds.items()):
        path = args.output / name
        path.write_bytes(data)
        records.append({"name": name, "bytes": len(data), "sha256": sha256(data)})

    manifest = {
        "schema": 1,
        "phase": "14B",
        "corpus": "hardened-envelope-parser",
        "seed_count": len(records),
        "seeds": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
