"""Re-export the publisher access verifier from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.publisher_access``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import publisher_access as _canonical
from ..publisher_access import (  # noqa: F401
    BROWSER_VERIFICATION_MATRIX_PATH,
    CATALOG_PATH,
    DEFAULT_HEADERS,
    INSTITUTIONAL_IDENTITY_POLICY_PATH,
    load_institutional_identity_policy,
    load_publisher_access_catalog,
    load_publisher_browser_verification_matrix,
    verify_publisher_access,
    verify_publishers,
    _classify_response,
    _get,
    _header,
    _observed_access,
    _probe_candidate,
    _profile_key,
    _response_text,
)


def __getattr__(name: str):
    """Forward anything not re-exported above to the canonical module.

    The old copy had the canonical module's own imported names as its
    attributes too (``requests``, ``time`` and friends), and code that
    patched or read one of them through this path should keep working.
    """
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical)))
