"""Re-export the publisher PDF router from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.publisher_pdf_router``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import publisher_pdf_router as _canonical
from ..publisher_pdf_router import (  # noqa: F401
    belongs_to_current_article,
    build_pdf_candidates,
    COPERNICUS_DOI_RE,
    discover_pdf_candidates_from_html,
    extract_elsevier_pii,
    extract_ieee_article_number,
    is_pdf_candidate_url,
    is_supplementary_url,
    MDPI_ISSN_JOURNAL_CODES,
    MDPI_JOURNAL_CODE_ISSNS,
    MDPI_NUMERIC_PATH_RE,
    PDF_JS_DEFAULT_URL_RE,
    PDF_LINK_TEXT_MARKERS,
    PDF_URL_MARKERS,
    PLOS_DOI_JOURNAL_RE,
    PLOS_JOURNAL_PATHS,
    _append_ams_candidates,
    _append_aps_candidates,
    _append_candidate,
    _append_copernicus_candidates,
    _append_mdpi_candidates,
    _append_oxford_candidates,
    _append_plos_candidates,
    _append_query_pdf_candidates,
    _append_source_path_candidates,
    _clean,
    _format_template,
    _mdpi_landing_url_from_doi,
    _mdpi_pdf_url_from_landing_url,
    _plos_journal_path_from_doi,
    _plos_journal_path_from_source,
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
