import time
from flask import Flask, Response, request
from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client import Histogram
from prometheus_metrics.decorators import do_not_track


class PrometheusMetrics:
    def __init__(self, app, endpoint="/metrics"):
        self.app = None
        self.endpoint = endpoint
        self.registry = CollectorRegistry()
        self.metrics = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.register_endpoint()
        self.load_default_metrics()

        assert isinstance(self.app, Flask)
        self.app.before_request(self.before_request_func)
        self.app.after_request(self.after_request_func)

    def register_endpoint(self):
        self.app.add_url_rule(self.endpoint, view_func=self.metrics_view)

    def load_default_metrics(self):
        self.metrics["http_request_duration_seconds"] = Histogram("http_request_duration_seconds",
                                                                  "Flask HTTP request duration in seconds",
                                                                  registry=self.registry)

    @do_not_track()
    def metrics_view(self):
        data = generate_latest(self.registry)
        r = Response(data)
        r.headers.add_header("Content-Type", "text/plain")
        return r

    def before_request_func(self):
        request.start_time = time.time()

    def after_request_func(self, response):
        if hasattr(request, "do_not_track"):
            return response

        latency = time.time() - request.start_time
        self.metrics["http_request_duration_seconds"].observe(latency)
        return response
