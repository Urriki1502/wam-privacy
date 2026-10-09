"""SEC-001 only: interface for independently trusted monotonic checkpointing.

Implementations MUST commit compare-and-advance atomically, and survive restarts
outside the rollback domain of the SQLite wallet-policy store. This module is
only an interface; it does not provide secure hardware / OS storage.
"""
from dataclasses import dataclass
import hashlib
from typing import Protocol


@dataclass(frozen=True)
class CheckpointStamp:
    generation: int
    snapshot_digest: str


def stamp_for(generation: int, snapshot: str) -> CheckpointStamp:
    if type(generation) is not int or generation < 0 or generation >= (1 << 63):
        raise ValueError("invalid checkpoint generation")
    if type(snapshot) is not str:
        raise ValueError("invalid checkpoint bytes")
    digest = hashlib.sha256(
        b"WAM/SEC001/MONOTONIC/v1\0"
        + generation.to_bytes(8, "little")
        + snapshot.encode("ascii")
    ).hexdigest()
    return CheckpointStamp(generation, digest)


class TrustedWitness(Protocol):
    def read(self) -> CheckpointStamp:
        """Read the most recent trusted stamp or raise (no default/reset)."""
        ...

    def advance(self, expected: CheckpointStamp, updated: CheckpointStamp) -> None:
        """Atomically CAS the durable stamp, never allow decrement or reset.

        If this call returned successfully, updated MUST be durable even if
        the wallet-policy SQLite transaction crashes immediately afterward.
        """
        ...
