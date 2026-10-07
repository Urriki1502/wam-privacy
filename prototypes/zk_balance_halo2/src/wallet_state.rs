//! Phase 12: shielded wallet scanning, witness maintenance and reorg recovery.
//!
//! The scanner intentionally receives only an IncomingViewingKey. It has no
//! spend-authority material. It consumes canonical encrypted-note records,
//! tracks the research commitment tree, and derives witnesses on demand.

use std::collections::HashSet;

use ff::PrimeField;
use halo2_proofs::pasta::Fp;

use crate::{
    anchor::{merkle_root, poseidon_pair, TREE_DEPTH},
    note_action::note_identity,
    note_encryption::{EncryptedNote, IncomingViewingKey, NoteAad, NotePlaintext},
};

const TREE_CAPACITY: usize = 1usize << TREE_DEPTH;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum WalletStateError {
    HeightMismatch,
    ParentMismatch,
    NetworkMismatch,
    DuplicateOutput,
    DuplicateCommitment,
    TreeFull,
    InvalidCommitment,
    InvalidCiphertext,
    UnknownRollbackHeight,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ShieldedOutputRecord {
    pub aad: NoteAad,
    pub encrypted_note: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ShieldedBlock {
    pub height: u64,
    pub hash: [u8; 32],
    pub prev_hash: [u8; 32],
    pub outputs: Vec<ShieldedOutputRecord>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WalletNote {
    pub plaintext: NotePlaintext,
    pub commitment: [u8; 32],
    pub position: usize,
    pub block_height: u64,
    pub block_hash: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NoteWitness {
    pub position: usize,
    pub root: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct BlockMeta {
    height: u64,
    hash: [u8; 32],
    commitments_after: usize,
    output_ids_after: usize,
}

#[derive(Clone)]
pub struct WalletScanner {
    incoming: IncomingViewingKey,
    network_id: u32,
    chain: Vec<BlockMeta>,
    commitments: Vec<Fp>,
    commitment_bytes: Vec<[u8; 32]>,
    output_ids: Vec<([u8; 32], u32)>,
    notes: Vec<WalletNote>,
}

impl WalletScanner {
    pub fn new(incoming: IncomingViewingKey, network_id: u32) -> Self {
        Self {
            incoming,
            network_id,
            chain: Vec::new(),
            commitments: Vec::new(),
            commitment_bytes: Vec::new(),
            output_ids: Vec::new(),
            notes: Vec::new(),
        }
    }

    pub fn notes(&self) -> &[WalletNote] {
        &self.notes
    }

    pub fn tip(&self) -> Option<(u64, [u8; 32])> {
        self.chain.last().map(|b| (b.height, b.hash))
    }

    pub fn commitment_count(&self) -> usize {
        self.commitments.len()
    }

    pub fn root(&self) -> Fp {
        build_levels(&self.commitments)
            .last()
            .expect("tree has root level")[0]
    }

    pub fn process_block(&mut self, block: ShieldedBlock) -> Result<(), WalletStateError> {
        let mut candidate = self.clone();
        candidate.apply_block(block)?;
        *self = candidate;
        Ok(())
    }

    fn apply_block(&mut self, block: ShieldedBlock) -> Result<(), WalletStateError> {
        let expected_height = self.chain.last().map_or(0, |b| b.height + 1);
        let expected_parent = self.chain.last().map_or([0u8; 32], |b| b.hash);
        if block.height != expected_height {
            return Err(WalletStateError::HeightMismatch);
        }
        if block.prev_hash != expected_parent {
            return Err(WalletStateError::ParentMismatch);
        }
        if self.commitments.len() + block.outputs.len() > TREE_CAPACITY {
            return Err(WalletStateError::TreeFull);
        }

        let mut local_ids = HashSet::new();
        let mut local_commitments = HashSet::new();

        for record in &block.outputs {
            if record.aad.network_id != self.network_id {
                return Err(WalletStateError::NetworkMismatch);
            }

            let output_id = (record.aad.transaction_digest, record.aad.output_index);
            if !local_ids.insert(output_id) || self.output_ids.contains(&output_id) {
                return Err(WalletStateError::DuplicateOutput);
            }

            if !local_commitments.insert(record.aad.note_commitment)
                || self.commitment_bytes.contains(&record.aad.note_commitment)
            {
                return Err(WalletStateError::DuplicateCommitment);
            }

            let commitment = fp_from_bytes(record.aad.note_commitment)
                .ok_or(WalletStateError::InvalidCommitment)?;
            let encrypted = EncryptedNote::decode(&record.encrypted_note)
                .map_err(|_| WalletStateError::InvalidCiphertext)?;

            let position = self.commitments.len();
            self.commitments.push(commitment);
            self.commitment_bytes.push(record.aad.note_commitment);
            self.output_ids.push(output_id);

            if let Ok(note) = self.incoming.decrypt(&encrypted, &record.aad) {
                let recomputed = note_identity(
                    note.value,
                    note.recipient_tag,
                    note.spend_authority_tag,
                    note.rho,
                    note.rseed,
                );
                if fp_to_bytes(recomputed) == record.aad.note_commitment {
                    self.notes.push(WalletNote {
                        plaintext: note,
                        commitment: record.aad.note_commitment,
                        position,
                        block_height: block.height,
                        block_hash: block.hash,
                    });
                }
            }
        }

        self.chain.push(BlockMeta {
            height: block.height,
            hash: block.hash,
            commitments_after: self.commitments.len(),
            output_ids_after: self.output_ids.len(),
        });
        Ok(())
    }

    pub fn witness_for(&self, commitment: [u8; 32]) -> Option<NoteWitness> {
        let note = self.notes.iter().find(|n| n.commitment == commitment)?;
        let levels = build_levels(&self.commitments);
        let mut index = note.position;
        let mut siblings = [Fp::zero(); TREE_DEPTH];
        let mut directions = [false; TREE_DEPTH];

        for level in 0..TREE_DEPTH {
            siblings[level] = levels[level][index ^ 1];
            directions[level] = index & 1 == 1;
            index >>= 1;
        }

        let root = levels[TREE_DEPTH][0];
        debug_assert_eq!(
            merkle_root(
                fp_from_bytes(commitment).expect("recognized note is canonical"),
                siblings,
                directions,
            ),
            root
        );

        Some(NoteWitness {
            position: note.position,
            root,
            siblings,
            directions,
        })
    }

    pub fn rollback_to(&mut self, height: Option<u64>) -> Result<(), WalletStateError> {
        match height {
            None => {
                self.chain.clear();
                self.commitments.clear();
                self.commitment_bytes.clear();
                self.output_ids.clear();
                self.notes.clear();
                Ok(())
            }
            Some(target) => {
                let index = self
                    .chain
                    .iter()
                    .position(|b| b.height == target)
                    .ok_or(WalletStateError::UnknownRollbackHeight)?;
                let commitments_after = self.chain[index].commitments_after;
                let output_ids_after = self.chain[index].output_ids_after;
                self.chain.truncate(index + 1);
                self.commitments.truncate(commitments_after);
                self.commitment_bytes.truncate(commitments_after);
                self.output_ids.truncate(output_ids_after);
                self.notes.retain(|note| note.block_height <= target);
                Ok(())
            }
        }
    }

    pub fn rescan(
        incoming: IncomingViewingKey,
        network_id: u32,
        blocks: &[ShieldedBlock],
    ) -> Result<Self, WalletStateError> {
        let mut scanner = Self::new(incoming, network_id);
        for block in blocks {
            scanner.process_block(block.clone())?;
        }
        Ok(scanner)
    }
}

fn fp_to_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

fn fp_from_bytes(raw: [u8; 32]) -> Option<Fp> {
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(&raw);
    Option::<Fp>::from(Fp::from_repr(repr))
}

fn build_levels(leaves: &[Fp]) -> Vec<Vec<Fp>> {
    let mut level = vec![Fp::zero(); TREE_CAPACITY];
    for (slot, value) in level.iter_mut().zip(leaves) {
        *slot = *value;
    }

    let mut levels = vec![level.clone()];
    for _ in 0..TREE_DEPTH {
        let mut next = Vec::with_capacity(level.len() / 2);
        for pair in level.chunks_exact(2) {
            next.push(poseidon_pair(pair[0], pair[1]));
        }
        levels.push(next.clone());
        level = next;
    }
    levels
}
