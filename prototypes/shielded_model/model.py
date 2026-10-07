"""Executable shielded-state model for Phase 7 research.

This module is intentionally NOT a privacy implementation and NOT a proof system.
It models state-transition rules a future shielded proof would need to enforce:
note membership, view/spend authority separation, nullifier uniqueness, value
conservation, pool accounting, commitment-tree anchoring, and versioning.

All hashing here is domain-separated SHA-256 solely to make deterministic test
vectors. It must not be interpreted as a production commitment, nullifier,
viewing, or Merkle construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

PROTOCOL_VERSION = 1
MAX_ATOMS = 22_000_000 * 100_000_000
ASSET_ID = b"WAM"


class ShieldedModelError(ValueError):
    """Fixed-code failure for the executable specification."""


def _fail(code: str) -> None:
    raise ShieldedModelError(code)


def _u64(value: int) -> bytes:
    if type(value) is not int or not 0 <= value <= MAX_ATOMS:
        _fail("AMOUNT_RANGE")
    return value.to_bytes(8, "little")


def _field(name: str, value: bytes, length: int) -> bytes:
    if not isinstance(value, bytes) or len(value) != length:
        _fail(name)
    return value


def _h(domain: bytes, *parts: bytes) -> bytes:
    return sha256(domain + b"".join(parts)).digest()


def spend_key_tag(nullifier_key: bytes) -> bytes:
    nk = _field("NULLIFIER_KEY", nullifier_key, 32)
    return _h(b"WAM/Shielded/SpendKeyTag/v1\x00", nk)


def view_tag(view_key: bytes, rho: bytes) -> bytes:
    vk = _field("VIEW_KEY", view_key, 32)
    r = _field("RHO", rho, 32)
    return _h(b"WAM/Shielded/ViewTag/v1\x00", vk, r)


@dataclass(frozen=True)
class Note:
    value: int
    recipient_tag: bytes
    spend_key_tag: bytes
    rho: bytes
    rseed: bytes
    version: int = PROTOCOL_VERSION

    def validate(self) -> None:
        if self.version != PROTOCOL_VERSION:
            _fail("UNSUPPORTED_NOTE_VERSION")
        _u64(self.value)
        if self.value == 0:
            _fail("ZERO_VALUE_NOTE")
        _field("RECIPIENT_TAG", self.recipient_tag, 32)
        _field("SPEND_KEY_TAG", self.spend_key_tag, 32)
        _field("RHO", self.rho, 32)
        _field("RSEED", self.rseed, 32)

    @property
    def commitment(self) -> bytes:
        self.validate()
        return note_commitment(self)


def note_commitment(note: Note) -> bytes:
    note.validate()
    return _h(
        b"WAM/Shielded/NoteCommitment/v1\x00",
        ASSET_ID,
        _u64(note.value),
        note.recipient_tag,
        note.spend_key_tag,
        note.rho,
        note.rseed,
    )


def can_view(note: Note, view_key: bytes) -> bool:
    note.validate()
    return view_tag(view_key, note.rho) == note.recipient_tag


def view_note(note: Note, view_key: bytes) -> dict | None:
    """Model selective recognition; this is not encrypted note decryption."""

    if not can_view(note, view_key):
        return None
    return {
        "value": note.value,
        "commitment": note.commitment.hex(),
        "version": note.version,
    }


def nullifier(note: Note, nullifier_key: bytes) -> bytes:
    note.validate()
    nk = _field("NULLIFIER_KEY", nullifier_key, 32)
    if spend_key_tag(nk) != note.spend_key_tag:
        _fail("SPEND_AUTHORITY_MISMATCH")
    return _h(
        b"WAM/Shielded/Nullifier/v1\x00",
        nk,
        note.commitment,
        note.rho,
    )


def commitment_root(commitments: tuple[bytes, ...]) -> bytes:
    """Deterministic placeholder Merkle root for state anchoring."""

    if any(not isinstance(c, bytes) or len(c) != 32 for c in commitments):
        _fail("COMMITMENT_FORMAT")
    if not commitments:
        return _h(b"WAM/Shielded/MerkleEmpty/v1\x00")

    level = [_h(b"WAM/Shielded/MerkleLeaf/v1\x00", c) for c in commitments]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            _h(b"WAM/Shielded/MerkleNode/v1\x00", level[i], level[i + 1])
            for i in range(0, len(level), 2)
        ]
    return _h(b"WAM/Shielded/MerkleRoot/v1\x00", level[0])


@dataclass(frozen=True)
class Spend:
    note: Note
    nullifier_key: bytes

    @property
    def nf(self) -> bytes:
        return nullifier(self.note, self.nullifier_key)


@dataclass(frozen=True)
class ShieldedState:
    commitments: tuple[bytes, ...] = ()
    nullifiers: frozenset[bytes] = frozenset()
    pool_atoms: int = 0
    version: int = PROTOCOL_VERSION

    @property
    def root(self) -> bytes:
        return commitment_root(self.commitments)

    def validate(self) -> None:
        if self.version != PROTOCOL_VERSION:
            _fail("UNSUPPORTED_STATE_VERSION")
        _u64(self.pool_atoms)
        if len(set(self.commitments)) != len(self.commitments):
            _fail("DUPLICATE_COMMITMENT_STATE")
        if any(not isinstance(c, bytes) or len(c) != 32 for c in self.commitments):
            _fail("COMMITMENT_FORMAT")
        if any(not isinstance(n, bytes) or len(n) != 32 for n in self.nullifiers):
            _fail("NULLIFIER_FORMAT")
        self.root


@dataclass(frozen=True)
class Transition:
    spends: tuple[Spend, ...] = ()
    outputs: tuple[Note, ...] = ()
    transparent_in: int = 0
    transparent_out: int = 0
    fee_atoms: int = 0
    version: int = PROTOCOL_VERSION

    def validate_shape(self) -> None:
        if self.version != PROTOCOL_VERSION:
            _fail("UNSUPPORTED_TRANSITION_VERSION")
        if not self.spends and not self.outputs and not self.transparent_in and not self.transparent_out:
            _fail("EMPTY_TRANSITION")
        _u64(self.transparent_in)
        _u64(self.transparent_out)
        _u64(self.fee_atoms)
        if len(self.spends) > 256 or len(self.outputs) > 256:
            _fail("TRANSITION_LIMIT")
        for spend in self.spends:
            if not isinstance(spend, Spend):
                _fail("SPEND_FORMAT")
            spend.note.validate()
            _field("NULLIFIER_KEY", spend.nullifier_key, 32)
        for note in self.outputs:
            if not isinstance(note, Note):
                _fail("NOTE_FORMAT")
            note.validate()


@dataclass(frozen=True)
class TransitionResult:
    state: ShieldedState
    spent_atoms: int
    created_atoms: int
    transparent_in: int
    transparent_out: int
    fee_atoms: int
    prior_root: bytes
    new_root: bytes

    @property
    def conservation_lhs(self) -> int:
        return self.spent_atoms + self.transparent_in

    @property
    def conservation_rhs(self) -> int:
        return self.created_atoms + self.transparent_out + self.fee_atoms


def apply_transition(state: ShieldedState, tx: Transition) -> TransitionResult:
    """Apply one modeled shielded transition with fail-closed validation."""

    state.validate()
    tx.validate_shape()
    prior_root = state.root

    commitments = set(state.commitments)
    new_nullifiers: list[bytes] = []
    spent_atoms = 0

    for spend in tx.spends:
        cm = spend.note.commitment
        if cm not in commitments:
            _fail("NOTE_NOT_IN_STATE")
        nf = spend.nf
        if nf in state.nullifiers or nf in new_nullifiers:
            _fail("NULLIFIER_ALREADY_USED")
        new_nullifiers.append(nf)
        spent_atoms += spend.note.value

    new_commitments = [note.commitment for note in tx.outputs]
    if len(set(new_commitments)) != len(new_commitments):
        _fail("DUPLICATE_OUTPUT_COMMITMENT")
    if any(cm in commitments for cm in new_commitments):
        _fail("COMMITMENT_ALREADY_EXISTS")

    if spent_atoms > state.pool_atoms:
        _fail("POOL_SPEND_EXCEEDS_BALANCE")

    created_atoms = sum(note.value for note in tx.outputs)
    lhs = spent_atoms + tx.transparent_in
    rhs = created_atoms + tx.transparent_out + tx.fee_atoms
    if lhs != rhs:
        _fail("VALUE_CONSERVATION")

    # Conservation implies the shielded pool changes by the transparent flow
    # and by any fee paid out of the transition. Keeping fee outside this
    # accounting would leave phantom value in the modeled pool.
    new_pool = (
        state.pool_atoms
        + tx.transparent_in
        - tx.transparent_out
        - tx.fee_atoms
    )
    if new_pool < 0:
        _fail("POOL_UNDERFLOW")
    _u64(new_pool)

    next_state = ShieldedState(
        commitments=state.commitments + tuple(new_commitments),
        nullifiers=frozenset((*state.nullifiers, *new_nullifiers)),
        pool_atoms=new_pool,
        version=state.version,
    )
    next_state.validate()

    return TransitionResult(
        next_state,
        spent_atoms,
        created_atoms,
        tx.transparent_in,
        tx.transparent_out,
        tx.fee_atoms,
        prior_root,
        next_state.root,
    )
