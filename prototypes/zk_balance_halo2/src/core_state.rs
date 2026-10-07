//! Phase 13C: atomic shielded-state and reorg model for Core integration.
//!
//! State mutation consumes only metadata extracted from an already verified
//! Phase 10D hardened proof. Callers cannot provide nullifiers, output
//! commitments, or the input anchor independently of the proof envelope.
//!
//! This remains a regtest/research state engine. The next anchor is supplied by
//! the higher-level commitment-tree integration layer and is required to be a
//! canonical Pasta field encoding. Production Core must derive that root from
//! canonical shielded outputs rather than accept it from an RPC caller.

use std::collections::HashSet;

use ff::PrimeField;
use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::VerifyingKey,
    poly::commitment::Params,
};

use crate::{
    context::ProofContext,
    serialization_v2::{
        verify_hardened_bundle_envelope_and_decode, HardenedEnvelopeError,
    },
    MAX_WAM_ATOMS,
};

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CoreStateError {
    Envelope(HardenedEnvelopeError),
    InitialPoolRange,
    NonCanonicalAnchor,
    EmptyBlock,
    HeightMismatch,
    ParentMismatch,
    AnchorMismatch,
    DuplicateNullifier,
    DuplicateCommitment,
    PoolOverflow,
    PoolUnderflow,
    TipMismatch,
    UnknownRollbackHeight,
}

impl From<HardenedEnvelopeError> for CoreStateError {
    fn from(value: HardenedEnvelopeError) -> Self {
        Self::Envelope(value)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VerifiedTransition {
    pub anchor: [u8; 32],
    pub nullifiers: [[u8; 32]; 2],
    pub output_commitments: [[u8; 32]; 2],
    pub transparent_in: u64,
    pub transparent_out: u64,
    pub fee: u64,
    pub context_digest: [u8; 32],
}

impl VerifiedTransition {
    pub fn from_verified_envelope(
        params: &Params<EqAffine>,
        vk: &VerifyingKey<EqAffine>,
        context: &ProofContext,
        encoded: &[u8],
    ) -> Result<Self, CoreStateError> {
        let envelope =
            verify_hardened_bundle_envelope_and_decode(params, vk, context, encoded)?;

        Ok(Self {
            anchor: fp_bytes(envelope.public_inputs[0]),
            nullifiers: [
                fp_bytes(envelope.public_inputs[1]),
                fp_bytes(envelope.public_inputs[2]),
            ],
            output_commitments: [
                fp_bytes(envelope.public_inputs[3]),
                fp_bytes(envelope.public_inputs[4]),
            ],
            fee: context.fee,
            transparent_in: context.transparent_in,
            transparent_out: context.transparent_out,
            context_digest: fp_bytes(envelope.public_inputs[8]),
        })
    }

    #[cfg(test)]
    fn model(
        anchor: [u8; 32],
        nullifiers: [[u8; 32]; 2],
        output_commitments: [[u8; 32]; 2],
        transparent_in: u64,
        transparent_out: u64,
        fee: u64,
    ) -> Self {
        Self {
            anchor,
            nullifiers,
            output_commitments,
            transparent_in,
            transparent_out,
            fee,
            context_digest: [0u8; 32],
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StateBlock {
    pub height: u64,
    pub hash: [u8; 32],
    pub prev_hash: [u8; 32],
    pub next_anchor: [u8; 32],
    pub transitions: Vec<VerifiedTransition>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct UndoRecord {
    height: u64,
    hash: [u8; 32],
    previous_height: Option<u64>,
    previous_hash: [u8; 32],
    previous_anchor: [u8; 32],
    previous_pool_atoms: u64,
    added_nullifiers: Vec<[u8; 32]>,
    added_commitments: Vec<[u8; 32]>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoreShieldedState {
    tip_height: Option<u64>,
    tip_hash: [u8; 32],
    current_anchor: [u8; 32],
    nullifiers: HashSet<[u8; 32]>,
    commitments: HashSet<[u8; 32]>,
    pool_atoms: u64,
    history: Vec<UndoRecord>,
}

impl CoreShieldedState {
    pub fn new(initial_anchor: [u8; 32], initial_pool_atoms: u64) -> Result<Self, CoreStateError> {
        if initial_pool_atoms > MAX_WAM_ATOMS {
            return Err(CoreStateError::InitialPoolRange);
        }
        require_canonical_fp(initial_anchor)?;

        Ok(Self {
            tip_height: None,
            tip_hash: [0u8; 32],
            current_anchor: initial_anchor,
            nullifiers: HashSet::new(),
            commitments: HashSet::new(),
            pool_atoms: initial_pool_atoms,
            history: Vec::new(),
        })
    }

    pub fn tip(&self) -> Option<(u64, [u8; 32])> {
        self.tip_height.map(|height| (height, self.tip_hash))
    }

    pub fn current_anchor(&self) -> [u8; 32] {
        self.current_anchor
    }

    pub fn pool_atoms(&self) -> u64 {
        self.pool_atoms
    }

    pub fn nullifier_count(&self) -> usize {
        self.nullifiers.len()
    }

    pub fn commitment_count(&self) -> usize {
        self.commitments.len()
    }

    pub fn apply_block(&mut self, block: StateBlock) -> Result<(), CoreStateError> {
        // Transactional semantics: mutate a clone first and publish only after
        // every transition and aggregate state invariant has passed.
        let mut candidate = self.clone();
        candidate.apply_block_inner(block)?;
        *self = candidate;
        Ok(())
    }

    fn apply_block_inner(&mut self, block: StateBlock) -> Result<(), CoreStateError> {
        if block.transitions.is_empty() {
            return Err(CoreStateError::EmptyBlock);
        }
        require_canonical_fp(block.next_anchor)?;

        let expected_height = self.tip_height.map_or(0, |height| height + 1);
        if block.height != expected_height {
            return Err(CoreStateError::HeightMismatch);
        }
        if block.prev_hash != self.tip_hash {
            return Err(CoreStateError::ParentMismatch);
        }

        let mut block_nullifiers = HashSet::new();
        let mut block_commitments = HashSet::new();
        let mut next_pool = self.pool_atoms;

        for transition in &block.transitions {
            if transition.anchor != self.current_anchor {
                return Err(CoreStateError::AnchorMismatch);
            }

            for nullifier in transition.nullifiers {
                if self.nullifiers.contains(&nullifier) || !block_nullifiers.insert(nullifier) {
                    return Err(CoreStateError::DuplicateNullifier);
                }
            }

            for commitment in transition.output_commitments {
                if self.commitments.contains(&commitment)
                    || !block_commitments.insert(commitment)
                {
                    return Err(CoreStateError::DuplicateCommitment);
                }
            }

            next_pool = next_pool
                .checked_add(transition.transparent_in)
                .ok_or(CoreStateError::PoolOverflow)?;
            if next_pool > MAX_WAM_ATOMS {
                return Err(CoreStateError::PoolOverflow);
            }
            next_pool = next_pool
                .checked_sub(transition.transparent_out)
                .ok_or(CoreStateError::PoolUnderflow)?;
            next_pool = next_pool
                .checked_sub(transition.fee)
                .ok_or(CoreStateError::PoolUnderflow)?;
        }

        let added_nullifiers: Vec<_> = block_nullifiers.into_iter().collect();
        let added_commitments: Vec<_> = block_commitments.into_iter().collect();

        let undo = UndoRecord {
            height: block.height,
            hash: block.hash,
            previous_height: self.tip_height,
            previous_hash: self.tip_hash,
            previous_anchor: self.current_anchor,
            previous_pool_atoms: self.pool_atoms,
            added_nullifiers: added_nullifiers.clone(),
            added_commitments: added_commitments.clone(),
        };

        self.nullifiers.extend(added_nullifiers);
        self.commitments.extend(added_commitments);
        self.pool_atoms = next_pool;
        self.current_anchor = block.next_anchor;
        self.tip_height = Some(block.height);
        self.tip_hash = block.hash;
        self.history.push(undo);
        Ok(())
    }

    pub fn disconnect_tip(&mut self, expected_hash: [u8; 32]) -> Result<(), CoreStateError> {
        let undo = self.history.last().ok_or(CoreStateError::TipMismatch)?;
        if undo.hash != expected_hash || self.tip_hash != expected_hash {
            return Err(CoreStateError::TipMismatch);
        }

        let undo = self.history.pop().expect("checked non-empty history");
        for nullifier in &undo.added_nullifiers {
            self.nullifiers.remove(nullifier);
        }
        for commitment in &undo.added_commitments {
            self.commitments.remove(commitment);
        }

        self.tip_height = undo.previous_height;
        self.tip_hash = undo.previous_hash;
        self.current_anchor = undo.previous_anchor;
        self.pool_atoms = undo.previous_pool_atoms;
        Ok(())
    }

    pub fn rollback_to(&mut self, height: Option<u64>) -> Result<(), CoreStateError> {
        match height {
            Some(target) => {
                let current = self.tip_height.ok_or(CoreStateError::UnknownRollbackHeight)?;
                if target > current {
                    return Err(CoreStateError::UnknownRollbackHeight);
                }
                while self.tip_height.is_some_and(|tip| tip > target) {
                    let hash = self.tip_hash;
                    self.disconnect_tip(hash)?;
                }
                if self.tip_height != Some(target) {
                    return Err(CoreStateError::UnknownRollbackHeight);
                }
            }
            None => {
                while self.tip_height.is_some() {
                    let hash = self.tip_hash;
                    self.disconnect_tip(hash)?;
                }
            }
        }
        Ok(())
    }
}

fn fp_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

fn require_canonical_fp(raw: [u8; 32]) -> Result<(), CoreStateError> {
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(&raw);
    if Option::<Fp>::from(Fp::from_repr(repr)).is_none() {
        return Err(CoreStateError::NonCanonicalAnchor);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn field(value: u64) -> [u8; 32] {
        fp_bytes(Fp::from(value))
    }

    fn transition(
        anchor: [u8; 32],
        seed: u64,
        transparent_in: u64,
        transparent_out: u64,
        fee: u64,
    ) -> VerifiedTransition {
        VerifiedTransition::model(
            anchor,
            [field(seed * 10 + 1), field(seed * 10 + 2)],
            [field(seed * 10 + 3), field(seed * 10 + 4)],
            transparent_in,
            transparent_out,
            fee,
        )
    }

    fn block(
        state: &CoreShieldedState,
        height: u64,
        hash_seed: u8,
        next_anchor: [u8; 32],
        transitions: Vec<VerifiedTransition>,
    ) -> StateBlock {
        StateBlock {
            height,
            hash: [hash_seed; 32],
            prev_hash: state.tip_hash,
            next_anchor,
            transitions,
        }
    }

    #[test]
    fn block_apply_is_atomic_on_duplicate_nullifier() {
        let anchor = field(100);
        let mut state = CoreShieldedState::new(anchor, 100_000).unwrap();
        let first = transition(anchor, 1, 0, 0, 0);
        let mut second = transition(anchor, 2, 0, 0, 0);
        second.nullifiers[0] = first.nullifiers[0];

        let before = state.clone();
        let candidate = block(&state, 0, 1, field(101), vec![first, second]);
        assert_eq!(
            state.apply_block(candidate),
            Err(CoreStateError::DuplicateNullifier)
        );
        assert_eq!(state, before);
    }

    #[test]
    fn disconnect_restores_exact_prior_state() {
        let anchor = field(200);
        let mut state = CoreShieldedState::new(anchor, 50_000).unwrap();
        let before = state.clone();
        let tx = transition(anchor, 3, 2_000, 1_000, 500);
        let candidate = block(&state, 0, 7, field(201), vec![tx]);

        state.apply_block(candidate).unwrap();
        assert_eq!(state.pool_atoms(), 50_500);
        assert_eq!(state.nullifier_count(), 2);
        assert_eq!(state.commitment_count(), 2);

        state.disconnect_tip([7; 32]).unwrap();
        assert_eq!(state, before);
    }

    #[test]
    fn stale_anchor_and_wrong_parent_fail_without_mutation() {
        let anchor = field(300);
        let mut state = CoreShieldedState::new(anchor, 10_000).unwrap();
        let before = state.clone();

        let stale = transition(field(299), 4, 0, 0, 0);
        let candidate = block(&state, 0, 9, field(301), vec![stale]);
        assert_eq!(
            state.apply_block(candidate),
            Err(CoreStateError::AnchorMismatch)
        );
        assert_eq!(state, before);

        let tx = transition(anchor, 5, 0, 0, 0);
        let mut wrong_parent = block(&state, 0, 10, field(302), vec![tx]);
        wrong_parent.prev_hash = [0xFF; 32];
        assert_eq!(
            state.apply_block(wrong_parent),
            Err(CoreStateError::ParentMismatch)
        );
        assert_eq!(state, before);
    }

    #[test]
    fn pool_accounting_fails_closed() {
        let anchor = field(400);
        let mut state = CoreShieldedState::new(anchor, 100).unwrap();
        let before = state.clone();
        let tx = transition(anchor, 6, 0, 101, 0);
        let candidate = block(&state, 0, 11, field(401), vec![tx]);

        assert_eq!(
            state.apply_block(candidate),
            Err(CoreStateError::PoolUnderflow)
        );
        assert_eq!(state, before);
    }

    #[test]
    fn deep_reorg_300_blocks_restores_and_replays() {
        let genesis_anchor = field(500);
        let mut state = CoreShieldedState::new(genesis_anchor, 1_000_000).unwrap();

        for height in 0..=300u64 {
            let anchor = state.current_anchor();
            let tx = transition(anchor, 1000 + height, 0, 0, 0);
            let candidate = block(
                &state,
                height,
                (height % 251) as u8,
                field(10_000 + height),
                vec![tx],
            );
            state.apply_block(candidate).unwrap();
        }

        let checkpoint_anchor = field(10_000);
        state.rollback_to(Some(0)).unwrap();
        assert_eq!(state.tip().map(|tip| tip.0), Some(0));
        assert_eq!(state.current_anchor(), checkpoint_anchor);
        assert_eq!(state.nullifier_count(), 2);
        assert_eq!(state.commitment_count(), 2);

        for height in 1..=300u64 {
            let anchor = state.current_anchor();
            let tx = transition(anchor, 20_000 + height, 0, 0, 0);
            let candidate = block(
                &state,
                height,
                ((height + 17) % 251) as u8,
                field(30_000 + height),
                vec![tx],
            );
            state.apply_block(candidate).unwrap();
        }

        assert_eq!(state.tip().map(|tip| tip.0), Some(300));
        assert_eq!(state.nullifier_count(), 602);
        assert_eq!(state.commitment_count(), 602);
    }
}
