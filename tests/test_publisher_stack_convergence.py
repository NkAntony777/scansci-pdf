"""The publisher stack must have one implementation, not two (#71 item 5).

The repository shipped two copies of the publisher stack: one at the package
root and one under ``scansci_pdf.institutional/``. They were both live --
``main.py`` and ``sources/__init__.py`` used the institutional one, the CLI
and ``acs_batch.py`` used the root one -- and they had already drifted: the
``%PDF-`` signature fix from #75 and the PDF-capture work from #69 landed in
the root copy only, and the Optica profile from #59 landed in the
institutional copy only.

The copies are now one implementation plus re-export shims. These tests pin
that, because the failure mode is a silent one: a fix applied to one copy
looks fine until the other copy runs it.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

# (institutional module, canonical module at the package root)
PAIRS = [
    ("scansci_pdf.institutional.publisher_batch", "scansci_pdf.publisher_batch"),
    ("scansci_pdf.institutional.publisher_profiles", "scansci_pdf.publisher_profiles"),
    ("scansci_pdf.institutional.publisher_access", "scansci_pdf.publisher_access"),
    ("scansci_pdf.institutional.publisher_pdf_router", "scansci_pdf.publisher_pdf_router"),
    ("scansci_pdf.institutional.http_utils", "scansci_pdf.http_utils"),
    ("scansci_pdf.institutional.session_store", "scansci_pdf.session_store"),
    ("scansci_pdf.institutional.session_broker", "scansci_pdf.session_broker"),
    ("scansci_pdf.institutional.flaresolverr", "scansci_pdf.flaresolverr"),
    ("scansci_pdf.institutional.cloakbrowser_compat", "scansci_pdf.cloakbrowser_compat"),
    (
        "scansci_pdf.institutional.extractors.html_extractor",
        "scansci_pdf.extractors.html_extractor",
    ),
    (
        "scansci_pdf.institutional.extractors.pdf_extractor",
        "scansci_pdf.extractors.pdf_extractor",
    ),
]
for _adapter in ["acs", "elsevier", "generic", "nature", "rsc", "tandfonline", "wiley"]:
    PAIRS.append((
        f"scansci_pdf.institutional.extractors.publisher_adapters.{_adapter}",
        f"scansci_pdf.extractors.publisher_adapters.{_adapter}",
    ))

IDS = [shim.rsplit(".", 1)[-1] if "publisher_adapters" in shim else shim for shim, _ in PAIRS]


@pytest.mark.parametrize("shim_name,canon_name", PAIRS, ids=IDS)
def test_the_old_import_path_gives_the_canonical_objects(shim_name, canon_name):
    """Both import paths must hand back the *same* objects, not equal copies."""
    shim = importlib.import_module(shim_name)
    canon = importlib.import_module(canon_name)

    for name in dir(canon):
        if name.startswith("__"):
            continue
        value = getattr(canon, name, None)
        if value is None:
            continue
        assert getattr(shim, name) is value, (
            f"{shim_name}.{name} is not the same object as {canon_name}.{name}"
        )


@pytest.mark.parametrize("shim_name,canon_name", PAIRS, ids=IDS)
def test_the_institutional_module_holds_no_implementation_of_its_own(shim_name, canon_name):
    """A second copy can only come back if someone writes one.

    This is the check that would have caught the drift: a new function or
    class defined in the shim means the two paths have started to diverge
    again, and every fix now has to be written twice.
    """
    shim = importlib.import_module(shim_name)
    source = Path(shim.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    own = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert own == ["__getattr__", "__dir__"], (
        f"{shim_name} defines {own} -- the implementation belongs in {canon_name}"
    )


def test_the_optica_profile_reaches_both_paths():
    """#59's profile was only in the institutional copy, so the CLI never saw it."""
    from scansci_pdf.institutional import publisher_profiles as institutional
    from scansci_pdf import publisher_profiles as canonical

    for module in (canonical, institutional):
        profile = module.get_publisher_profile("optica")
        assert profile.name == "Optica"
        assert module.infer_publisher_profile("10.1364/OL.47.013297") is profile
        assert "optica" in module.list_publisher_profiles()

    assert institutional.get_publisher_profile("optica") is canonical.get_publisher_profile(
        "optica"
    )
