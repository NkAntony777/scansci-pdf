"""The version of record must win even when the container resolution runs wide.

#89 traced a real Elsevier article (``10.1016/j.tws.2017.05.030``) where the
attachment scorer ranked the accepted manuscript above the version of record
-- and the cause was not the scoring weights. ``_elsevier_attachment_container``
resolved the two attachments of the *same* article to wildly different nodes:

    …-main.pdf                                 238,040 chars  (whole article)
    …-Fatemeh_Azhari_empirical_model_2017.pdf   1,171 chars  (tight block)

The version of record's container was an ancestor spanning the document, so
its metadata contained the *sibling* attachment's markers -- ``aam-pdf`` (-60)
and ``thumbnail`` (-100) -- and the correct file scored

    +20 (.pdf) +10 (pdf) +100 (-main.pdf) +5 (page-count) +5 (attachment-size)
    -100 (thumbnail) -60 (aam-pdf)                                  = -20

while the manuscript, with a tight container, scored

    +20 +10 +5 -60 ("submitted to")                                = -25

The version of record won by five points, and on an article whose manuscript
carries a "full-text" claim of its own it would have lost outright.

The payload below is a model of that shape -- the article-level ``<eid>`` that
sits outside every attachment block, the two attachment blocks, and a body
large enough to dominate the metadata of any node that spans it. The
``aam-pdf`` and ``thumbnail`` markers live in the body, which is where the
sibling's markers were in the captured payload.
"""

from __future__ import annotations

import importlib
import xml.etree.ElementTree as ET

import pytest

from scansci_pdf._publisher_strategies_core import _elsevier_attachment_score
from scansci_pdf.sources import elsevier_api

VOR_EID = "1-s2.0-S0263823116307662-main.pdf"
AM_EID = "1-s2.0-S0263823116307662-Fatemeh_Azhari_empirical_model_2017.pdf"

# The markers the sibling's metadata contributed to the version of record when
# the container ran wide. Neither belongs to the version of record.
SIBLING_MARKERS = ("aam-pdf", "thumbnail")

_BODY_PARAGRAPH = (
    "Post-fire mechanical response of ultra-high strength (Grade 1200) steel "
    "under high temperatures: linking thermal stability and microstructure. "
)


def _payload() -> str:
    """The modelled Elsevier FULL response for the reported article."""
    body = (_BODY_PARAGRAPH * 2400) + (
        '<ce:para>Supplementary material is served as aam-pdf; a thumbnail '
        "preview is available for the accepted manuscript.</ce:para>"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<full-text-retrieval-response xmlns:ce="http://www.elsevier.com/xml/common/dtd">
  <originalText>
    <xocs:doc xmlns:xocs="http://www.elsevier.com/xml/xocs/dtd">
      <xocs:full-text-retrieval-response>
        <full-text-retrieval-response>
          <eid>1-s2.0-S0263823116307662</eid>
          <attachments>
            <attachment>
              <attachment-eid>{VOR_EID}</attachment-eid>
              <attachment-size>1234567</attachment-size>
              <page-count>22</page-count>
              <mime-type>application/pdf</mime-type>
            </attachment>
            <attachment>
              <attachment-eid>{AM_EID}</attachment-eid>
              <label>submitted to thin-walled structures this manuscript version is
                made available under the cc-by-nc-nd 4.0 license</label>
              <page-count>22</page-count>
            </attachment>
          </attachments>
          <body><ce:sections>{body}</ce:sections></body>
        </full-text-retrieval-response>
      </xocs:full-text-retrieval-response>
    </xocs:doc>
  </originalText>
</full-text-retrieval-response>
"""


# The container logic exists in two places; both feed a live code path
# (_publisher_strategies_core's API lane and sources.elsevier_api's fetch_pdf).
IMPLS = (
    pytest.param(
        (
            "scansci_pdf._publisher_strategies_core",
            "_elsevier_attachment_container",
            "_elsevier_attachment_metadata",
            "_elsevier_attachment_blocks",
            "_elsevier_eids_in",
        ),
        id="publisher_strategies_core",
    ),
    pytest.param(
        (
            "scansci_pdf.sources.elsevier_api",
            "_attachment_container",
            "_attachment_metadata",
            "_attachment_blocks",
            "_eids_in",
        ),
        id="sources.elsevier_api",
    ),
)


def _metadata_by_eid(module_name, container_name, metadata_name, blocks_name,
                     eids_name, xml_text):
    """The metadata each candidate attachment is scored with."""
    module = importlib.import_module(module_name)
    root = ET.fromstring(xml_text)
    parent_map = {child: parent for parent in root.iter() for child in parent}
    blocks = getattr(module, blocks_name)(root)

    out: dict[str, str] = {}
    for el in root.iter():
        for eid in getattr(module, eids_name)(el):
            if eid in out:
                continue
            container = getattr(module, container_name)(el, parent_map, eid, blocks)
            out[eid] = getattr(module, metadata_name)(container)
    return out


@pytest.mark.parametrize("impl", IMPLS)
def test_the_version_of_record_is_scored_on_its_own_metadata(impl):
    """The version of record must not inherit the manuscript's markers."""
    module_name, container_name, metadata_name, blocks_name, eids_name = impl
    metadata = _metadata_by_eid(
        module_name, container_name, metadata_name, blocks_name, eids_name, _payload()
    )

    vor = metadata[VOR_EID]
    assert vor, "the version of record resolved to no metadata at all"
    for marker in SIBLING_MARKERS:
        assert marker not in vor, (
            f"the version of record's metadata carries the sibling's {marker!r} marker"
        )


@pytest.mark.parametrize("impl", IMPLS)
def test_both_containers_stay_tight(impl):
    """Pin the two containers so they cannot drift apart again.

    The defect was a container of 238,040 chars next to one of 1,171 chars for
    the same article's two attachments. Both must now be a tight block, of a
    comparable size.
    """
    module_name, container_name, metadata_name, blocks_name, eids_name = impl
    metadata = _metadata_by_eid(
        module_name, container_name, metadata_name, blocks_name, eids_name, _payload()
    )

    vor_len = len(metadata[VOR_EID])
    am_len = len(metadata[AM_EID])
    assert vor_len < 4096, f"the version of record's container is {vor_len} chars"
    assert am_len < 4096, f"the manuscript's container is {am_len} chars"
    assert max(vor_len, am_len) <= 4 * max(1, min(vor_len, am_len)), (
        f"the two containers drifted apart again: {vor_len} vs {am_len}"
    )


@pytest.mark.parametrize("impl", IMPLS)
def test_the_version_of_record_outranks_the_manuscript(impl):
    """The whole point: the version of record is the file that gets fetched."""
    module_name, container_name, metadata_name, blocks_name, eids_name = impl
    metadata = _metadata_by_eid(
        module_name, container_name, metadata_name, blocks_name, eids_name, _payload()
    )

    vor_score = _elsevier_attachment_score(VOR_EID, metadata[VOR_EID])
    am_score = _elsevier_attachment_score(AM_EID, metadata[AM_EID])
    assert vor_score > am_score, (
        f"the version of record scored {vor_score}, the manuscript {am_score}"
    )


def test_the_extraction_ranks_the_version_of_record_first():
    """End to end: the ranked candidate list starts with the version of record."""
    from scansci_pdf._publisher_strategies_core import (
        _extract_elsevier_pdf_attachment_eids,
    )

    ranked = _extract_elsevier_pdf_attachment_eids(_payload())
    assert ranked[0] == VOR_EID
    assert AM_EID in ranked


def test_the_two_copies_agree_on_the_container():
    """The container helpers had drifted too (only one knew about ``web-pdf``).

    Pin them together so #89 cannot be fixed in one copy only.
    """
    core = importlib.import_module("scansci_pdf._publisher_strategies_core")
    api = importlib.import_module("scansci_pdf.sources.elsevier_api")
    payload = _payload()

    core_meta = _metadata_by_eid(
        "scansci_pdf._publisher_strategies_core",
        "_elsevier_attachment_container",
        "_elsevier_attachment_metadata",
        "_elsevier_attachment_blocks",
        "_elsevier_eids_in",
        payload,
    )
    api_meta = _metadata_by_eid(
        "scansci_pdf.sources.elsevier_api",
        "_attachment_container",
        "_attachment_metadata",
        "_attachment_blocks",
        "_eids_in",
        payload,
    )
    assert core_meta == api_meta

    # The normalisation of an id to an attachment identity is shared logic.
    for eid in (VOR_EID, AM_EID, "1-s2.0-S0263823116307662"):
        assert core._elsevier_attachment_key(eid) == api._attachment_key(eid)


def test_an_article_level_id_and_its_main_pdf_name_one_attachment():
    """``1-s2.0-X`` and ``1-s2.0-X-main.pdf`` are the same version of record.

    The article-level id sits outside every attachment block, so it is the
    attachment block that describes the version of record it names -- and the
    two must not be treated as two different attachments.
    """
    core = importlib.import_module("scansci_pdf._publisher_strategies_core")
    assert core._elsevier_attachment_key("1-s2.0-X-main.pdf") == core._elsevier_attachment_key(
        "1-s2.0-X"
    )
    assert core._elsevier_attachment_key(AM_EID) != core._elsevier_attachment_key(VOR_EID)
