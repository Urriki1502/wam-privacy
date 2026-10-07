use ff::PrimeField;
use halo2_proofs::pasta::Fp;
use wam_privacy_halo2_prototype::{
    anchor::merkle_root,
    note_action::note_identity,
    note_encryption::{
        encrypt_note, NoteAad, NotePlaintext, ShieldedKeyBundle,
    },
    wallet_state::{
        ShieldedBlock, ShieldedOutputRecord, WalletScanner, WalletStateError,
    },
};

fn fp_bytes(value: Fp) -> [u8; 32] {
    let repr = value.to_repr();
    let mut out = [0u8; 32];
    out.copy_from_slice(repr.as_ref());
    out
}

fn output_for(
    bundle: &ShieldedKeyBundle,
    tx_byte: u8,
    output_index: u32,
    value: u64,
    rho: u64,
) -> ShieldedOutputRecord {
    let address = bundle.address();
    let note = NotePlaintext {
        value,
        recipient_tag: address.recipient_tag,
        spend_authority_tag: address.spend_authority_tag,
        rho: Fp::from(rho),
        rseed: Fp::from(rho + 1),
        memo: b"phase12".to_vec(),
    };
    let commitment = note_identity(
        note.value,
        note.recipient_tag,
        note.spend_authority_tag,
        note.rho,
        note.rseed,
    );
    let aad = NoteAad {
        network_id: 3,
        transaction_digest: [tx_byte; 32],
        output_index,
        note_commitment: fp_bytes(commitment),
        context_digest: [tx_byte.wrapping_add(1); 32],
    };
    let encrypted = encrypt_note(&address, &note, &aad).expect("encrypt");
    ShieldedOutputRecord {
        aad,
        encrypted_note: encrypted.encode().expect("encode"),
    }
}

fn block(
    height: u64,
    hash_byte: u8,
    prev_byte: u8,
    outputs: Vec<ShieldedOutputRecord>,
) -> ShieldedBlock {
    ShieldedBlock {
        height,
        hash: [hash_byte; 32],
        prev_hash: [prev_byte; 32],
        outputs,
    }
}

#[test]
fn scanner_recognizes_only_its_notes_and_has_no_spend_authority() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let other = ShieldedKeyBundle::derive([9u8; 32]);
    let incoming = wallet.incoming_viewing_key();

    let ours = output_for(&wallet, 1, 0, 50_000, 10);
    let theirs = output_for(&other, 1, 1, 60_000, 20);

    let mut scanner = WalletScanner::new(incoming, 3);
    scanner
        .process_block(block(0, 1, 0, vec![ours.clone(), theirs]))
        .expect("scan");

    assert_eq!(scanner.commitment_count(), 2);
    assert_eq!(scanner.notes().len(), 1);
    assert_eq!(scanner.notes()[0].plaintext.value, 50_000);
    assert_eq!(scanner.notes()[0].commitment, ours.aad.note_commitment);
}

#[test]
fn current_witness_tracks_new_commitments_and_matches_tree_root() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let first = output_for(&wallet, 1, 0, 50_000, 10);
    let second = output_for(&wallet, 2, 0, 25_000, 30);
    let commitment = first.aad.note_commitment;

    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner
        .process_block(block(0, 1, 0, vec![first]))
        .expect("block0");
    let root0 = scanner.root();

    scanner
        .process_block(block(1, 2, 1, vec![second]))
        .expect("block1");
    let witness = scanner.witness_for(commitment).expect("witness");

    assert_ne!(root0, witness.root);
    let mut repr = <Fp as PrimeField>::Repr::default();
    repr.as_mut().copy_from_slice(&commitment);
    let leaf = Option::<Fp>::from(Fp::from_repr(repr)).expect("canonical");
    assert_eq!(
        merkle_root(leaf, witness.siblings, witness.directions),
        scanner.root()
    );
}

#[test]
fn rollback_then_replacement_branch_updates_notes_and_witnesses() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let first = output_for(&wallet, 1, 0, 50_000, 10);
    let old_second = output_for(&wallet, 2, 0, 25_000, 30);
    let new_second = output_for(&wallet, 3, 0, 30_000, 40);

    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner
        .process_block(block(0, 1, 0, vec![first]))
        .expect("block0");
    scanner
        .process_block(block(1, 2, 1, vec![old_second]))
        .expect("old branch");
    assert_eq!(scanner.notes().len(), 2);

    scanner.rollback_to(Some(0)).expect("rollback");
    assert_eq!(scanner.notes().len(), 1);
    assert_eq!(scanner.tip(), Some((0, [1u8; 32])));

    scanner
        .process_block(block(1, 3, 1, vec![new_second]))
        .expect("replacement");
    assert_eq!(scanner.notes().len(), 2);
    assert_eq!(scanner.notes()[1].plaintext.value, 30_000);
    assert_eq!(scanner.tip(), Some((1, [3u8; 32])));
}

#[test]
fn full_rescan_reconstructs_identical_wallet_state() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let other = ShieldedKeyBundle::derive([9u8; 32]);
    let blocks = vec![
        block(
            0,
            1,
            0,
            vec![
                output_for(&wallet, 1, 0, 50_000, 10),
                output_for(&other, 1, 1, 60_000, 20),
            ],
        ),
        block(1, 2, 1, vec![output_for(&wallet, 2, 0, 25_000, 30)]),
    ];

    let scanner_a =
        WalletScanner::rescan(wallet.incoming_viewing_key(), 3, &blocks).expect("rescan a");
    let scanner_b =
        WalletScanner::rescan(wallet.incoming_viewing_key(), 3, &blocks).expect("rescan b");

    assert_eq!(scanner_a.root(), scanner_b.root());
    assert_eq!(scanner_a.tip(), scanner_b.tip());
    assert_eq!(scanner_a.notes(), scanner_b.notes());
    for note in scanner_a.notes() {
        assert_eq!(
            scanner_a.witness_for(note.commitment),
            scanner_b.witness_for(note.commitment)
        );
    }
}

#[test]
fn wrong_aad_never_creates_false_credit() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let mut record = output_for(&wallet, 1, 0, 50_000, 10);
    record.aad.transaction_digest[0] ^= 1;

    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner
        .process_block(block(0, 1, 0, vec![record]))
        .expect("block remains scanable");
    assert!(scanner.notes().is_empty());
    assert_eq!(scanner.commitment_count(), 1);
}

#[test]
fn malformed_or_discontinuous_block_fails_atomically() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let first = output_for(&wallet, 1, 0, 50_000, 10);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner
        .process_block(block(0, 1, 0, vec![first]))
        .expect("block0");

    let root = scanner.root();
    let notes = scanner.notes().to_vec();

    let bad_parent = block(1, 2, 99, vec![output_for(&wallet, 2, 0, 25_000, 30)]);
    assert_eq!(
        scanner.process_block(bad_parent),
        Err(WalletStateError::ParentMismatch)
    );
    assert_eq!(scanner.root(), root);
    assert_eq!(scanner.notes(), notes.as_slice());

    let mut malformed = output_for(&wallet, 2, 0, 25_000, 30);
    malformed.encrypted_note.truncate(3);
    assert_eq!(
        scanner.process_block(block(1, 2, 1, vec![malformed])),
        Err(WalletStateError::InvalidCiphertext)
    );
    assert_eq!(scanner.root(), root);
    assert_eq!(scanner.notes(), notes.as_slice());
}

#[test]
fn duplicate_output_or_commitment_fails_closed() {
    let wallet = ShieldedKeyBundle::derive([7u8; 32]);
    let first = output_for(&wallet, 1, 0, 50_000, 10);
    let mut scanner = WalletScanner::new(wallet.incoming_viewing_key(), 3);
    scanner
        .process_block(block(0, 1, 0, vec![first.clone()]))
        .expect("block0");

    assert_eq!(
        scanner.process_block(block(1, 2, 1, vec![first])),
        Err(WalletStateError::DuplicateOutput)
    );
}
