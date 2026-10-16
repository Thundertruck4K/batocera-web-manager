"""Tests de idempotencia/concurrencia de `_start_batch_worker`.

Antes, dos peticiones HTTP concurrentes podían pasar la comprobación
"¿worker vivo?" al mismo tiempo y arrancar dos workers (race "check-then-act").
"""
from __future__ import annotations

import threading as th


def test_concurrent_calls_produce_single_worker(appmod):
    appmod._scraper_worker_thread = None

    n = 8
    barrier = th.Barrier(n)
    results: list = []
    guard = th.Lock()

    def call():
        barrier.wait()  # fuerza el solape máximo de las llamadas
        t = appmod._start_batch_worker()
        with guard:
            results.append(t)

    workers = [th.Thread(target=call) for _ in range(n)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()

    assert len(results) == n
    assert all(r is results[0] for r in results), "todas deben obtener el mismo worker"
    assert appmod._scraper_worker_thread is results[0]


def test_second_call_is_idempotent(appmod):
    appmod._scraper_worker_thread = None
    first = appmod._start_batch_worker()
    second = appmod._start_batch_worker()
    assert second is first
