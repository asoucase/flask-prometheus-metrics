from flask import Flask
from prometheus_metrics import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route("/")
def index():
    return "Hello!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
