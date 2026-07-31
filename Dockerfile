# Flask web application (dashboard, equipment, prediction UI, admin).
# Not built/tested in the development sandbox used to write this project —
# provided ready-to-use for local Docker deployment (see docs/08_mlops.md).
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p instance logs app/ml/artifacts

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
