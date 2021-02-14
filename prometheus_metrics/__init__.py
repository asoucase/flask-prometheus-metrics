import time
from flask import Response, request
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client import Histogram, Counter
from prometheus_metrics.decorators import do_not_track


class PrometheusMetrics:
    def __init__(self, app, endpoint="/metrics"):
        self.app = None
        self.endpoint = endpoint
        self.registry = CollectorRegistry()
        self._metrics = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.register_endpoint()
        self.load_default_metrics()

        self.app.before_request(self.before_request_func)
        self.app.after_request(self.after_request_func)
        self.app.teardown_request(self.teardown_request_func)

    def register_endpoint(self):
        self.app.add_url_rule(self.endpoint, view_func=self.metrics_view)

    def load_default_metrics(self):
        labels = ("method", "path", "status")

        request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "Flask HTTP request duration in seconds",
            labelnames=labels,
            registry=self.registry
        )
        self._register_metric("http_request_duration_seconds", request_duration_seconds)

        request_total = Counter(
            "http_requests_total",
            "Total number of requests",
            labelnames=labels,
            registry=self.registry
        )
        self._register_metric("http_requests_total", request_total)

        request_exceptions_total = Counter(
            "http_request_exceptions_total",
            "Total number of HTTP requests which resulted in an exception",
            labelnames=("method", "path"),
            registry=self.registry
        )
        self._register_metric("http_request_exceptions_total", request_exceptions_total)

    def _register_metric(self, name, metric):
        if name in self._metrics:
            raise ValueError(f"Metric '{name}' already registered")
        self._metrics[name] = metric

    @do_not_track()
    def metrics_view(self):
        data = generate_latest(self.registry)
        r = Response(data)
        r.headers.add_header("Content-Type", "text/plain")
        return r

    def before_request_func(self):
        request.start_time = time.perf_counter()

    def after_request_func(self, response):
        if hasattr(request, "do_not_track"):
            return response

        latency = time.perf_counter() - request.start_time
        latency_labels = {
           "method": request.method,
           "path": request.path,
           "status": response.status_code
        }

        self._metrics["http_request_duration_seconds"].labels(**latency_labels).observe(latency)
        self._metrics["http_requests_total"].labels(**latency_labels).inc()

        return response

    def teardown_request_func(self, err):
        if err is None or hasattr(request, "do_not_track"):
            return

        label_values = {
            "method": request.method,
            "path": request.path,
        }
        self._metrics["http_request_exceptions_total"].labels(**label_values).inc()
