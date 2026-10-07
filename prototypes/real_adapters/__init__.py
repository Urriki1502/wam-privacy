"""Phase 12 adapters that bind privacy policy to the qualified WSP/WAM runtime."""

from .wam import (
    AdapterError,
    WspPsbtSignerProvider,
    core_v0_psbt,
    make_local_wam_rpc,
    request_id_from_psbt,
    sign_request_from_psbt,
)

__all__ = [
    "AdapterError",
    "WspPsbtSignerProvider",
    "core_v0_psbt",
    "make_local_wam_rpc",
    "request_id_from_psbt",
    "sign_request_from_psbt",
]
