"""Composition contract for wallet privacy, PayJoin, signer, and network policy.

This is an in-memory normalized integration harness. It performs no real WAM
parsing, signing, networking, RPC, or broadcast.
"""

from __future__ import annotations

from payjoin_safety import PayjoinContext, Transaction as PayjoinTransaction, validate_proposal
from network_privacy import NetworkPlan, NetworkPolicy, validate_network_plan
from signer_abstraction import (
    Approval,
    SignRequest,
    SignerGate,
    TransactionOutput as SignerOutput,
    redacted_signer_event,
)
from wallet_privacy import Selection, redacted_event as redacted_wallet_event


class StackError(ValueError):
    """Fixed-code integration boundary failure."""


def _fail(code: str) -> None:
    raise StackError(code)


def _bind_wallet_selection(
    selection: Selection,
    original: PayjoinTransaction,
    context: PayjoinContext,
    approval: Approval,
) -> None:
    """Bind Phase 2 wallet decisions to the normalized pre-PayJoin transaction."""

    original_sender = [i for i in original.inputs if i.owner == "sender"]
    selected = {c.outpoint: c.atoms for c in selection.selected}
    observed = {i.outpoint: i.atoms for i in original_sender}

    if selected != observed:
        _fail("WALLET_INPUT_BINDING_MISMATCH")

    if original.fee_atoms > approval.max_fee_atoms:
        _fail("ORIGINAL_FEE_NOT_APPROVED")

    if len(approval.intents) != 1:
        _fail("INTEGRATION_SINGLE_PAYMENT_ONLY")
    intent = approval.intents[0]
    payment = original.outputs[context.payment_output_index]
    if (
        payment.owner != "receiver"
        or payment.destination != intent.destination
        or payment.atoms != intent.atoms
    ):
        _fail("ORIGINAL_INTENT_MISMATCH")

    sender_outputs = [o for o in original.outputs if o.owner == "sender"]
    if selection.change_required:
        if (
            len(sender_outputs) != 1
            or sender_outputs[0].atoms != selection.change_atoms
        ):
            _fail("ORIGINAL_CHANGE_MISMATCH")
    elif sender_outputs:
        _fail("ORIGINAL_CHANGE_MISMATCH")

    if selection.change_required != ("CHANGE_CREATED" in selection.warnings):
        _fail("WALLET_CHANGE_WARNING_MISMATCH")
    if (len(selection.clusters) > 1) != ("CLUSTER_MERGE" in selection.warnings):
        _fail("WALLET_CLUSTER_WARNING_MISMATCH")


def _signer_outputs(
    proposal: PayjoinTransaction,
    context: PayjoinContext,
) -> tuple[SignerOutput, ...]:
    outputs: list[SignerOutput] = []
    for index, output in enumerate(proposal.outputs):
        if index == context.payment_output_index:
            if output.owner != "receiver":
                _fail("PAYMENT_OWNERSHIP_MISMATCH")
            outputs.append(SignerOutput(output.destination, output.atoms, "payment", False))
        elif output.owner == "sender":
            outputs.append(SignerOutput(output.destination, output.atoms, "change", True))
        else:
            # Phase 4 v0.1 already disallows receiver batching. Keep the stack
            # representation equally strict rather than silently reclassifying.
            _fail("UNREPRESENTABLE_PROPOSAL_OUTPUT")
    return tuple(outputs)


def _warnings(selection: Selection) -> tuple[str, ...]:
    ordered = [*selection.warnings, "PAYJOIN_PROPOSAL"]
    return tuple(dict.fromkeys(ordered))


def authorize_payjoin_stack(
    *,
    selection: Selection,
    original: PayjoinTransaction,
    proposal: PayjoinTransaction,
    payjoin_context: PayjoinContext,
    signer_gate: SignerGate,
    approval: Approval,
    network_plan: NetworkPlan,
    network_policy: NetworkPolicy | None,
    request_id: str,
    tx_digest: str,
) -> dict:
    """Validate all current privacy layers before allowing the signer fixture.

    Order matters:
      1. bind wallet selection to original transaction;
      2. validate PayJoin proposal;
      3. validate network route plan;
      4. build signer view and enforce explicit approval;
      5. invoke provider.

    A network-policy failure therefore occurs before signing.
    """

    _bind_wallet_selection(selection, original, payjoin_context, approval)

    try:
        payjoin = validate_proposal(original, proposal, payjoin_context)
    except ValueError as exc:
        raise StackError("PAYJOIN_" + str(exc)) from None

    try:
        network = validate_network_plan(
            network_plan,
            NetworkPolicy() if network_policy is None else network_policy,
        )
    except ValueError as exc:
        raise StackError("NETWORK_" + str(exc)) from None

    request = SignRequest(
        request_id=request_id,
        network="regtest",
        tx_digest=tx_digest,
        input_count=len(proposal.inputs),
        outputs=_signer_outputs(proposal, payjoin_context),
        fee_atoms=proposal.fee_atoms,
        wallet_input_atoms=selection.total_input_atoms,
        warning_codes=_warnings(selection),
    )

    try:
        signed = signer_gate.sign(request, approval)
    except ValueError as exc:
        raise StackError("SIGNER_" + str(exc)) from None

    return {
        "schema": 1,
        "wallet": redacted_wallet_event(selection),
        "payjoin": payjoin,
        "network": network,
        "signer": redacted_signer_event(request, signer_gate.provider, "PASS"),
        "signed": bool(signed.envelope),
        "result": "PASS",
    }


def redacted_stack_event(evidence: dict) -> dict:
    """Flatten only coarse integration results; never emit identifiers/amounts."""

    return {
        "schema": 1,
        "result": evidence.get("result"),
        "wallet_inputs": evidence.get("wallet", {}).get("selected_inputs"),
        "wallet_clusters": evidence.get("wallet", {}).get("cluster_count"),
        "wallet_change": evidence.get("wallet", {}).get("change_created"),
        "payjoin_receiver_inputs": evidence.get("payjoin", {}).get("receiver_inputs_added"),
        "private_broadcast_route": evidence.get("network", {}).get("broadcast_route"),
        "signer_kind": evidence.get("signer", {}).get("provider_kind"),
        "signed": bool(evidence.get("signed")),
    }
