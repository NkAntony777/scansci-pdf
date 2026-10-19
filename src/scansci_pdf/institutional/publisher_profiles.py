"""Re-export the publisher profiles from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.publisher_profiles``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import publisher_profiles as _canonical
from ..publisher_profiles import (  # noqa: F401
    ACM_PROFILE,
    ACS_PROFILE,
    AIP_PROFILE,
    AMS_PROFILE,
    ANNUAL_REVIEWS_PROFILE,
    APS_PROFILE,
    COPERNICUS_PROFILE,
    ELSEVIER_PROFILE,
    FRONTIERS_PROFILE,
    get_publisher_profile,
    IEEE_PROFILE,
    infer_publisher_profile,
    infer_publisher_profile_from_url,
    IOP_PROFILE,
    list_publisher_profiles,
    MDPI_PROFILE,
    OPTICA_PROFILE,
    OXFORD_ACADEMIC_PROFILE,
    PdfSourcePathTemplate,
    PLOS_PROFILE,
    PNAS_PROFILE,
    PUBLISHER_PROFILES,
    PublisherProfile,
    ROYAL_SOCIETY_PUBLISHING_PROFILE,
    RSC_PROFILE,
    SCIENCE_PROFILE,
    SPRINGER_PROFILE,
    WILEY_PROFILE,
    WORLD_SCIENTIFIC_PROFILE,
    _aps_article_url,
    _PROFILE_ALIASES,
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
