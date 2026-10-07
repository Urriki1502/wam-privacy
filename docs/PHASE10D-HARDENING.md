# Phase 10D — Protocol Hardening and Context Binding

**Status:** under qualification.

Phase 10D creates a hardened successor to the Phase 10B/10C research profile without rewriting the historical baseline.

## Hardened public relation

The new fixed 2×2 relation exposes:

1. shared input commitment-tree root;
2. input 0 nullifier;
3. input 1 nullifier;
4. output 0 note commitment;
5. output 1 note commitment;
6. fee;
7. transparent input amount;
8. transparent output amount;
9. protocol/network/transaction context digest.

### Authority privacy correction

Phase 10B exposed one deterministic authority tag per input as a public instance. If the same spend authority were reused, that value could become a cross-note linkage identifier.

Phase 10D removes authority tags from the public relation. Spend authority is still derived inside the circuit and is still bound into the exact anchored note commitment and nullifier relation, but the tag itself is not revealed to the verifier.

## Value balance

The hardened circuit proves:

```
sum(shielded_inputs) + transparent_in
=
sum(shielded_outputs) + transparent_out + fee
```

All values remain 64-bit and capped by the exact WAM monetary maximum.

## Context binding

A public context digest binds:

- protocol version;
- WAM network id;
- hardened circuit id;
- outer transaction digest;
- transparent input;
- transparent output;
- fee.

The verifier recomputes this digest from the expected context. Replaying an otherwise valid proof under another network, transaction digest, or transparent balance is rejected.

## Verifying-key identity

The hardened envelope derives its 32-byte VK identifier from Halo2's pinned verification-key representation under a WAM-specific domain separator. The Halo2 dependency version is pinned by the build profile; a dependency/circuit change is therefore an explicit qualification trigger.

## Boundary

Phase 10D does not yet define the final shielded key hierarchy, note encryption, production tree depth, WAM transaction serialization, or Core consensus activation. Those remain later gates.

## Exit gate

- authority tags absent from public instances;
- transparent/shielded conservation enforced in-circuit;
- context replay across network/transaction/value balance rejected;
- deterministic VK identity verified;
- real proof accepted only under the exact context;
- all prior regressions remain green.
