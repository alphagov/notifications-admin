from gunicorn_config import keepalive, timeout, worker_class, workers


def test_gunicorn_config():
    assert workers == 5
    assert worker_class == "notifications_utils.gunicorn.eventlet.OtelAwareEventletWorker"
    assert keepalive == 35
    assert timeout == 30
