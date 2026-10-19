"""Tests for the persistent Sci-Hub browser-worker pool.

The pool's whole point: its threads live for the process lifetime, so each
worker's thread-local browser (browser_engine._get_shared_browser) is created
once and reused for every paper — no per-paper window flashing. These tests
verify the properties that make that work, without launching real browsers.
"""

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from scansci_pdf.sources import scihub


def _own_close_calls(pool, calls):
    """The close calls made by `pool`'s own workers.

    _close_my_browser resolves `shutdown_shared_browser` when the task *runs*,
    not when it is queued, and _shutdown_scihub_pool queues the close tasks
    with shutdown(wait=False). A task queued by an earlier test in this module
    can therefore still be in flight while a later test measures its own
    shutdown — and when it lands it resolves the very same patched attribute.
    Only the workers of the pool under test may be counted against its bound.
    `pool._threads` is the executor's worker thread set (the module already
    relies on the executor's `pool._max_workers`).
    """
    return [t for t in calls if t in pool._threads]


class PersistentPoolTests(unittest.TestCase):
    def setUp(self):
        # Start every test from a clean slate (pools are module-global).
        scihub._shutdown_scihub_pool()
        self.addCleanup(scihub._shutdown_scihub_pool)

    def test_pool_is_singleton(self):
        p1 = scihub._race_pool({})
        p2 = scihub._race_pool({})
        self.assertIs(p1, p2)

    def test_pool_size_from_config(self):
        pool = scihub._race_pool({"scihub_browser_workers": 2})
        self.assertEqual(pool._max_workers, 2)

    def test_pool_size_fallback_default(self):
        pool = scihub._race_pool({})
        self.assertEqual(pool._max_workers, 3)

    def test_worker_threads_are_reused(self):
        """Few distinct threads across many submissions — the property that
        lets thread-local browsers persist across papers."""
        pool = scihub._race_pool({"scihub_browser_workers": 2})
        idents = {pool.submit(threading.get_ident).result() for _ in range(12)}
        self.assertLessEqual(len(idents), 2, "workers must be reused, not respawned")

    def test_shutdown_resets_pool_and_closes_worker_browsers(self):
        pool = scihub._race_pool({"scihub_browser_workers": 2})
        pool.submit(threading.get_ident).result()  # ensure a worker exists
        calls: list[threading.Thread] = []

        def fake_close():
            calls.append(threading.current_thread())

        with patch("scansci_pdf.browser_engine.shutdown_shared_browser", fake_close):
            # _close_my_browser imports lazily inside the worker; patch the
            # resolved module attribute it will find.
            scihub._shutdown_scihub_pool()
            # The close tasks are queued with shutdown(wait=False) on purpose
            # (issue #57: a worker stuck in an interactive Cloudflare wait must
            # not hang process exit), so they land later, in the pool's
            # workers. The patch has to stay installed until they have run:
            # _close_my_browser resolves shutdown_shared_browser when the task
            # runs, so a task that starts after the patch is gone calls the
            # real function and would never reach `calls` at all.
            #
            # Joining the workers is the deterministic way to get there: the
            # close tasks are queued ahead of the executor's shutdown
            # sentinel, and a worker only exits after it has run them. Polling
            # for "the first call" instead would snapshot the count at an
            # arbitrary moment, which is how the bound below used to pass
            # without ever being enforceable.
            for thread in list(pool._threads):
                thread.join(timeout=5)

            own_calls = _own_close_calls(pool, calls)

        self.assertIsNone(scihub._RACE_POOL)
        # Each worker closed its own browser in its own thread.
        self.assertLessEqual(len(own_calls), 2)
        self.assertTrue(own_calls)

    def test_a_close_task_queued_by_another_pool_is_not_counted_against_this_pool(self):
        """Regression: the shutdown measurement must not see another pool's
        close task.

        _close_my_browser resolves `shutdown_shared_browser` when the task runs,
        not when it is queued. A close task queued by an earlier test in this
        module can still be in flight while this test measures its own
        shutdown, and it resolves the same patched attribute when it lands.
        Counting it against this pool breaks the bound above — that is how the
        macOS CI job failed with "3 not less than or equal to 2".
        """
        foreign = ThreadPoolExecutor(max_workers=1, thread_name_prefix="foreign")
        release = threading.Event()
        try:
            # Occupy the only foreign worker, then queue a close task behind
            # it, so the task is guaranteed to land late — i.e. while this
            # test's patch is installed.
            foreign.submit(release.wait)
            foreign.submit(scihub._close_my_browser)

            pool = scihub._race_pool({"scihub_browser_workers": 2})
            calls: list[threading.Thread] = []

            def fake_close():
                calls.append(threading.current_thread())

            with patch("scansci_pdf.browser_engine.shutdown_shared_browser", fake_close):
                release.set()
                # Shut the foreign pool down so its worker exits after the
                # queued close task instead of blocking on the next item.
                foreign.shutdown(wait=False)
                for thread in list(foreign._threads):
                    thread.join(timeout=5)

            # The foreign task really did resolve the patched attribute ...
            self.assertTrue(calls)
            # ... but it belongs to another pool and must not be counted.
            self.assertEqual(_own_close_calls(pool, calls), [])
        finally:
            release.set()
            foreign.shutdown(wait=False)

    def test_shutdown_is_idempotent(self):
        scihub._shutdown_scihub_pool()
        scihub._shutdown_scihub_pool()  # must not raise
        self.assertIsNone(scihub._RACE_POOL)

    def test_new_pool_after_shutdown(self):
        p1 = scihub._race_pool({})
        scihub._shutdown_scihub_pool()
        p2 = scihub._race_pool({})
        self.assertIsNot(p1, p2)

    def test_browser_available_stays_true_in_pool_worker_after_launch(self):
        """Regression: launching the sync API leaves its dispatcher event loop
        running in the worker thread. The naive asyncio guard used to read
        that as 'user asyncio code' and made _is_browser_available return
        False for every paper after the first — silently degrading whole
        batches to HTTP-only."""
        from scansci_pdf import browser_engine as be

        if not be.is_available({}):
            self.skipTest("no browser backend installed")
        pool = scihub._race_pool({"scihub_browser_workers": 1})
        cfg = {"browser_backend": "patchright", "browser_headless": True}
        try:
            first = pool.submit(scihub._is_browser_available, {"scihub_enabled": True}).result()
            pool.submit(be._get_shared_browser, cfg).result()  # launch in worker
            second = pool.submit(scihub._is_browser_available, {"scihub_enabled": True}).result()
            self.assertTrue(first)
            self.assertTrue(
                second,
                "browser availability must not flip off after the first launch",
            )
        finally:
            pool.submit(scihub._close_my_browser).result()


if __name__ == "__main__":
    unittest.main()
