import os

from flask import Flask

if (environment := os.getenv("NOTIFY_ENVIRONMENT")) in {"development", "preview", "staging"} and os.getenv(
    "NEW_RELIC_ENABLED"
) == "1":
    import newrelic.agent

    # Expects NEW_RELIC_LICENSE_KEY set in environment as well.
    newrelic.agent.initialize("newrelic.ini", environment=environment, ignore_errors=False)

from app import create_app

application = Flask("app")

create_app(application)
