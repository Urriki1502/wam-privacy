# V2-03 — Offline privacy-routing and metadata observer fixtures

**Status:** experimental wallet/application-layer simulator. NOT a deployed relay
or proof of network anonymity. Built on V2-01/02 research, V1 pinned source
95dfe0abf04b4e4dcbdbe9eb6d9bd0439a45a127 unchanged.

## Scope and threat model

- Deterministic synthetic TOR/I2P/DIRECT **policy route names**, no sockets,
  process spawning, real networks, Tor/I2P clients or outbound transactions.
- Only synthetic requests with action BROADCAST, network_id and txid enter
  the simulator. Seed, viewing keys, scanner data, account identifiers,
  key material or raw transactions are deliberately NOT inputs.
- Strict privacy-required route cannot select DIRECT and will fail closed
  if the available private policy routes disappear. Explicit direct transport
  requires privacy_required=False and allow_direct=True.
- Scanner-RPC and broadcast endpoint roles remain distinct. Cross-role
  credential reuse is always denied. Shared operator/provider is denied by
  default, or explicitly WARN if the caller accepts correlation leakage.
- Simulated observers include first hop, RPC provider, broadcast peer, public
  chain observer and global observer. Synthetic trace schemas identify
  which *classes* of metadata are visible and what correlation risk remains.
- No claims that Tor/I2P guarantee IP/timing unlinkability or prevent global
  traffic correlation. OHTTP transport is not a generic WAM broadcast route
  in this prototype; requires a specified compatible RPC/runtime adapter.

## Adversarial acceptance

- NET-001: unavailable private routes never silently fall back to DIRECT.
- NET-002: shared provider explicitly reported and DENY/WARN according to
  policy; shared cross-role credentials always DENY.
- NET-003: broadcast-request allowlist rejects seed, scanning credentials,
  account details, full wallet exports, raw tx or other unsolicited fields.
- NET-004: observers see residual metadata fields, including first-hop
  source IP/timing and public-chain information. The comparative report
  never returns source IP, timestamp, txid or synthetic credential values.
- Additional parser/DoS bounds, malformed input, deterministic tie-breaking
  and no raw metadata in decision events are verified.

## Limitations and integration gate

- Route selection says SELECTED_POLICY_ONLY, not actual delivery/broadcast,
  anonymity, cryptographic validation or independent real-world measurements.
- No real WAM Core, consensus, signing, RPC, network integration or crypto
  modifications. Maintaining transparency and immutability is non-negotiable.
- Provider identity independence cannot be inferred from endpoint labels in
  the real world. Operator mapping and shared upstream access must be
  validated by future audited adapters.
- No operator uptime/performance measurement and no first-relay cryptographic
  origin protection are implemented.
- Live relay integration / OHTTP adoption is outside this phase and requires
  WAM maintainer confirmation per the existing design compatibility gate.
- V2-04 remains the wallet/regtest integration and negative-case bridge.

**No merging into main by this PR.** Keep stacked PR Draft until CI, frozen V1
regressions, architecture review and decision log are complete.
