"""Executable shielded-state model for Phase 7 research.

This module is intentionally NOT a privacy implementation and NOT a proof system.
It models consensus-relevant state transitions that a future shielded proof would
need to prove: note membership, spend-authority binding, nullifier uniqueness,
value conservation, shield/unshield accounting, and protocol versioning.

All hashing here is domain-separated SHA-256 solely to make deterministic test
vectors. It must not be interpreted as a production note commitment/nullifier
construction.
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

    created_atoms = sum(note.value for note in tx.outputs)
    lhs = spent_atoms + tx.transparent_in
    rhs = created_atoms + tx.transparent_out + tx.fee_atoms
    if lhs != rhs:
        _fail("VALUE_CONSERVATION")

    new_pool = state.pool_atoms + tx.transparent_in - tx.transparent_out
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
    )
