# Upstream References

These projects are references, not drop-in dependencies or claims of compatibility.

## Bitcoin

- BIP 352 — Silent Payments  
  https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki

- BIP 78 — A Simple Payjoin Proposal  
  https://github.com/bitcoin/bips/blob/master/bip-0078.mediawiki

- BIP 77 — Async Payjoin  
  https://github.com/bitcoin/bips/blob/master/bip-0077.mediawiki

## Monero

Relevant design lesson: explicit separation of private view capability and private spend authority.

- Monero private-key documentation  
  https://docs.getmonero.org/cryptography/asymmetric/private-key/

- Monero wallet RPC documentation  
  https://docs.getmonero.org/rpc-library/wallet-rpc/

WAM does not assume Monero's curve, stealth-address construction, RingCT model, or transaction format.

## Zcash

Relevant research lessons: shielded value pools, notes, commitments, nullifiers, viewing capabilities, proof-system engineering, and supply-integrity discipline.

- ZIP 224 — Orchard Shielded Protocol  
  https://zips.z.cash/zip-0224

- Orchard design documentation  
  https://zcash.github.io/orchard/

- Halo 2 documentation  
  https://zcash.github.io/halo2/

- Zcash protocol specification  
  https://zips.z.cash/protocol/protocol.pdf

## Reference policy

Before implementing against any upstream protocol:

1. record the exact upstream version or commit;
2. identify WAM-specific deviations;
3. create deterministic compatibility vectors;
4. avoid silently changing cryptographic domain separation or serialization;
5. treat upstream status changes as review triggers.
