"""SEC-003 recovery decision contract; no coordinator/signing integration.

Input records must come from authenticated durable adapters, never RPC.
This pure checker cannot authenticate inputs or make independent stores atomic.
"""
from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    PREPARED = "PREPARED"
    POLICY_SPENT = "POLICY_SPENT"
    SIGNER_RESERVED = "SIGNER_RESERVED"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class Record:
    transaction_id: str
    request_binding: str
    phase: Phase
    policy_generation: int
    signer_binding: str | None = None
    result_binding: str | None = None


def recover(record: Record, *, trusted_policy_generation: int,
            policy_consumed: bool, signer_state: str,
            signer_binding: str | None = None,
            result_binding: str | None = None) -> str:
    """Conservative restart decision; COMPLETE only with matching receipts.

    Decisions describe contract requirements, not actions automatically taken.
    REAUTHORIZE requires new trusted authorization, never grant resurrection.
    """
    if (not isinstance(record, Record) or not isinstance(record.phase, Phase)
            or type(record.transaction_id) is not str or not record.transaction_id
            or type(record.request_binding) is not str or not record.request_binding
            or type(record.policy_generation) is not int or record.policy_generation < 0
            or type(trusted_policy_generation) is not int
            or trusted_policy_generation < record.policy_generation
            or type(policy_consumed) is not bool
            or signer_state not in ("ABSENT", "RESERVED", "COMPLETE")):
        return "BLOCKED"
    # A receipt from a different request can never satisfy this transaction.
    if signer_state != "ABSENT" and (
            signer_binding != record.request_binding
            or (record.signer_binding is not None
                and record.signer_binding != signer_binding)):
        return "BLOCKED"
    if signer_state == "COMPLETE":
        if (record.phase not in (Phase.SIGNER_RESERVED, Phase.COMPLETE)
                or not policy_consumed or type(result_binding) is not str
                or not result_binding
                or (record.result_binding is not None
                    and record.result_binding != result_binding)):
            return "BLOCKED"
        return "RETURN_DURABLE_RESULT"
    if signer_state == "RESERVED":
        # Provider may have acted; no retry, refund or resetting consumption.
        return "BLOCKED"
    if record.phase in (Phase.SIGNER_RESERVED, Phase.COMPLETE):
        # A durable reservation/result disappeared: corruption/rollback.
        return "BLOCKED"
    if record.phase == Phase.POLICY_SPENT and not policy_consumed:
        return "BLOCKED"
    return "REAUTHORIZE"


def next_phase(current: Phase, proposed: Phase) -> Phase:
    """Monotonic intent log phases. No phase skipping or rollback."""
    if not isinstance(current, Phase) or not isinstance(proposed, Phase):
        raise ValueError("INVALID_PHASE")
    order = list(Phase)
    if order.index(proposed) != order.index(current) + 1:
        raise ValueError("INVALID_TRANSITION")
    return proposed
