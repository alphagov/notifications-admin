import os

if (environment := os.getenv("NOTIFY_ENVIRONMENT")) in {"development", "preview"} and os.getenv(
    "NEW_RELIC_ENABLED"
) == "1":
    import newrelic.agent

    # Expects NEW_RELIC_LICENSE_KEY set in environment as well.
    newrelic.agent.initialize("newrelic.ini", environment=environment, ignore_errors=False)

from flask import Flask

from app import create_app

application = Flask("app")

create_app(application)
