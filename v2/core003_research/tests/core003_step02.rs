//! CORE-003 Step 02: differential research against the *frozen* V1 WalletScanner.
//!
//! Standalone integration test, staged with the Step 01 reference fixture into
//! a temporary copy of the frozen V1 Rust crate. Does NOT change V1 or Core.
//! WalletScanner is the oracle for its own current experimental 16-leaf tree.
//! This is not an external independent consensus vector or production approval.
#![forbid(unsafe_code)]

#[path = "core003_reference.rs"]
mod step01_reference;

use ff::PrimeField;
use halo2_proofs::pasta::Fp;
use step01_reference::{OrderedRootGate, RootGateError};
use wam_privacy_halo2_prototype::{
    anchor::{merkle_root, TREE_DEPTH},
    note_action::note_identity,
    note_encryption::{encrypt_note, NoteAad, NotePlaintext, ShieldedKeyBundle},
    wallet_state::{ShieldedBlock, ShieldedOutputRecord, WalletScanner, WalletStateError},
};

fn bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut result = [0u8; 32];
    result.copy_from_slice(repr.as_ref());
    result
}

fn from_bytes(raw: [u8; 32]) -> Fp {
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(&raw);
    Option::<Fp>::from(Fp::from_repr(repr)).expect("known canonical commitment")
}

fn fixture_output(wallet: &ShieldedKeyBundle, index: usize) -> ShieldedOutputRecord {
    // Fixed seed, note fields and context: commitment is deterministic even
    // though HPKE encryption uses randomness.
    assert!(index < 255);
    let address = wallet.address();
    let note = NotePlaintext {
        value: 1_000 + index as u64,
        recipient_tag: address.recipient_tag,
        spend_authority_tag: address.spend_authority_tag,
        rho: Fp::from(10_000 + index as u64),
        rseed: Fp::from(20_000 + index as u64),
        memo: b"CORE003-STEP02-local-regtest".to_vec(),
    };
    let commitment = note_identity(
        note.value, note.recipient_tag, note.spend_authority_tag, note.rho, note.rseed,
    );
    let aad = NoteAad {
        network_id: 3,
        transaction_digest: [1 + index as u8; 32],
        output_index: index as u32,
        note_commitment: bytes(commitment),
        context_digest: [0x72; 32],
    };
    let encrypted = encrypt_note(&address, &note, &aad).expect("local note encryption");
    ShieldedOutputRecord {
        aad,
        encrypted_note: encrypted.encode().expect("canonical encoding"),
    }
}

fn sample(wallet: &ShieldedKeyBundle, count: usize) -> Vec<ShieldedOutputRecord> {
    (0..count).map(|i| fixture_output(wallet, i)).collect()
}

fn chain_block(
    height: u64, hash: u8, parent: u8, records: Vec<ShieldedOutputRecord>,
) -> ShieldedBlock {
    ShieldedBlock {
        height,
        hash: [hash; 32],
        prev_hash: [parent; 32],
        outputs: records,
    }
}

fn commitments(records: &[ShieldedOutputRecord]) -> Vec<[u8; 32]> {
    records.iter().map(|o| o.aad.note_commitment).collect()
}

fn vector_root(label: &str, count: usize, root: [u8; 32]) {
    let hex = root.iter().map(|v| format!("{v:02x}")).collect::<String>();
    // Exactly one line per checkpoint; CI compares two independently staged
    // source trees on an identical deterministic set of note commitments.
    println!("\\nCORE003_VECTOR {label} {count} {hex}");
}

fn append_both(
    scanner: &mut WalletScanner,
    reference: &mut OrderedRootGate,
    height: u64,
    hash: u8,
    parent: u8,
    records: Vec<ShieldedOutputRecord>,
) {
    let next = commitments(&records);
    let independently_derived = reference.expected_after_append(&next).unwrap();
    scanner
        .process_block(chain_block(height, hash, parent, records))
        .expect("V1 scanner accepts canonical fixture");
    reference.verify_and_append(&next, independently_derived).unwrap();
    assert_eq!(bytes(scanner.root()), reference.current_root().unwrap());
    assert_eq!(bytes(scanner.root()), independently_derived);
    assert_eq!(scanner.commitment_count(), reference.commitment_count());
}

#[test]
fn boundaries_zero_one_two_fifteen_sixteen_match_actual_wallet_scanner() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let outputs = sample(&wallet, 16);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut gate = OrderedRootGate::new();

    // Fixed synthetic set describes boundary vectors; the root derives from
    // deterministic note fields, never from ciphertext randomness.
    assert_eq!(bytes(scanner.root()), gate.current_root().unwrap()); // count 0
    vector_root("tree", 0, bytes(scanner.root()));
    append_both(&mut scanner, &mut gate, 0, 1, 0, outputs[0..1].to_vec()); // 1
    vector_root("tree", 1, bytes(scanner.root()));
    append_both(&mut scanner, &mut gate, 1, 2, 1, outputs[1..2].to_vec()); // 2
    vector_root("tree", 2, bytes(scanner.root()));
    append_both(&mut scanner, &mut gate, 2, 3, 2, outputs[2..15].to_vec()); // 15
    vector_root("tree", 15, bytes(scanner.root()));
    append_both(&mut scanner, &mut gate, 3, 4, 3, outputs[15..16].to_vec()); // 16
    vector_root("tree", 16, bytes(scanner.root()));
    assert_eq!(scanner.notes().len(), 16);
}

#[test]
fn different_block_partitions_produce_identical_root_and_witnesses() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let outputs = sample(&wallet, 6);

    let mut batch_scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut batch_gate = OrderedRootGate::new();
    append_both(&mut batch_scanner, &mut batch_gate, 0, 8, 0, outputs.clone());

    let mut partitioned_scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut partitioned_gate = OrderedRootGate::new();
    append_both(&mut partitioned_scanner, &mut partitioned_gate, 0, 1, 0, outputs[..2].to_vec());
    append_both(&mut partitioned_scanner, &mut partitioned_gate, 1, 2, 1, outputs[2..5].to_vec());
    append_both(&mut partitioned_scanner, &mut partitioned_gate, 2, 3, 2, outputs[5..].to_vec());
    assert_eq!(batch_gate.current_root(), partitioned_gate.current_root());
    assert_eq!(batch_scanner.root(), partitioned_scanner.root());

    for (position, record) in outputs.iter().enumerate() {
        let witness = partitioned_scanner
            .witness_for(record.aad.note_commitment).expect("owned note witness");
        assert_eq!(witness.position, position);
        assert_eq!(witness.root, partitioned_scanner.root());
        assert_eq!(
            merkle_root(from_bytes(record.aad.note_commitment), witness.siblings, witness.directions),
            partitioned_scanner.root(),
        );
        assert_eq!(witness.siblings.len(), TREE_DEPTH);
    }
}

#[test]
fn reordering_valid_commitments_cannot_reuse_previous_canonical_root() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let outputs = sample(&wallet, 3);
    let ordered = commitments(&outputs);
    let reversed = vec![ordered[1], ordered[0], ordered[2]];
    let mut reference = OrderedRootGate::new();
    let root = reference.expected_after_append(&ordered).unwrap();
    let wrong = reference.expected_after_append(&reversed).unwrap();
    assert_ne!(root, wrong);
    assert_eq!(
        reference.verify_and_append(&ordered, wrong),
        Err(RootGateError::ForgedClaimedRoot)
    );
    assert_eq!(reference.commitment_count(), 0);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner.process_block(chain_block(0, 1, 0, outputs)).unwrap();
    assert_eq!(root, bytes(scanner.root()));
}

#[test]
fn multi_block_rollback_replacement_and_full_rescan_match() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let outputs = sample(&wallet, 5);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut reference = OrderedRootGate::new();

    let first = chain_block(0, 1, 0, outputs[0..2].to_vec());
    let old_second = chain_block(1, 2, 1, outputs[2..4].to_vec());
    let replacement = chain_block(1, 3, 1, vec![outputs[4].clone()]);
    append_both(&mut scanner, &mut reference, 0, 1, 0, first.outputs.clone());
    let root_at_height_zero = reference.current_root().unwrap();
    append_both(&mut scanner, &mut reference, 1, 2, 1, old_second.outputs.clone());
    assert_ne!(reference.current_root().unwrap(), root_at_height_zero);

    scanner.rollback_to(Some(0)).unwrap();
    reference.rewind_for_fixture(2).unwrap();
    assert_eq!(bytes(scanner.root()), root_at_height_zero);
    assert_eq!(reference.current_root().unwrap(), root_at_height_zero);
    append_both(&mut scanner, &mut reference, 1, 3, 1, replacement.outputs.clone());

    let replay = WalletScanner::rescan(
        wallet.incoming_viewing_key(), 3, &[first, replacement],
    ).expect("full canonical rescan");
    assert_eq!(replay.root(), scanner.root());
    assert_eq!(replay.notes(), scanner.notes());
    assert_eq!(reference.current_root().unwrap(), bytes(replay.root()));
}

#[test]
fn bad_parent_duplicate_and_capacity_fail_without_scanner_root_mutation() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let outputs = sample(&wallet, 17);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut gate = OrderedRootGate::new();
    append_both(&mut scanner, &mut gate, 0, 1, 0, outputs[..1].to_vec());
    let prior_root = bytes(scanner.root());

    let wrong_parent = chain_block(1, 2, 0x55, outputs[1..2].to_vec());
    assert_eq!(scanner.process_block(wrong_parent), Err(WalletStateError::ParentMismatch));
    assert_eq!(bytes(scanner.root()), prior_root);

    let duplicate = chain_block(1, 2, 1, outputs[..1].to_vec());
    assert_eq!(scanner.process_block(duplicate), Err(WalletStateError::DuplicateOutput));
    assert_eq!(bytes(scanner.root()), prior_root);
    assert_eq!(
        gate.expected_after_append(&[outputs[0].aad.note_commitment]),
        Err(RootGateError::DuplicateCommitment)
    );
    append_both(&mut scanner, &mut gate, 1, 2, 1, outputs[1..16].to_vec());
    let full_root = bytes(scanner.root());
    assert_eq!(
        scanner.process_block(chain_block(2, 3, 2, outputs[16..17].to_vec())),
        Err(WalletStateError::TreeFull)
    );
    assert_eq!(
        gate.expected_after_append(&[outputs[16].aad.note_commitment]),
        Err(RootGateError::CapacityExceeded)
    );
    assert_eq!(bytes(scanner.root()), full_root);
    assert_eq!(gate.current_root().unwrap(), full_root);
}

#[test]
fn wallet_scanner_empty_block_keeps_root_but_reference_rejects_empty_append() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    let mut gate = OrderedRootGate::new();
    let root = bytes(scanner.root());
    assert_eq!(gate.expected_after_append(&[]), Err(RootGateError::EmptyAppend));
    // The wallet scan accepts empty blocks; Step01 gate deliberately models
    // a nonempty *shielded transition*. This semantic difference is documented.
    scanner.process_block(chain_block(0, 1, 0, Vec::new())).unwrap();
    assert_eq!(bytes(scanner.root()), root);
    assert_eq!(gate.current_root().unwrap(), root);
    assert_eq!(scanner.tip(), Some((0, [1u8; 32])));
}

#[test]
fn explicit_noncanonical_and_tampered_claims_fail_closed() {
    let wallet = ShieldedKeyBundle::derive([0x47; 32]);
    let records = sample(&wallet, 2);
    let commitments = commitments(&records);
    let mut gate = OrderedRootGate::new();
    let expected = gate.expected_after_append(&commitments).unwrap();
    assert_eq!(
        gate.verify_and_append(&commitments, [0xff; 32]),
        Err(RootGateError::NonCanonicalClaimedRoot)
    );
    assert_ne!(expected, bytes(Fp::from(42)));
    assert_eq!(
        gate.verify_and_append(&commitments, bytes(Fp::from(42))),
        Err(RootGateError::ForgedClaimedRoot)
    );
    assert_eq!(gate.commitment_count(), 0);
}
