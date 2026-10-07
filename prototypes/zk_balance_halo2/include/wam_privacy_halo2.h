#ifndef WAM_PRIVACY_HALO2_H
#define WAM_PRIVACY_HALO2_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct WamPrivacyVerifier WamPrivacyVerifier;

enum WamPrivacyStatus {
    WAM_PRIVACY_OK = 0,
    WAM_PRIVACY_NULL_POINTER = 1,
    WAM_PRIVACY_BAD_LENGTH = 2,
    WAM_PRIVACY_UNSUPPORTED_NETWORK = 3,
    WAM_PRIVACY_AMOUNT_RANGE = 4,
    WAM_PRIVACY_INTERNAL = 5,
    WAM_PRIVACY_PANIC = 6,
    WAM_PRIVACY_BAD_ENVELOPE = 10,
    WAM_PRIVACY_VK_ID_MISMATCH = 11,
    WAM_PRIVACY_CONTEXT_MISMATCH = 12,
    WAM_PRIVACY_TRANSPARENT_BALANCE_MISMATCH = 13,
    WAM_PRIVACY_PROOF_REJECTED = 14
};

uint32_t wam_privacy_halo2_abi_version(void);

int32_t wam_privacy_halo2_verifier_new(WamPrivacyVerifier **out);
int32_t wam_privacy_halo2_verifier_free(WamPrivacyVerifier *handle);

int32_t wam_privacy_halo2_verifier_vk_id(
    const WamPrivacyVerifier *handle,
    uint8_t *out,
    size_t out_len);

int32_t wam_privacy_halo2_verify_hardened_v1(
    const WamPrivacyVerifier *handle,
    const uint8_t *envelope,
    size_t envelope_len,
    uint32_t network_id,
    const uint8_t *transaction_digest,
    size_t transaction_digest_len,
    uint64_t transparent_in,
    uint64_t transparent_out,
    uint64_t fee);

#ifdef __cplusplus
}
#endif

#endif
