#!/usr/bin/env python3
"""Generate the Phase 7 semantic oracle consumed by the Phase 8 Halo2 bridge.

The oracle intentionally contains semantic accept/reject results and relational
properties only. It never claims byte compatibility between the Phase 7
SHA-256 placeholder hashes and the Phase 8 Poseidon circuit-native hashes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototypes.shielded_model.model import (
    MAX_ATOMS,
    Note,
    ShieldedModelError,
    ShieldedState,
    Spend,
    Transition,
    apply_transition,
    nullifier,
    spend_key_tag,
)


def blob(tag: int) -> bytes:
    return bytes([tag]) * 32


def note(value: int, marker: int, nullifier_key: bytes) -> Note:
    return Note(
        value=value,
        recipient_tag=blob(0x40 + marker),
        spend_key_tag=spend_key_tag(nullifier_key),
        rho=blob(0x60 + marker),
        rseed=blob(0x80 + marker),
    )


BALANCE_CASES = (
    ("shield_only", 0, 100_000, 99_000, 0, 1_000),
    ("private_transfer_unshield", 100_000, 0, 74_000, 25_000, 1_000),
    ("mixed", 50_000, 20_000, 60_000, 9_000, 1_000),
    ("exact_cap_roundtrip", MAX_ATOMS, 0, MAX_ATOMS, 0, 0),
    ("exact_cap_transparent_fee", 0, MAX_ATOMS, 0, 0, MAX_ATOMS),
    ("inflation_attempt", 100_000, 0, 100_001, 0, 0),
    ("hidden_fee_mismatch", 100_000, 0, 99_500, 0, 400),
    ("amount_over_cap", MAX_ATOMS + 1, 0, MAX_ATOMS + 1, 0, 0),
)


def evaluate_balance_case(name: str, spent: int, tin: int, created: int, tout: int, fee: int) -> dict:
    nk = blob(0x11)
    try:
        spends = ()
        commitments = ()
        if spent:
            input_note = note(spent, 1, nk)
            spends = (Spend(input_note, nk),)
            commitments = (input_note.commitment,)

        outputs = ()
        if created:
            outputs = (note(created, 2, blob(0x12)),)

        # Seed the modeled pool with the value represented by the spend fixture.
        # This keeps pool accounting coherent while isolating the semantic
        # accept/reject comparison from unrelated malformed-state behavior.
        state = ShieldedState(commitments=commitments, pool_atoms=spent)
        tx = Transition(
            spends=spends,
            outputs=outputs,
            transparent_in=tin,
            transparent_out=tout,
            fee_atoms=fee,
        )
        apply_transition(state, tx)
        accepted, error = True, None
    except ShieldedModelError as exc:
        accepted, error = False, str(exc)

    return {
        "name": name,
        "spent": spent,
        "transparent_in": tin,
        "created": created,
        "transparent_out": tout,
        "fee": fee,
        "phase7_accepts": accepted,
        "phase7_error": error,
    }


def relational_properties() -> dict:
    nk = blob(0x21)
    other_nk = blob(0x22)
    a = note(10_000, 3, nk)
    b = Note(
        value=a.value,
        recipient_tag=a.recipient_tag,
        spend_key_tag=a.spend_key_tag,
        rho=blob(0x64),
        rseed=a.rseed,
    )
    mutated = Note(
        value=a.value,
        recipient_tag=a.recipient_tag,
        spend_key_tag=a.spend_key_tag,
        rho=a.rho,
        rseed=blob(0x85),
    )

    try:
        nullifier(a, other_nk)
        mismatch_rejected = False
    except ShieldedModelError as exc:
        mismatch_rejected = str(exc) == "SPEND_AUTHORITY_MISMATCH"

    return {
        "authority_mismatch_rejected": mismatch_rejected,
        "same_authority_different_notes_have_distinct_nullifiers": nullifier(a, nk) != nullifier(b, nk),
        "note_mutation_changes_commitment": a.commitment != mutated.commitment,
        "note_mutation_changes_root": ShieldedState(commitments=(a.commitment,)).root
        != ShieldedState(commitments=(mutated.commitment,)).root,
        "root_byte_compatibility_claimed": False,
    }


def build_oracle() -> dict:
    return {
        "schema": 1,
        "phase7_protocol_version": 1,
        "max_wam_atoms": MAX_ATOMS,
        "comparison_mode": "semantic-not-byte-equivalence",
        "phase7_tree_hash": "domain-separated-sha256-placeholder",
        "phase8_tree_hash": "halo2-poseidon-p128pow5t3",
        "balance_cases": [evaluate_balance_case(*case) for case in BALANCE_CASES],
        "properties": relational_properties(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    oracle = build_oracle()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"phase8f_oracle": "generated", "cases": len(oracle["balance_cases"])}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
