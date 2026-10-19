"""Re-export the CloakBrowser compatibility helpers from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.cloakbrowser_compat``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import cloakbrowser_compat as _canonical
from ..cloakbrowser_compat import (  # noqa: F401
    configure_builtin_cloakbrowser,
    ensure_cloakbrowser_platform_compatible,
    prepare_cloakbrowser_runtime,
    _BUILTIN_CACHE_DIR,
    _CLOAKBROWSER_CACHE_ENV,
    _SCANSCI_CACHE_ENV,
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
