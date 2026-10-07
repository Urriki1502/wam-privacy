//! Phase 13A: fail-closed C ABI for the hardened WAM privacy verifier.
//!
//! The ABI is intentionally narrow:
//! - an opaque verifier handle owns Halo2 parameters and the verification key;
//! - only regtest verification is enabled;
//! - network/transaction/transparent-balance context is supplied by the caller;
//! - malformed envelopes, context mismatch and invalid proofs return stable codes;
//! - Rust panics are contained and never unwind across the C boundary.
//!
//! This is an integration bridge for isolated Core/regtest work, not a consensus API.

use std::{
    panic::{catch_unwind, AssertUnwindSafe},
    ptr, slice,
};

use halo2_proofs::{
    pasta::EqAffine,
    plonk::{keygen_vk, VerifyingKey},
    poly::commitment::Params,
};

use crate::{
    context::{NetworkId, ProofContext},
    hardened_bundle::HardenedBundleCircuit,
    serialization_v2::{
        verify_hardened_bundle_envelope, vk_identifier, HardenedEnvelopeError, MAX_PROOF_BYTES,
    },
    MAX_WAM_ATOMS,
};

pub const ABI_VERSION: u32 = 1;
pub const VERIFIER_K: u32 = 15;

#[repr(i32)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FfiStatus {
    Ok = 0,
    NullPointer = 1,
    BadLength = 2,
    UnsupportedNetwork = 3,
    AmountRange = 4,
    Internal = 5,
    Panic = 6,
    BadEnvelope = 10,
    VkIdMismatch = 11,
    ContextMismatch = 12,
    TransparentBalanceMismatch = 13,
    ProofRejected = 14,
}

pub struct WamPrivacyVerifier {
    params: Params<EqAffine>,
    vk: VerifyingKey<EqAffine>,
}

fn map_verify_error(err: HardenedEnvelopeError) -> FfiStatus {
    match err {
        HardenedEnvelopeError::VkIdMismatch => FfiStatus::VkIdMismatch,
        HardenedEnvelopeError::ContextMismatch => FfiStatus::ContextMismatch,
        HardenedEnvelopeError::TransparentBalanceMismatch => FfiStatus::TransparentBalanceMismatch,
        HardenedEnvelopeError::ProofRejected => FfiStatus::ProofRejected,
        HardenedEnvelopeError::Truncated
        | HardenedEnvelopeError::BadMagic
        | HardenedEnvelopeError::UnsupportedVersion
        | HardenedEnvelopeError::UnsupportedCircuit
        | HardenedEnvelopeError::WrongInstanceCount
        | HardenedEnvelopeError::NonCanonicalField
        | HardenedEnvelopeError::EmptyProof
        | HardenedEnvelopeError::ProofTooLarge
        | HardenedEnvelopeError::TrailingBytes => FfiStatus::BadEnvelope,
    }
}

#[no_mangle]
pub extern "C" fn wam_privacy_halo2_abi_version() -> u32 {
    ABI_VERSION
}

/// Allocate a verifier context.
///
/// # Safety
///
/// `out` must be either null or writable for one pointer value.
#[no_mangle]
pub unsafe extern "C" fn wam_privacy_halo2_verifier_new(out: *mut *mut WamPrivacyVerifier) -> i32 {
    if out.is_null() {
        return FfiStatus::NullPointer as i32;
    }

    // Fail closed: a failed constructor must never leave the caller holding a
    // stale or uninitialized handle value.
    unsafe {
        ptr::write(out, ptr::null_mut());
    }

    match catch_unwind(AssertUnwindSafe(|| {
        let params: Params<EqAffine> = Params::new(VERIFIER_K);
        let circuit = HardenedBundleCircuit::default();
        let vk = keygen_vk(&params, &circuit).map_err(|_| FfiStatus::Internal)?;
        let handle = Box::new(WamPrivacyVerifier { params, vk });
        // SAFETY: caller supplied a non-null output pointer and the ABI contract
        // requires it to be writable for one pointer value.
        unsafe {
            ptr::write(out, Box::into_raw(handle));
        }
        Ok::<(), FfiStatus>(())
    })) {
        Ok(Ok(())) => FfiStatus::Ok as i32,
        Ok(Err(status)) => status as i32,
        Err(_) => FfiStatus::Panic as i32,
    }
}

/// Destroy a verifier context created by `wam_privacy_halo2_verifier_new`.
///
/// # Safety
///
/// `handle` must be null or a live handle returned by this library and must
/// not be freed more than once.
#[no_mangle]
pub unsafe extern "C" fn wam_privacy_halo2_verifier_free(handle: *mut WamPrivacyVerifier) -> i32 {
    if handle.is_null() {
        return FfiStatus::NullPointer as i32;
    }

    match catch_unwind(AssertUnwindSafe(|| {
        // SAFETY: guaranteed by the function's caller contract.
        unsafe {
            drop(Box::from_raw(handle));
        }
    })) {
        Ok(()) => FfiStatus::Ok as i32,
        Err(_) => FfiStatus::Panic as i32,
    }
}

/// Return the deterministic identifier of the verifier key.
///
/// # Safety
///
/// `handle` must be a live verifier handle. `out` must be writable for
/// exactly 32 bytes.
#[no_mangle]
pub unsafe extern "C" fn wam_privacy_halo2_verifier_vk_id(
    handle: *const WamPrivacyVerifier,
    out: *mut u8,
    out_len: usize,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return FfiStatus::NullPointer as i32;
    }
    if out_len != 32 {
        return FfiStatus::BadLength as i32;
    }

    match catch_unwind(AssertUnwindSafe(|| {
        // SAFETY: non-null live handle is required by the caller contract.
        let verifier = unsafe { &*handle };
        let id = vk_identifier(&verifier.vk);
        // SAFETY: caller contract requires an output buffer of exactly 32 bytes.
        unsafe {
            ptr::copy_nonoverlapping(id.as_ptr(), out, id.len());
        }
    })) {
        Ok(()) => FfiStatus::Ok as i32,
        Err(_) => FfiStatus::Panic as i32,
    }
}

/// Verify one Phase 10D hardened bundle envelope in the Core-facing profile.
///
/// Only network id 3 (regtest) is accepted in Phase 13A.
///
/// # Safety
///
/// All pointers must reference readable buffers for their declared lengths.
/// `handle` must be a live verifier handle.
#[no_mangle]
pub unsafe extern "C" fn wam_privacy_halo2_verify_hardened_v1(
    handle: *const WamPrivacyVerifier,
    envelope_ptr: *const u8,
    envelope_len: usize,
    network_id: u32,
    transaction_digest_ptr: *const u8,
    transaction_digest_len: usize,
    transparent_in: u64,
    transparent_out: u64,
    fee: u64,
) -> i32 {
    if handle.is_null() || envelope_ptr.is_null() || transaction_digest_ptr.is_null() {
        return FfiStatus::NullPointer as i32;
    }
    if transaction_digest_len != 32 || envelope_len == 0 || envelope_len > MAX_PROOF_BYTES + 1024 {
        return FfiStatus::BadLength as i32;
    }
    if network_id != NetworkId::Regtest as u32 {
        return FfiStatus::UnsupportedNetwork as i32;
    }
    if transparent_in > MAX_WAM_ATOMS || transparent_out > MAX_WAM_ATOMS || fee > MAX_WAM_ATOMS {
        return FfiStatus::AmountRange as i32;
    }

    match catch_unwind(AssertUnwindSafe(|| {
        // SAFETY: pointer validity and declared lengths are part of the caller
        // contract; null/length checks were performed above.
        let verifier = unsafe { &*handle };
        let envelope = unsafe { slice::from_raw_parts(envelope_ptr, envelope_len) };
        let digest_raw =
            unsafe { slice::from_raw_parts(transaction_digest_ptr, transaction_digest_len) };
        let mut digest = [0u8; 32];
        digest.copy_from_slice(digest_raw);

        let context = ProofContext::new(
            NetworkId::Regtest,
            digest,
            transparent_in,
            transparent_out,
            fee,
        );

        verify_hardened_bundle_envelope(&verifier.params, &verifier.vk, &context, envelope)
            .map_err(map_verify_error)
    })) {
        Ok(Ok(())) => FfiStatus::Ok as i32,
        Ok(Err(status)) => status as i32,
        Err(_) => FfiStatus::Panic as i32,
    }
}
