"""Re-export the shared HTTP retry helpers from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.http_utils``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import http_utils as _canonical
from ..http_utils import (  # noqa: F401
    request_with_retry,
    _SSL_VERIFY,
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
