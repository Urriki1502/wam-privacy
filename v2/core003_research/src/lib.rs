//! CORE-003 reference-only gate for exact, ordered, canonical commitment roots.
//!
//! Uses the *actual frozen V1* Poseidon pair and TREE_DEPTH / zero-padding
//! conventions. Does not modify or hook CoreShieldedState, wallets, consensus
//! code, RPC or live chains. No proof verification lives in this crate.
//! A passing test is NOT closure of CORE-003 for production.

#![forbid(unsafe_code)]

use ff::PrimeField;
use halo2_proofs::pasta::Fp;
use std::collections::HashSet;
use wam_privacy_halo2_prototype::anchor::{poseidon_pair, TREE_DEPTH};

const CAPACITY: usize = 1usize << TREE_DEPTH;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RootGateError {
    EmptyAppend,
    CapacityExceeded,
    NonCanonicalCommitment,
    DuplicateCommitment,
    NonCanonicalClaimedRoot,
    ForgedClaimedRoot,
    InvalidRollbackPosition,
}

fn canonical_fp(raw: [u8; 32]) -> Option<Fp> {
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(&raw);
    Option::<Fp>::from(Fp::from_repr(repr))
}

fn canonical_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

/// Explicit leaves preserve append order. V1 Core's HashSet alone cannot do so.
fn root_of(leaves: &[[u8; 32]]) -> Result<[u8; 32], RootGateError> {
    if leaves.len() > CAPACITY {
        return Err(RootGateError::CapacityExceeded);
    }
    let mut level = vec![Fp::zero(); CAPACITY];
    for (slot, raw) in level.iter_mut().zip(leaves) {
        *slot = canonical_fp(*raw).ok_or(RootGateError::NonCanonicalCommitment)?;
    }
    for _ in 0..TREE_DEPTH {
        let mut parents = Vec::with_capacity(level.len() / 2);
        for children in level.chunks_exact(2) {
            parents.push(poseidon_pair(children[0], children[1]));
        }
        level = parents;
    }
    Ok(canonical_bytes(level[0]))
}

/// Local model, not a chain-state implementation or consensus verification API.
#[derive(Clone, Debug, Default)]
pub struct OrderedRootGate {
    ordered_commitments: Vec<[u8; 32]>,
}

impl OrderedRootGate {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn commitment_count(&self) -> usize {
        self.ordered_commitments.len()
    }

    pub fn current_root(&self) -> Result<[u8; 32], RootGateError> {
        root_of(&self.ordered_commitments)
    }

    fn prepare(&self, new_commitments: &[[u8; 32]])
        -> Result<Vec<[u8; 32]>, RootGateError>
    {
        if new_commitments.is_empty() {
            return Err(RootGateError::EmptyAppend);
        }
        if self.ordered_commitments.len().checked_add(new_commitments.len())
            .is_none_or(|total| total > CAPACITY)
        {
            return Err(RootGateError::CapacityExceeded);
        }

        let mut seen: HashSet<[u8; 32]> = self.ordered_commitments.iter().copied().collect();
        let mut candidate = self.ordered_commitments.clone();
        for raw in new_commitments {
            if canonical_fp(*raw).is_none() {
                return Err(RootGateError::NonCanonicalCommitment);
            }
            if !seen.insert(*raw) {
                return Err(RootGateError::DuplicateCommitment);
            }
            candidate.push(*raw);
        }
        Ok(candidate)
    }

    /// For local fixtures only: compute the root that the proposed gate expects.
    /// Production Core must compute from independently authenticated proof
    /// transitions and a consensus-approved commitment tree.
    pub fn expected_after_append(
        &self, new_commitments: &[[u8; 32]]
    ) -> Result<[u8; 32], RootGateError> {
        root_of(&self.prepare(new_commitments)?)
    }

    /// Only publishes state once EVERY validity + root check has passed.
    pub fn verify_and_append(
        &mut self,
        new_commitments: &[[u8; 32]],
        claimed_root: [u8; 32],
    ) -> Result<(), RootGateError> {
        let candidate = self.prepare(new_commitments)?;
        // Canonical alone is intentionally insufficient.
        if canonical_fp(claimed_root).is_none() {
            return Err(RootGateError::NonCanonicalClaimedRoot);
        }
        let expected = root_of(&candidate)?;
        if claimed_root != expected {
            return Err(RootGateError::ForgedClaimedRoot);
        }
        self.ordered_commitments = candidate;
        Ok(())
    }

    /// Deterministic rollback fixture only; no chain-tip/hash authorization
    /// and no crash-safe persistence. This MUST NOT be treated as Core undo.
    pub fn rewind_for_fixture(&mut self, count: usize) -> Result<(), RootGateError> {
        if count > self.ordered_commitments.len() {
            return Err(RootGateError::InvalidRollbackPosition);
        }
        self.ordered_commitments.truncate(count);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wam_privacy_halo2_prototype::anchor::merkle_root;

    fn field(n: u64) -> [u8; 32] {
        canonical_bytes(Fp::from(n))
    }

    fn append_valid(gate: &mut OrderedRootGate, values: &[[u8; 32]]) {
        let expected = gate.expected_after_append(values).expect("model root");
        gate.verify_and_append(values, expected).expect("valid append");
    }

    #[test]
    fn one_commitment_root_matches_frozen_v1_merkle_membership() {
        let mut gate = OrderedRootGate::new();
        append_valid(&mut gate, &[field(7)]);
        let z1 = poseidon_pair(Fp::zero(), Fp::zero());
        let z2 = poseidon_pair(z1, z1);
        let z3 = poseidon_pair(z2, z2);
        let expected = merkle_root(
            Fp::from(7),
            [Fp::zero(), z1, z2, z3],
            [false; TREE_DEPTH],
        );
        assert_eq!(gate.current_root().unwrap(), canonical_bytes(expected));
    }

    #[test]
    fn forged_but_canonical_root_is_rejected_without_partial_mutation() {
        let mut gate = OrderedRootGate::new();
        let original_root = gate.current_root().unwrap();
        let expected = gate.expected_after_append(&[field(7)]).unwrap();
        let forged = field(42);
        assert_ne!(expected, forged);
        assert_eq!(
            gate.verify_and_append(&[field(7)], forged),
            Err(RootGateError::ForgedClaimedRoot)
        );
        assert_eq!(gate.current_root().unwrap(), original_root);
        assert_eq!(gate.commitment_count(), 0);
        append_valid(&mut gate, &[field(7)]);
    }

    #[test]
    fn noncanonical_root_and_commitment_rejected() {
        let mut gate = OrderedRootGate::new();
        assert_eq!(
            gate.verify_and_append(&[field(3)], [0xff; 32]),
            Err(RootGateError::NonCanonicalClaimedRoot)
        );
        assert_eq!(
            gate.verify_and_append(&[[0xff; 32]], field(3)),
            Err(RootGateError::NonCanonicalCommitment)
        );
        assert_eq!(gate.commitment_count(), 0);
    }

    #[test]
    fn append_order_matters_and_reordered_root_cannot_be_reused() {
        let mut gate = OrderedRootGate::new();
        let correct = gate.expected_after_append(&[field(1), field(2)]).unwrap();
        let reversed = gate.expected_after_append(&[field(2), field(1)]).unwrap();
        assert_ne!(correct, reversed);
        assert_eq!(
            gate.verify_and_append(&[field(1), field(2)], reversed),
            Err(RootGateError::ForgedClaimedRoot)
        );
        assert_eq!(gate.commitment_count(), 0);
        gate.verify_and_append(&[field(1), field(2)], correct).unwrap();
    }

    #[test]
    fn repeated_commits_and_duplicate_input_are_rejected_atomically() {
        let mut gate = OrderedRootGate::new();
        append_valid(&mut gate, &[field(10)]);
        let old = gate.current_root().unwrap();
        assert_eq!(
            gate.expected_after_append(&[field(20), field(10)]),
            Err(RootGateError::DuplicateCommitment)
        );
        assert_eq!(
            gate.expected_after_append(&[field(20), field(20)]),
            Err(RootGateError::DuplicateCommitment)
        );
        assert_eq!(gate.current_root().unwrap(), old);
        assert_eq!(gate.commitment_count(), 1);
    }

    #[test]
    fn depth_four_capacity_limit_is_enforced() {
        let mut gate = OrderedRootGate::new();
        let leaves: Vec<[u8; 32]> = (1..=16).map(field).collect();
        append_valid(&mut gate, &leaves);
        assert_eq!(gate.commitment_count(), 16);
        assert_eq!(
            gate.expected_after_append(&[field(17)]),
            Err(RootGateError::CapacityExceeded)
        );
    }

    #[test]
    fn empty_append_is_invalid() {
        let mut gate = OrderedRootGate::new();
        let unchanged_root = gate.current_root().unwrap();
        assert_eq!(
            gate.verify_and_append(&[], unchanged_root),
            Err(RootGateError::EmptyAppend)
        );
    }

    #[test]
    fn batch_and_sequential_append_converge() {
        let values = [field(8), field(9), field(11), field(12)];
        let mut batched = OrderedRootGate::new();
        append_valid(&mut batched, &values);
        let mut incremental = OrderedRootGate::new();
        for v in values {
            append_valid(&mut incremental, &[v]);
        }
        assert_eq!(batched.current_root(), incremental.current_root());
    }

    #[test]
    fn fixture_rollback_and_canonical_history_replay_converge() {
        let mut gate = OrderedRootGate::new();
        append_valid(&mut gate, &[field(1), field(2)]);
        let prior = gate.current_root().unwrap();
        append_valid(&mut gate, &[field(3)]);
        gate.rewind_for_fixture(2).unwrap();
        assert_eq!(gate.current_root().unwrap(), prior);
        append_valid(&mut gate, &[field(4)]);
        let mut replay = OrderedRootGate::new();
        append_valid(&mut replay, &[field(1), field(2), field(4)]);
        assert_eq!(gate.current_root(), replay.current_root());
        assert_eq!(
            gate.rewind_for_fixture(8),
            Err(RootGateError::InvalidRollbackPosition)
        );
    }
}
