# Security Policy

This repository contains defensive security research, specifications, local prototypes, and validation work for WAM privacy technology.

## Research boundary

Development and validation in this repository should use:

- local fixtures;
- mocked RPC responses;
- synthetic transactions;
- deterministic test vectors;
- isolated regtest or testnet environments;
- repository-owned CI.

Do not use this repository as authorization to probe, disrupt, exploit, or stress public infrastructure or third-party systems.

## Sensitive material

Never commit:

- wallet seeds;
- real private spend keys;
- exchange/API credentials;
- production node credentials;
- treasury keys;
- release-signing secrets;
- personally identifying wallet datasets.

Tests should use deterministic non-production fixtures created specifically for testing.

## Vulnerability handling

If a finding could affect live WAM funds, consensus integrity, private keys, or currently deployed infrastructure:

1. do not publish weaponized reproduction steps;
2. preserve a minimal local regression test where safe;
3. report the issue privately to the relevant WAM maintainer;
4. publish details only after remediation or explicit maintainer approval.

## Cryptography policy

Prefer established, reviewed constructions and upstream specifications.

Custom cryptographic constructions require an explicit written rationale, independent review, dedicated test vectors, and a separate approval gate before production consideration.

## Scope distinction

A passing prototype or CI suite demonstrates behavior under the tested model. It does **not** by itself establish production security, anonymity, consensus safety, or cryptographic soundness.
