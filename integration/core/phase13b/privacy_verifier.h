#ifndef WAM_PHASE13B_PRIVACY_VERIFIER_H
#define WAM_PHASE13B_PRIVACY_VERIFIER_H

#include <array>
#include <cstdint>
#include <span>
#include <vector>

namespace wam::privacy {

enum class VerifyStatus : int32_t {
    OK = 0,
    NULL_POINTER = 1,
    BAD_LENGTH = 2,
    UNSUPPORTED_NETWORK = 3,
    AMOUNT_RANGE = 4,
    INTERNAL = 5,
    PANIC = 6,
    BAD_ENVELOPE = 10,
    VK_ID_MISMATCH = 11,
    CONTEXT_MISMATCH = 12,
    TRANSPARENT_BALANCE_MISMATCH = 13,
    PROOF_REJECTED = 14,
    NOT_COMPILED = 100,
};

struct VerifyRequest {
    std::vector<unsigned char> envelope;
    std::array<unsigned char, 32> transaction_digest{};
    uint64_t transparent_in{0};
    uint64_t transparent_out{0};
    uint64_t fee{0};
};

bool ExperimentalVerifierCompiled();
VerifyStatus VerifyRegtest(const VerifyRequest& request);

} // namespace wam::privacy

#endif
