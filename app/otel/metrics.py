from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource


class Metrics:
    def __init__(self):
        self.meter = None
        self.default_histogram_bucket = [
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
            float("inf"),
        ]

    def init_app(self, app):
        export_mode = app.config.get("OTEL_EXPORT_TYPE", "none").lower()
        metric_readers = []

        if export_mode == "console":
            app.logger.info("OpenTelemetry metrics will be exported to console")
            metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        elif export_mode == "otlp":
            endpoint = app.config.get("OTEL_COLLECTOR_ENDPOINT", "localhost:4317")
            app.logger.info("OpenTelemetry metrics will be exported to OTLP collector at %s", endpoint)
            otlp_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
            # Metrics will be exported every 60 seconds with a 30 seconds timeout by default.
            # The following environments variables can be used to change this:
            # OTEL_METRIC_EXPORT_INTERVAL
            # OTEL_METRIC_EXPORT_TIMEOUT
            metric_readers.append(PeriodicExportingMetricReader(otlp_exporter))

        resource = Resource.create({"service.name": "notifications-api"})
        provider = MeterProvider(metric_readers=metric_readers, resource=resource)
        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(__name__)

        self.create_counters()
        self.create_histograms()
        self.create_gauges()

    def create_counters(self):
        pass

    def create_histograms(self):
        pass

    def create_gauges(self):
        pass


# Initialize the metrics instance singleton
otel_metrics = Metrics()
