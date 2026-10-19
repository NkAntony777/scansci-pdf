"""Re-export the publisher batch downloader from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.publisher_batch``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import publisher_batch as _canonical
from ..publisher_batch import (  # noqa: F401
    ACSCloakBatchDownloader,
    DownloadResult,
    EST_ISSN,
    fetch_est_records,
    IP_BLOCK_STOP_THRESHOLD,
    MAX_BROWSER_CONCURRENCY,
    MIN_PDF_BYTES,
    NON_ARTICLE_PDF_MARKERS,
    PaperRecord,
    PDF_URL_RE,
    PublisherBatchDownloader,
    RETRYABLE_REASONS,
    safe_name,
    _IP_BLOCK_STATUS_CODES,
    _JS_TEXTOF,
    _JS_VISIBLE,
    _PagePool,
    _resolve_profile_dir,
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
