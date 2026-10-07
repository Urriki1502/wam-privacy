#include <wam/privacy/privacy_verifier.h>

extern "C" {
#include <wam/privacy/wam_privacy_halo2.h>
}

#include <atomic>
#include <cassert>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <thread>

struct WamPrivacyVerifier {};

static std::atomic<bool> g_entered{false};
static std::atomic<bool> g_release{false};

extern "C" int32_t wam_privacy_halo2_verifier_new(WamPrivacyVerifier** out)
{
    static WamPrivacyVerifier verifier;
    if (out == nullptr) {
        return WAM_PRIVACY_NULL_POINTER;
    }
    *out = &verifier;
    return WAM_PRIVACY_OK;
}

extern "C" int32_t wam_privacy_halo2_verifier_free(WamPrivacyVerifier*)
{
    return WAM_PRIVACY_OK;
}

extern "C" int32_t wam_privacy_halo2_verify_hardened_v1(
    const WamPrivacyVerifier*,
    const uint8_t*,
    size_t,
    uint32_t,
    const uint8_t*,
    size_t,
    uint64_t,
    uint64_t,
    uint64_t)
{
    g_entered.store(true, std::memory_order_release);
    while (!g_release.load(std::memory_order_acquire)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return WAM_PRIVACY_OK;
}

int main()
{
    wam::privacy::VerifyRequest request;
    request.envelope = {0x01};
    request.transaction_digest.fill(0);

    std::atomic<int32_t> first{-1};
    std::thread worker([&] {
        first.store(
            static_cast<int32_t>(wam::privacy::VerifyRegtest(request)),
            std::memory_order_release);
    });

    while (!g_entered.load(std::memory_order_acquire)) {
        std::this_thread::yield();
    }

    const auto second = wam::privacy::VerifyRegtest(request);
    assert(second == wam::privacy::VerifyStatus::BUSY);

    g_release.store(true, std::memory_order_release);
    worker.join();

    assert(first.load(std::memory_order_acquire) ==
           static_cast<int32_t>(wam::privacy::VerifyStatus::OK));
    return 0;
}
