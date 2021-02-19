FROM python:3.9-slim
LABEL maintainer="Arturo Soucase <arthur@arturosoucase.com>"

# Install gcc in case a pip package requires to be compiled
RUN apt update && apt install -y gcc

# Install uWSGI
RUN pip install uwsgi

# Create low priviledge user
RUN groupadd appuser && useradd -r -g appuser appuser

# Create folder for app_see
RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY prometheus_metrics/ prometheus_metrics/

COPY example/basic-demo.py .
COPY uwsgi/uwsgi.ini .

EXPOSE 6001

CMD ["/usr/local/bin/uwsgi", "--ini", "/app/uwsgi.ini", "--die-on-term"]