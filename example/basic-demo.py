from flask import Flask
from prometheus_metrics import PrometheusMetrics
from prometheus_metrics.decorators import do_not_track

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route("/")
def index():
    return "Hello!"


@app.route("/error")
def error():
    raise ValueError(f"this is an error")


@app.route("/err")
@do_not_track()
def not_track_error():
    raise RuntimeError(f"this is an error that isn't tracked")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
