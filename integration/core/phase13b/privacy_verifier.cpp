#include <wam/privacy/privacy_verifier.h>

#include <mutex>

#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL
extern "C" {
#include <wam/privacy/wam_privacy_halo2.h>
}
#endif

namespace wam::privacy {

bool ExperimentalVerifierCompiled()
{
#ifdef ENABLE_WAM_PRIVACY_EXPERIMENTAL
    return true;
#else
    return false;
#endif
}

VerifyStatus VerifyRegtest(const VerifyRequest& request)
{
#ifndef ENABLE_WAM_PRIVACY_EXPERIMENTAL
    (void)request;
    return VerifyStatus::NOT_COMPILED;
#else
    struct Holder {
        WamPrivacyVerifier* verifier{nullptr};
        int32_t init_status{WAM_PRIVACY_INTERNAL};

        Holder()
        {
            init_status = wam_privacy_halo2_verifier_new(&verifier);
            if (init_status != WAM_PRIVACY_OK) {
                verifier = nullptr;
            }
        }

        ~Holder()
        {
            if (verifier != nullptr) {
                (void)wam_privacy_halo2_verifier_free(verifier);
            }
        }

        Holder(const Holder&) = delete;
        Holder& operator=(const Holder&) = delete;
    };

    static Holder holder;
    static std::mutex verify_mutex;

    if (holder.verifier == nullptr || holder.init_status != WAM_PRIVACY_OK) {
        return static_cast<VerifyStatus>(holder.init_status);
    }

    std::lock_guard<std::mutex> lock{verify_mutex};
    const int32_t status = wam_privacy_halo2_verify_hardened_v1(
        holder.verifier,
        request.envelope.data(),
        request.envelope.size(),
        3, // Phase 13B: regtest only.
        request.transaction_digest.data(),
        request.transaction_digest.size(),
        request.transparent_in,
        request.transparent_out,
        request.fee);
    return static_cast<VerifyStatus>(status);
#endif
}

} // namespace wam::privacy
