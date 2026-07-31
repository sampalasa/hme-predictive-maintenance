# Flask web application (dashboard, equipment, prediction UI, admin).
# Not built/tested in the development sandbox used to write this project —
# provided ready-to-use for local Docker deployment (see docs/08_mlops.md).
FROM python:3.10-slim

WORKDIR /app

# libgomp1 is required at runtime by LightGBM/XGBoost on Debian slim images
# (missing it causes "libgomp.so.1: cannot open shared object file").
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p instance logs app/ml/artifacts

# instance/hme.db and app/ml/artifacts/*.joblib are gitignored (not in the
# repository), so on a git-based build (Render, Railway, ...) they must be
# generated at build time. A reduced Optuna trial count keeps the build fast;
# this bakes a working seeded database + trained model into the image itself,
# so the container is immediately functional even on free tiers with an
# ephemeral filesystem (no persistent volume required for a demo/test deploy).
ENV OPTUNA_N_TRIALS=5
RUN python -m app.database.seed && python -m app.ml.training.train_pipeline

EXPOSE 5000

# Shell form (not exec form) so $PORT is expanded — most free PaaS providers
# (Render, Railway, ...) inject their own $PORT and expect the app to bind to it.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 run:app
