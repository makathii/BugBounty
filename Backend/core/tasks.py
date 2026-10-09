"""
Helpers for dispatching Celery tasks from request/signal code.
"""
from django.conf import settings
from django.db import transaction


def enqueue_after_commit(task, *args, **kwargs):
    """
    Run ``task`` once the surrounding transaction has committed.

    * With a broker configured, the task is sent with ``on_commit`` so a worker
      never runs against rows that are not visible yet (and never runs at all if
      the transaction rolls back).
    * Without a broker (``CELERY_TASK_ALWAYS_EAGER``: local dev, tests) the task
      runs inline immediately, preserving the previous synchronous behaviour.

    Broker outages must not break the request that triggered the task, so a
    failed publish is logged and swallowed by ``_publish``.
    """
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        task.apply(args=args, kwargs=kwargs, throw=True)
        return
    transaction.on_commit(lambda: _publish(task, args, kwargs))


def _publish(task, args, kwargs):
    import logging
    try:
        task.apply_async(args=args, kwargs=kwargs)
    except Exception:  # broker down: log, do not fail the request
        logging.getLogger(__name__).exception("Could not enqueue %s", task.name)
