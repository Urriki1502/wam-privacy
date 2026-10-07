# Phase 12 — Real WAM/WSP Adapters

**Status:** under qualification.

Phase 12 begins replacing fixture-only boundaries with the already-qualified WSP/WAM transaction implementation.

## Qualified dependency

The adapter is pinned in CI to:

`Urriki1502/wam-silent-payments@dcf1aecc00a64bfad3151fa202c3e07d47d83e69`

## Implemented boundary

The Phase 12 adapter:

- parses canonical WSP PSBT bytes;
- derives signer-visible outputs, fee and transaction digest from those bytes;
- derives a stable replay identifier from canonical PSBT bytes, network and change-script classification;
- rejects caller-selected request-id rotation;
- delegates signing to the WSP real P2TR/Schnorr implementation;
- verifies finalization before returning a signed envelope;
- exports the verified result through the WSP Core-v0 adapter;
- constructs only the qualified loopback RPC boundary;
- refuses mainnet signing in this research profile.

## Security boundary

Change ownership remains an explicit trusted-wallet input to the adapter. A later production wallet integration must derive that ownership from authenticated wallet derivation state rather than arbitrary UI or network input.

The adapter does not turn the Phase 12 research stack into a production wallet.

## Exit evidence

Phase 12 requires:

- canonical PSBT round-trip;
- stable request-id binding;
- real Schnorr signing through the Phase 3 signer gate;
- Core-v0 export after verified finalization;
- mutation rejection;
- signed-PSBT reinterpretation rejection;
- loopback-only RPC construction;
- full prior-phase regression pass.

No mainnet claim is implied.
