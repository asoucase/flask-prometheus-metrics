from flask import Flask
from prometheus_metrics import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route("/")
def index():
    return "Hello!"


@app.route("/error")
def error():
    raise ValueError(f"this is an error")


@app.route("/error")
@metrics.do_not_track()
def do_not_track_error():
    raise RuntimeError(f"this is an error that isn't tracked")


@app.route("/gauge")
@metrics.do_not_track()
@metrics.gauge("task_queue", "Number of tasks in queue", after_request_func=None)
def inc_gauge():
    g = metrics.get_metric("task_queue")
    g.inc()
    return "task added to queue"


@app.route("/counter")
@metrics.counter("my_counter", "Custom counter", labels={'labelA': 'A', 'labelB': 'B'})
def inc_counter():
    return "counter increased by +1"


@app.route("/hist")
@metrics.histogram("my_hist", "Custom histogram")
def obs_hist():
    return "histogram updated"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
