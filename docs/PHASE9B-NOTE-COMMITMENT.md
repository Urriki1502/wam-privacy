# Phase 9B — In-Circuit Note Commitment Derivation

## Objective

Phase 9A proved composition using one precomputed `note_identity` witness.

Phase 9B removes that trust boundary. The identity is now derived inside the circuit from private note fields before it is consumed by the anchor and nullifier branches.

## Private note fields

- value;
- recipient tag;
- spend secret / authority;
- rho;
- rseed;
- Merkle authentication path.

## Circuit-native note identity

The research encoding is:

```
authority_tag = Poseidon(AUTHORITY_DOMAIN, spend_secret)

h0 = Poseidon(NOTE_DOMAIN, value)
h1 = Poseidon(h0, recipient_tag)
h2 = Poseidon(h1, authority_tag)
h3 = Poseidon(h2, rho)
note_identity = Poseidon(h3, rseed)
```

The exact resulting cell is then used in:

```
root = MerklePoseidon(note_identity, path)

note_key = Poseidon(spend_secret, note_identity)
nullifier = Poseidon(NULLIFIER_DOMAIN, note_key)
```

No second note-identity witness exists.

## Amount constraints

The private note value is constrained to:

```
1 <= value <= MAX_WAM_ATOMS
```

using:

- 64-bit boolean decomposition;
- exact monetary-cap slack;
- a constrained `value - 1` witness to reject zero.

Tests cover:

- ordinary valid value;
- exact WAM cap;
- zero value;
- cap + 1.

## Mutation coverage

Against the original public root/tag/nullifier relation, the circuit rejects changes to:

- value;
- recipient tag;
- spend secret;
- rho;
- rseed.

Distinct rho or rseed also yields a distinct native note identity.

## Real proof

The suite creates and verifies a real Halo2 proof for the note-derived action.

The same proof fails verification when any public instance is modified:

- commitment root;
- authority tag;
- nullifier.

## Remaining boundary

This is still a circuit-native research note encoding. It does not define:

- final WAM note serialization;
- note encryption;
- viewing-key cryptography;
- canonical recipient encoding;
- consensus verifier integration;
- production proving parameters.

The next composition step is to integrate shielded value conservation with the anchored-spend action.

## Claim

`PHASE 9B INTERNAL NOTE-COMMITMENT PASS`

No audit, production, consensus, anonymity, or mainnet claim is implied.
