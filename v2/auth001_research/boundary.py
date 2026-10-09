"""Research local adapter. Construction and confirmer must remain trusted."""
from dataclasses import dataclass
import threading
from policy import ConsentIssuer, _request_valid
from disclosure import SelectionIssuer, DisclosureService, _selection_fields

@dataclass(frozen=True)
class Prompt:
    request: tuple
    selected_fields: tuple
    exported_metadata: tuple = ("network_id", "resource_scope", "purpose")

class LocalConsentBoundary:
    """The confirmer is installed by local UI bootstrap, never an RPC callback.
    True must mean independently displayed/confirmed Prompt; this code cannot
    establish user presence or authentic UI origin by itself.
    All access to this instance must use release; direct service access bypasses
    this adapter. Durability/recovery remains owned by SEC-001/SEC-003.
    """
    def __init__(self, service, consent_issuer, selection_issuer, confirmer, clock):
        if not isinstance(service, DisclosureService):
            raise ValueError("trusted disclosure service required")
        if not isinstance(consent_issuer, ConsentIssuer) or not isinstance(selection_issuer, SelectionIssuer):
            raise ValueError("trusted local issuers required")
        if not callable(confirmer) or not callable(clock):
            raise ValueError("trusted UI and clock required")
        self._service, self._consent, self._selection = service, consent_issuer, selection_issuer
        self._confirm, self._clock = confirmer, clock
        self._lock = threading.Lock()

    def release(self, request, fields):
        # Copy RPC data before displaying; issuer and service use this same copy.
        if type(request) is not dict or not _request_valid(request) or request["action"] != "DISCLOSE":
            return None
        if not _selection_fields(fields):
            return None
        copied = dict(request)
        prompt = Prompt(tuple(sorted(copied.items())), fields)
        with self._lock:
            try:
                if self._confirm(prompt) is not True:
                    return None
                now = self._clock()
                if type(now) is not int or not 0 <= now < copied["expires_at"]:
                    return None
                expiry = min(copied["expires_at"], now + 60)
                consent = self._consent.issue_after_user_confirmation(copied, expires_at=expiry)
                selection = self._selection.issue_after_user_confirmation(copied, consent, fields, expires_at=expiry)
                return self._service.disclose(copied, now=now, consent=consent, selection=selection)[0]
            except (ValueError, TypeError, RuntimeError):
                return None
