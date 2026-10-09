//! CORE-003 Step 03 — crash/reorg journal fault-injection research only.
//! No Core patch, consensus interface, real wallet, live RPC or production claims.
//! This uses a SINGLE-WRITER local filesystem model. The key and monotonic
//! highwater witness must be supplied by trusted external systems in real use.
#![forbid(unsafe_code)]

#[path = "core003_reference.rs"]
mod reference;

use blake2b_simd::Params;
use ff::PrimeField;
use halo2_proofs::pasta::Fp;
use reference::{OrderedRootGate, RootGateError};
use std::fs::{self, File, OpenOptions};
use std::io::{Cursor, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

const MAGIC: &[u8; 8] = b"CORE003J";
const VERSION: u8 = 1;
const DOMAIN: &[u8] = b"WAM/CORE003/STEP03/JOURNAL/v1";
const STATE_NAME: &str = "shielded.state";
const TEMP_NAME: &str = "shielded.tmp";
const MAX_BLOB: usize = 4096;
const MAX_LEAVES: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Failure {
    Io,
    Malformed,
    MacFailure,
    InvalidState,
    RollbackDetected,
    WrongParent,
    WrongHeight,
    WrongTip,
    EmptyBlock,
    Injected,
    Root(RootGateError),
}

impl From<RootGateError> for Failure {
    fn from(value: RootGateError) -> Self {
        Self::Root(value)
    }
}

#[derive(Clone, Copy, Debug)]
struct Block {
    height: u64,
    hash: [u8; 32],
    parent: [u8; 32],
    root: [u8; 32],
    // Must be ordered; unordered HashSet cannot reconstruct canonical root.
    // Fixtures only: no cryptographic proof-origin attestation here.
    leaves: Vec<[u8; 32]>,
}

#[derive(Clone, Debug)]
struct State {
    seq: u64,
    blocks: Vec<Block>,
    root: [u8; 32],
}

fn fp(n: u64) -> [u8; 32] {
    let repr = Fp::from(n).to_repr();
    let mut raw = [0u8; 32];
    raw.copy_from_slice(repr.as_ref());
    raw
}

fn new_state() -> State {
    State {
        seq: 0,
        blocks: Vec::new(),
        root: OrderedRootGate::new().current_root().expect("empty tree root"),
    }
}

fn derive(state: &State) -> Result<OrderedRootGate, Failure> {
    if state.blocks.len() > MAX_LEAVES {
        return Err(Failure::InvalidState);
    }
    let mut gate = OrderedRootGate::new();
    let mut height = 0u64;
    let mut parent = [0u8; 32];
    for block in &state.blocks {
        if block.height != height || block.parent != parent || block.leaves.is_empty() {
            return Err(Failure::InvalidState);
        }
        // The exact claimed-root binding must be enforced after deriving
        // each block from its ordered commitments.
        gate.verify_and_append(&block.leaves, block.root)
            .map_err(|_| Failure::InvalidState)?;
        parent = block.hash;
        height += 1;
    }
    if gate.current_root()? != state.root {
        return Err(Failure::InvalidState);
    }
    Ok(gate)
}

fn authenticated_digest(key: &[u8; 32], payload: &[u8]) -> [u8; 32] {
    // Keyed Blake2b is a valid MAC primitive, but key storage/rotation is OUT
    // OF SCOPE. This fixture key is fixed, public test material.
    let mut h = Params::new().hash_length(32).key(key).to_state();
    h.update(DOMAIN);
    h.update(payload);
    let digest = h.finalize();
    let mut result = [0u8; 32];
    result.copy_from_slice(digest.as_bytes());
    result
}

fn encode(state: &State, key: &[u8; 32]) -> Result<Vec<u8>, Failure> {
    derive(state)?;
    let mut bytes = Vec::new();
    bytes.extend_from_slice(MAGIC);
    bytes.push(VERSION);
    bytes.extend_from_slice(&state.seq.to_le_bytes());
    bytes.push(u8::try_from(state.blocks.len()).map_err(|_| Failure::Malformed)?);
    for block in &state.blocks {
        bytes.extend_from_slice(&block.height.to_le_bytes());
        bytes.extend_from_slice(&block.hash);
        bytes.extend_from_slice(&block.parent);
        bytes.extend_from_slice(&block.root);
        bytes.push(u8::try_from(block.leaves.len()).map_err(|_| Failure::Malformed)?);
        for commitment in &block.leaves {
            bytes.extend_from_slice(commitment);
        }
    }
    bytes.extend_from_slice(&state.root);
    let mac = authenticated_digest(key, &bytes);
    bytes.extend_from_slice(&mac);
    if bytes.len() > MAX_BLOB {
        return Err(Failure::Malformed);
    }
    Ok(bytes)
}

fn read_exact<const N: usize>(cursor: &mut Cursor<&[u8]>) -> Result<[u8; N], Failure> {
    let mut buf = [0u8; N];
    cursor.read_exact(&mut buf).map_err(|_| Failure::Malformed)?;
    Ok(buf)
}

fn decode(bytes: &[u8], key: &[u8; 32]) -> Result<State, Failure> {
    if bytes.len() < 8 + 1 + 8 + 1 + 32 + 32 || bytes.len() > MAX_BLOB {
        return Err(Failure::Malformed);
    }
    let (payload, mac) = bytes.split_at(bytes.len() - 32);
    if authenticated_digest(key, payload).as_slice() != mac {
        return Err(Failure::MacFailure);
    }
    let mut cursor = Cursor::new(payload);
    if read_exact::<8>(&mut cursor)? != *MAGIC || read_exact::<1>(&mut cursor)?[0] != VERSION {
        return Err(Failure::Malformed);
    }
    let seq = u64::from_le_bytes(read_exact::<8>(&mut cursor)?);
    let count = read_exact::<1>(&mut cursor)?[0] as usize;
    if count > MAX_LEAVES {
        return Err(Failure::Malformed);
    }
    let mut blocks = Vec::with_capacity(count);
    let mut leaf_total = 0usize;
    for _ in 0..count {
        let height = u64::from_le_bytes(read_exact::<8>(&mut cursor)?);
        let hash = read_exact::<32>(&mut cursor)?;
        let parent = read_exact::<32>(&mut cursor)?;
        let root = read_exact::<32>(&mut cursor)?;
        let leaf_count = read_exact::<1>(&mut cursor)?[0] as usize;
        leaf_total += leaf_count;
        if leaf_count == 0 || leaf_total > MAX_LEAVES {
            return Err(Failure::Malformed);
        }
        let mut leaves = Vec::with_capacity(leaf_count);
        for _ in 0..leaf_count {
            leaves.push(read_exact::<32>(&mut cursor)?);
        }
        blocks.push(Block {height, hash, parent, root, leaves});
    }
    let root = read_exact::<32>(&mut cursor)?;
    if cursor.position() as usize != payload.len() {
        return Err(Failure::Malformed);
    }
    let state = State { seq, blocks, root };
    derive(&state)?;
    Ok(state)
}

#[derive(Clone, Copy, Debug)]
enum Crash {
    None,
    AfterWriteBeforeFileSync,
    AfterFileSyncBeforeRename,
    AfterRenameBeforeDirSync,
    AfterDirSyncBeforeAck,
}

fn write_atomic(dir: &Path, key: &[u8; 32], state: &State, crash: Crash)
    -> Result<(), Failure>
{
    let payload = encode(state, key)?;
    let tmp = dir.join(TEMP_NAME);
    let dst = dir.join(STATE_NAME);
    // create_new stops an old orphan from being silently reused. Recovery
    // must authenticate the committed snapshot before removing an orphan.
    let mut f = OpenOptions::new().write(true).create_new(true).open(&tmp)
        .map_err(|_| Failure::Io)?;
    f.write_all(&payload).map_err(|_| Failure::Io)?;
    if matches!(crash, Crash::AfterWriteBeforeFileSync) {
        return Err(Failure::Injected);
    }
    f.sync_all().map_err(|_| Failure::Io)?;
    if matches!(crash, Crash::AfterFileSyncBeforeRename) {
        return Err(Failure::Injected);
    }
    drop(f);
    fs::rename(&tmp, &dst).map_err(|_| Failure::Io)?;
    if matches!(crash, Crash::AfterRenameBeforeDirSync) {
        // Process-crash test sees the new filename. On physical power loss
        // the durable result is filesystem-dependent, NOT proven by this test.
        return Err(Failure::Injected);
    }
    File::open(dir).map_err(|_| Failure::Io)?.sync_all().map_err(|_| Failure::Io)?;
    if matches!(crash, Crash::AfterDirSyncBeforeAck) {
        return Err(Failure::Injected);
    }
    Ok(())
}

struct Journal {
    dir: PathBuf,
    key: [u8; 32],
    state: State,
}

impl Journal {
    fn initialize(dir: &Path, key: [u8; 32]) -> Result<Self, Failure> {
        fs::create_dir_all(dir).map_err(|_| Failure::Io)?;
        if dir.join(STATE_NAME).exists() || dir.join(TEMP_NAME).exists() {
            return Err(Failure::Io);
        }
        let state = new_state();
        write_atomic(dir, &key, &state, Crash::None)?;
        Ok(Self {dir: dir.to_path_buf(), key, state})
    }

    fn recover(dir: &Path, key: [u8; 32], highwater: Option<u64>)
        -> Result<Self, Failure>
    {
        // Missing committed state fails closed. Never silently reset to an
        // empty wallet when the durable state is missing.
        let data = fs::read(dir.join(STATE_NAME)).map_err(|_| Failure::Io)?;
        let state = decode(&data, &key)?;
        if highwater.is_some_and(|trusted_seq| state.seq < trusted_seq) {
            return Err(Failure::RollbackDetected);
        }
        // Only after successful validation, clean a prior incomplete write.
        if dir.join(TEMP_NAME).exists() {
            fs::remove_file(dir.join(TEMP_NAME)).map_err(|_| Failure::Io)?;
        }
        Ok(Self {dir: dir.to_path_buf(), key, state})
    }

    fn root(&self) -> [u8; 32] {
        self.state.root
    }

    fn seq(&self) -> u64 {
        self.state.seq
    }

    fn tip(&self) -> [u8; 32] {
        self.state.blocks.last().map_or([0u8; 32], |b| b.hash)
    }

    fn expected_root(&self, leaves: &[[u8; 32]]) -> Result<[u8; 32], Failure> {
        derive(&self.state)?.expected_after_append(leaves).map_err(Into::into)
    }

    fn append(
        &mut self,
        height: u64, hash: [u8; 32], parent: [u8; 32],
        leaves: &[[u8; 32]], claimed_root: [u8; 32], crash: Crash
    ) -> Result<(), Failure> {
        if height != self.state.blocks.len() as u64 {
            return Err(Failure::WrongHeight);
        }
        if parent != self.tip() {
            return Err(Failure::WrongParent);
        }
        if leaves.is_empty() {
            return Err(Failure::EmptyBlock);
        }
        let mut gate = derive(&self.state)?;
        gate.verify_and_append(leaves, claimed_root)?;
        let mut next = self.state.clone();
        next.seq = next.seq.checked_add(1).ok_or(Failure::InvalidState)?;
        next.blocks.push(Block {height, hash, parent, root: claimed_root, leaves: leaves.to_vec()});
        next.root = gate.current_root()?;
        write_atomic(&self.dir, &self.key, &next, crash)?;
        self.state = next;
        Ok(())
    }

    fn rollback_tip(&mut self, hash: [u8; 32], crash: Crash)
        -> Result<(), Failure>
    {
        if self.state.blocks.is_empty() || self.tip() != hash {
            return Err(Failure::WrongTip);
        }
        let mut next = self.state.clone();
        next.blocks.pop();
        next.seq = next.seq.checked_add(1).ok_or(Failure::InvalidState)?;
        next.root = derive(&next)?.current_root()?;
        write_atomic(&self.dir, &self.key, &next, crash)?;
        self.state = next;
        Ok(())
    }
}

static NEXT_TMP: AtomicU64 = AtomicU64::new(1);
struct FixtureDir(PathBuf);
impl FixtureDir {
    fn new() -> Self {
        let n = NEXT_TMP.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!("wam-core003-s3-{}-{n}", std::process::id()));
        fs::create_dir(&path).expect("isolated fixture directory");
        Self(path)
    }
}
impl Drop for FixtureDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
const KEY: [u8; 32] = [0x47; 32];
fn new_journal(dir: &FixtureDir) -> Journal {
    Journal::initialize(&dir.0, KEY).expect("initialize")
}
fn append_valid(j: &mut Journal, height: u64, hash: u8, parent: u8, leaves: &[u64]) {
    let leaves: Vec<_> = leaves.iter().copied().map(fp).collect();
    let root = j.expected_root(&leaves).expect("expected root");
    j.append(height, [hash; 32], [parent; 32], &leaves, root, Crash::None)
        .expect("committed append");
}

#[test]
fn genesis_is_authenticated_and_recovers_to_identical_root() {
    let dir = FixtureDir::new();
    let journal = new_journal(&dir);
    let reopened = Journal::recover(&dir.0, KEY, Some(0)).unwrap();
    assert_eq!(journal.root(), reopened.root());
    assert_eq!(reopened.seq(), 0);
}

#[test]
fn durable_multiblock_restart_matches_replay_root() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1, 2]);
    append_valid(&mut j, 1, 2, 1, &[3]);
    let seq = j.seq();
    let root = j.root();
    drop(j);
    let recovered = Journal::recover(&dir.0, KEY, Some(seq)).unwrap();
    assert_eq!(recovered.root(), root);
    let other = FixtureDir::new();
    let mut replay = new_journal(&other);
    append_valid(&mut replay, 0, 1, 0, &[1, 2]);
    append_valid(&mut replay, 1, 2, 1, &[3]);
    assert_eq!(replay.root(), recovered.root());
}

#[test]
fn malformed_claim_parent_and_height_cannot_mutate_disk() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    let old = fs::read(dir.0.join(STATE_NAME)).unwrap();
    let wrong = fp(999);
    assert!(matches!(
        j.append(0, [1; 32], [0; 32], &[fp(1)], wrong, Crash::None),
        Err(Failure::Root(RootGateError::ForgedClaimedRoot))
    ));
    assert_eq!(j.append(1, [1; 32], [0; 32], &[fp(1)], wrong, Crash::None), Err(Failure::WrongHeight));
    assert_eq!(j.append(0, [1; 32], [99; 32], &[fp(1)], wrong, Crash::None), Err(Failure::WrongParent));
    assert_eq!(fs::read(dir.0.join(STATE_NAME)).unwrap(), old);
    assert_eq!(j.seq(), 0);
}

#[test]
fn injected_before_rename_recovers_previous_committed_root_and_cleans_orphan() {
    for crash in [Crash::AfterWriteBeforeFileSync, Crash::AfterFileSyncBeforeRename] {
        let dir = FixtureDir::new();
        let mut j = new_journal(&dir);
        append_valid(&mut j, 0, 1, 0, &[1]);
        let root = j.root();
        let seq = j.seq();
        let next = [fp(2)];
        let expected = j.expected_root(&next).unwrap();
        assert_eq!(
            j.append(1, [2; 32], [1; 32], &next, expected, crash),
            Err(Failure::Injected)
        );
        drop(j); // Simulate crash; never reuse volatile copy
        let recovered = Journal::recover(&dir.0, KEY, Some(seq)).unwrap();
        assert_eq!(recovered.root(), root);
        assert_eq!(recovered.seq(), seq);
        assert!(!dir.0.join(TEMP_NAME).exists());
    }
}

#[test]
fn ambiguous_ack_after_rename_recovers_new_state_without_double_append() {
    for crash in [Crash::AfterRenameBeforeDirSync, Crash::AfterDirSyncBeforeAck] {
        let dir = FixtureDir::new();
        let mut j = new_journal(&dir);
        append_valid(&mut j, 0, 1, 0, &[1]);
        let next = [fp(2)];
        let new_root = j.expected_root(&next).unwrap();
        let seq_before = j.seq();
        assert_eq!(
            j.append(1, [2; 32], [1; 32], &next, new_root, crash),
            Err(Failure::Injected)
        );
        drop(j);
        let mut recovered = Journal::recover(&dir.0, KEY, Some(seq_before)).unwrap();
        assert_eq!(recovered.root(), new_root);
        assert_eq!(recovered.seq(), seq_before + 1);
        assert_eq!(
            recovered.append(1, [2; 32], [1; 32], &next, new_root, Crash::None),
            Err(Failure::WrongHeight)
        );
    }
}

#[test]
fn reorg_undo_then_replacement_and_fresh_rescan_converge() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1, 2]);
    let stable = j.root();
    append_valid(&mut j, 1, 2, 1, &[3]);
    let old_seq = j.seq();
    j.rollback_tip([2; 32], Crash::None).unwrap();
    assert_eq!(j.root(), stable);
    append_valid(&mut j, 1, 3, 1, &[4]);
    let final_root = j.root();
    let final_seq = j.seq();
    assert_eq!(final_seq, old_seq + 2);
    drop(j);
    let recovered = Journal::recover(&dir.0, KEY, Some(final_seq)).unwrap();
    assert_eq!(recovered.root(), final_root);
    let fresh_dir = FixtureDir::new();
    let mut fresh = new_journal(&fresh_dir);
    append_valid(&mut fresh, 0, 1, 0, &[1, 2]);
    append_valid(&mut fresh, 1, 3, 1, &[4]);
    assert_eq!(fresh.root(), final_root);
}

#[test]
fn wrong_tip_rollback_cannot_touch_committed_state() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1]);
    let before = fs::read(dir.0.join(STATE_NAME)).unwrap();
    assert_eq!(j.rollback_tip([99; 32], Crash::None), Err(Failure::WrongTip));
    assert_eq!(fs::read(dir.0.join(STATE_NAME)).unwrap(), before);
}

#[test]
fn missing_truncated_bitflipped_wrong_key_snapshots_fail_closed() {
    let dir = FixtureDir::new();
    assert!(matches!(Journal::recover(&dir.0, KEY, None), Err(Failure::Io)));
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1]);
    let path = dir.0.join(STATE_NAME);
    let bytes = fs::read(&path).unwrap();
    assert!(matches!(Journal::recover(&dir.0, [0x58; 32], None), Err(Failure::MacFailure)));
    fs::write(&path, &bytes[..10]).unwrap();
    assert!(matches!(Journal::recover(&dir.0, KEY, None), Err(Failure::Malformed)));
    let mut damaged = bytes.clone();
    damaged[18] ^= 0x01;
    fs::write(&path, &damaged).unwrap();
    assert!(matches!(Journal::recover(&dir.0, KEY, None), Err(Failure::MacFailure)));
    fs::write(&path, &bytes).unwrap();
    assert!(Journal::recover(&dir.0, KEY, None).is_ok());
}

#[test]
fn authenticated_but_semantically_invalid_journal_is_rejected() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1]);
    append_valid(&mut j, 1, 2, 1, &[2]);
    let mut forged = j.state.clone();
    forged.blocks[1].parent = [88; 32];
    // No verified policy should serialize this malformed state.
    assert_eq!(encode(&forged, &KEY), Err(Failure::InvalidState));
    // Directly test decoder state validation with re-authenticated bytes.
    let mut bytes = fs::read(dir.0.join(STATE_NAME)).unwrap();
    let second_parent_offset = 8 + 1 + 8 + 1 + (8 + 32 + 32 + 32 + 1 + 32) + 8 + 32;
    bytes[second_parent_offset] ^= 1;
    let mac_pos = bytes.len() - 32;
    let mac = authenticated_digest(&KEY, &bytes[..mac_pos]);
    bytes[mac_pos..].copy_from_slice(&mac);
    assert!(matches!(decode(&bytes, &KEY), Err(Failure::InvalidState)));
}

#[test]
fn valid_old_snapshot_requires_trusted_highwater_to_detect_rollback() {
    let dir = FixtureDir::new();
    let mut j = new_journal(&dir);
    append_valid(&mut j, 0, 1, 0, &[1]);
    let first = fs::read(dir.0.join(STATE_NAME)).unwrap();
    append_valid(&mut j, 1, 2, 1, &[2]);
    let trusted_seq = j.seq();
    fs::write(dir.0.join(STATE_NAME), first).unwrap();
    assert!(matches!(
        Journal::recover(&dir.0, KEY, Some(trusted_seq)),
        Err(Failure::RollbackDetected)
    ));
    // Explicit negative evidence: a valid, older MAC can be replayed if
    // caller cannot supply an INDEPENDENT persistent trusted highwater.
    assert_eq!(Journal::recover(&dir.0, KEY, None).unwrap().seq(), 1);
}
