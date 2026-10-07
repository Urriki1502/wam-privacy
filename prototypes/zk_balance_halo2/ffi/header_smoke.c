#include "wam_privacy_halo2.h"

int main(void) {
    WamPrivacyVerifier *verifier = 0;
    if (wam_privacy_halo2_abi_version() != 1) {
        return 1;
    }
    (void)verifier;
    return 0;
}
