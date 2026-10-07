//! Phase 10D: protocol/network/transaction context binding.
//!
//! The context digest is a public circuit input. It prevents a valid shielded
//! proof from being silently reinterpreted under another WAM network,
//! protocol version, circuit profile, transaction digest, or transparent
//! value-balance tuple.

use blake2b_simd::Params;
use ff::FromUniformBytes;
use halo2_proofs::pasta::Fp;

pub const CONTEXT_DOMAIN: &[u8] = b"WAM/Privacy/ProofContext/v1";
pub const PROTOCOL_VERSION: u16 = 1;
pub const CIRCUIT_ID_HARDENED_2X2: u16 = 0x0A04;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u32)]
pub enum NetworkId {
    Mainnet = 1,
    Testnet = 2,
    Regtest = 3,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProofContext {
    pub protocol_version: u16,
    pub network: NetworkId,
    pub circuit_id: u16,
    pub transaction_digest: [u8; 32],
    pub transparent_in: u64,
    pub transparent_out: u64,
    pub fee: u64,
}

impl ProofContext {
    pub fn new(
        network: NetworkId,
        transaction_digest: [u8; 32],
        transparent_in: u64,
        transparent_out: u64,
        fee: u64,
    ) -> Self {
        Self {
            protocol_version: PROTOCOL_VERSION,
            network,
            circuit_id: CIRCUIT_ID_HARDENED_2X2,
            transaction_digest,
            transparent_in,
            transparent_out,
            fee,
        }
    }

    pub fn digest(&self) -> Fp {
        let mut state = Params::new()
            .hash_length(64)
            .personal(b"WAMctx10d")
            .to_state();
        state.update(CONTEXT_DOMAIN);
        state.update(&self.protocol_version.to_le_bytes());
        state.update(&(self.network as u32).to_le_bytes());
        state.update(&self.circuit_id.to_le_bytes());
        state.update(&self.transaction_digest);
        state.update(&self.transparent_in.to_le_bytes());
        state.update(&self.transparent_out.to_le_bytes());
        state.update(&self.fee.to_le_bytes());
        let digest = state.finalize();
        let mut wide = [0u8; 64];
        wide.copy_from_slice(digest.as_bytes());
        Fp::from_uniform_bytes(&wide)
    }
}
