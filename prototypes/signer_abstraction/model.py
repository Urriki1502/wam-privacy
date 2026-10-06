"""Data model for Phase 3 signer abstraction.

This model is intentionally protocol-agnostic. It does not parse or sign WAM
transactions. A future WAM adapter must derive this view from the actual
transaction bytes and independently verify every field before invoking a signer.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_MONEY = 22_000_000 * 100_000_000


def _hex(value: str, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class PaymentIntent:
    destination: str
    atoms: int

    def validate(self) -> None:
        if not isinstance(self.destination, str) or not 1 <= len(self.destination) <= 512:
            raise ValueError("INTENT_DESTINATION")
        if type(self.atoms) is not int or not 1 <= self.atoms <= MAX_MONEY:
            raise ValueError("INTENT_AMOUNT")


@dataclass(frozen=True)
class TransactionOutput:
    destination: str
    atoms: int
    role: str  # "payment" or "change"
    wallet_owned: bool = False

    def validate(self) -> None:
        if not isinstance(self.destination, str) or not 1 <= len(self.destination) <= 512:
            raise ValueError("OUTPUT_DESTINATION")
        if type(self.atoms) is not int or not 1 <= self.atoms <= MAX_MONEY:
            raise ValueError("OUTPUT_AMOUNT")
        if self.role not in ("payment", "change"):
            raise ValueError("OUTPUT_ROLE")
        if type(self.wallet_owned) is not bool:
            raise ValueError("OUTPUT_OWNERSHIP")
        if self.role == "payment" and self.wallet_owned:
            raise ValueError("PAYMENT_MARKED_WALLET_OWNED")
        if self.role == "change" and not self.wallet_owned:
            raise ValueError("UNVERIFIED_CHANGE")


@dataclass(frozen=True)
class SignRequest:
    request_id: str
    network: str
    tx_digest: str
    input_count: int
    outputs: tuple[TransactionOutput, ...]
    fee_atoms: int
    wallet_input_atoms: int | None = None
    warning_codes: tuple[str, ...] = ()

    def validate_shape(self) -> None:
        if not _hex(self.request_id, 64):
            raise ValueError("REQUEST_ID")
        if self.network not in ("regtest", "testnet", "mainnet"):
            raise ValueError("NETWORK")
        if not _hex(self.tx_digest, 64):
            raise ValueError("TX_DIGEST")
        if type(self.input_count) is not int or not 1 <= self.input_count <= 128:
            raise ValueError("INPUT_COUNT")
        if not self.outputs or len(self.outputs) > 256:
            raise ValueError("OUTPUT_COUNT")
        for output in self.outputs:
            output.validate()
        if type(self.fee_atoms) is not int or not 0 <= self.fee_atoms <= 1_000_000:
            raise ValueError("FEE")
        if self.wallet_input_atoms is not None and (
            type(self.wallet_input_atoms) is not int
            or not 1 <= self.wallet_input_atoms <= MAX_MONEY
        ):
            raise ValueError("WALLET_INPUT_AMOUNT")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("DUPLICATE_WARNING")
        if any(not isinstance(w, str) or not 1 <= len(w) <= 64 for w in self.warning_codes):
            raise ValueError("WARNING_CODE")


@dataclass(frozen=True)
class Approval:
    intents: tuple[PaymentIntent, ...]
    max_fee_atoms: int
    allow_cluster_merge: bool = False
    allow_payjoin: bool = False
    allow_payment_increase: bool = False

    def validate(self) -> None:
        if not self.intents or len(self.intents) > 128:
            raise ValueError("APPROVAL_INTENTS")
        for intent in self.intents:
            intent.validate()
        if type(self.max_fee_atoms) is not int or not 0 <= self.max_fee_atoms <= 1_000_000:
            raise ValueError("APPROVAL_FEE")
        for value in (
            self.allow_cluster_merge,
            self.allow_payjoin,
            self.allow_payment_increase,
        ):
            if type(value) is not bool:
                raise ValueError("APPROVAL_FLAGS")
        if self.allow_payment_increase and not self.allow_payjoin:
            raise ValueError("PAYMENT_INCREASE_REQUIRES_PAYJOIN_APPROVAL")


@dataclass(frozen=True)
class SignerPolicy:
    allowed_networks: tuple[str, ...] = ("regtest",)
    hard_max_fee_atoms: int = 1_000_000
    max_inputs: int = 128
    max_outputs: int = 256

    def validate(self) -> None:
        if (
            not self.allowed_networks
            or len(set(self.allowed_networks)) != len(self.allowed_networks)
            or any(n not in ("regtest", "testnet", "mainnet") for n in self.allowed_networks)
        ):
            raise ValueError("POLICY_NETWORKS")
        if type(self.hard_max_fee_atoms) is not int or not 0 <= self.hard_max_fee_atoms <= 1_000_000:
            raise ValueError("POLICY_MAX_FEE")
        if type(self.max_inputs) is not int or not 1 <= self.max_inputs <= 128:
            raise ValueError("POLICY_MAX_INPUTS")
        if type(self.max_outputs) is not int or not 1 <= self.max_outputs <= 256:
            raise ValueError("POLICY_MAX_OUTPUTS")


@dataclass(frozen=True)
class SignerCapabilities:
    kind: str  # "software", "offline", "hardware", or "fixture"
    supports_networks: tuple[str, ...]
    production: bool

    def validate(self) -> None:
        if self.kind not in ("software", "offline", "hardware", "fixture"):
            raise ValueError("CAPABILITY_KIND")
        if (
            not self.supports_networks
            or any(n not in ("regtest", "testnet", "mainnet") for n in self.supports_networks)
        ):
            raise ValueError("CAPABILITY_NETWORK")
        if type(self.production) is not bool:
            raise ValueError("CAPABILITY_PRODUCTION")


@dataclass(frozen=True)
class SignedResult:
    request_id: str
    tx_digest: str
    envelope: bytes
