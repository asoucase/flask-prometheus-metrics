FROM python:3.8-alpine
COPY requirements.txt .
COPY prometheus_metrics/ prometheus_metrics/
COPY example/basic-demo.py demo.py
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "demo.py"]