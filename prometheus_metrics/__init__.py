from functools import wraps
import time
from flask import Response, request
from prometheus_client import Histogram, Counter, Gauge
from prometheus_client.exposition import generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.process_collector import ProcessCollector
from prometheus_client.registry import CollectorRegistry


class PrometheusMetrics:
    def __init__(self, app, endpoint="/metrics"):
        self.app = None
        self.endpoint = endpoint
        self.registry = CollectorRegistry()
        MultiProcessCollector(self.registry)
        self._metrics = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.register_endpoint()
        self.load_default_metrics()
        self.register_request_functions()

    def register_endpoint(self):
        @self.do_not_track()
        def metrics_view():
            data = generate_latest(self.registry)
            r = Response(data)
            r.headers.add_header("Content-Type", "text/plain")
            return r

        self.app.add_url_rule(self.endpoint, view_func=metrics_view)

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

        self._register_metric("process_collector", ProcessCollector(registry=self.registry))

    def register_request_functions(self):
        def before_request_func():
            request.start_time = time.perf_counter()

        self.app.before_request(before_request_func)

        def after_request_func(response):
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

        self.app.after_request(after_request_func)

        def teardown_request_func(err):
            if err is None or hasattr(request, "do_not_track"):
                return

            label_values = {
                "method": request.method,
                "path": request.path,
            }
            self._metrics["http_request_exceptions_total"].labels(**label_values).inc()

        self.app.teardown_request(teardown_request_func)

    def _register_metric(self, name, metric):
        if name in self._metrics:
            raise ValueError(f"Metric '{name}' already registered")
        self._metrics[name] = metric

    @staticmethod
    def do_not_track():
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                request.do_not_track = True
                return f(*args, **kwargs)
            return wrapper
        return decorator

    def get_metric(self, name):
        if name not in self._metrics:
            raise ValueError(f"'{name}' metric not found")
        return self._metrics[name]

    def counter(self, name, description, labels=None, after_request_func=lambda x: x.inc()):
        c = Counter(
            name,
            description,
            labelnames=labels.keys() if labels else tuple(),
            registry=self.registry
        )
        return self._add_custom_metric(c, name, labels, after_request_func)

    def gauge(self, name, description, labels=None, after_request_func=lambda x: x.inc()):
        g = Gauge(
            name,
            description,
            labelnames=labels.keys() if labels else tuple(),
            registry=self.registry
        )
        return self._add_custom_metric(g, name, labels, after_request_func)

    def histogram(self, name, description, labels=None, after_request_func=lambda x, t: x.observe(t)):
        h = Histogram(
            name,
            description,
            labelnames=labels.keys() if labels else tuple(),
            registry=self.registry
        )
        return self._add_custom_metric(h, name, labels, after_request_func)

    def _add_custom_metric(self, metric, name, labels, after_request_func):
        self._register_metric(name, metric)

        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                start_time = None

                if isinstance(metric, Histogram) and callable(after_request_func):
                    start_time = time.perf_counter()

                resp = f(*args, **kwargs)

                if isinstance(metric, (Counter, Gauge)) and callable(after_request_func):
                    if labels:
                        after_request_func(metric.labels(**labels))
                    else:
                        after_request_func(metric)

                if isinstance(metric, Histogram) and callable(after_request_func):
                    t = time.perf_counter() - start_time
                    after_request_func(metric, t)

                return resp
            return wrapper
        return decorator
