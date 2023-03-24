import os
import re

org_dashboard_endpoint = re.compile(r"^/organisations/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/?$")


def sentry_sampler(sampling_context):
    if sampling_context["parent_sampled"]:
        return 1

    if request_uri := sampling_context.get("wsgi_environ", {}).get("PATH_INFO", None):
        if org_dashboard_endpoint.match(request_uri):
            return 1

    return 0


def init_performance_monitoring():
    environment = os.getenv("NOTIFY_ENVIRONMENT").lower()
    enable_apm = environment in {"development", "preview", "staging"}

    if enable_apm and os.getenv("NEW_RELIC_ENABLED") == "1":
        import newrelic.agent

        # Expects NEW_RELIC_LICENSE_KEY set in environment as well.
        newrelic.agent.initialize("newrelic.ini", environment=environment, ignore_errors=False)

    if sentry_dsn := os.getenv("SENTRY_DSN"):
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            debug=False,
            # Disable options while we're only testing the performance monitoring
            # traces_sample_rate=float(os.getenv("SENTRY_SAMPLE_RATE", 0.01)),
            sample_rate=0.0,  # Disable error reporting
            attach_stacktrace=False,
            traces_sampler=sentry_sampler,
            send_default_pii=False,
            request_bodies="never",
        )
