"""Phase 3 signer-abstraction reference contract."""

from .model import (
    Approval,
    PaymentIntent,
    SignedResult,
    SignRequest,
    SignerCapabilities,
    SignerPolicy,
    TransactionOutput,
)
from .provider import (
    FixtureSigner,
    ProviderError,
    SignerGate,
    SigningProvider,
    redacted_signer_event,
)

__all__ = [
    "Approval",
    "PaymentIntent",
    "SignedResult",
    "SignRequest",
    "SignerCapabilities",
    "SignerPolicy",
    "TransactionOutput",
    "FixtureSigner",
    "ProviderError",
    "SignerGate",
    "SigningProvider",
    "redacted_signer_event",
]
