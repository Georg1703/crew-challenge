from celery import shared_task


@shared_task(name="core.ping")
def ping() -> str:
    """Proves the worker is connected to the broker. Used by health tooling and tests."""
    return "pong"
