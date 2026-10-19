"""Re-export the session broker from the root package.

The publisher stack shipped in two copies that drifted apart; this module is
now a re-export shim over the single implementation in
``scansci_pdf.session_broker``
(#71 item 5). Keep the implementation there, not here.
"""

from .. import session_broker as _canonical
from ..session_broker import (  # noqa: F401
    broker_dir,
    broker_is_running,
    broker_key,
    BROKER_ROOT,
    broker_state_path,
    broker_stop_path,
    BrokerState,
    DATA_DIR,
    load_broker_state,
    pid_is_running,
    start_broker_process,
    submit_broker_job,
    write_broker_state,
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
