# Ankur Saathi: one container with the API and the built app (docs/../deploy/DEPLOY.md).
# Built by Cloud Build from `gcloud run deploy --source .` (no Docker needed on your own machine).

# ---- stage 1: build the app (React + Vite) ---------------------------------------------------------------------------------------
FROM node:20-slim AS pwa
WORKDIR /pwa
COPY pwa/package.json pwa/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY pwa/ ./
# true: the login screen lists the demo accounts for reviewers. Build with --build-arg VITE_DEMO_HINT=false for a real school.
ARG VITE_DEMO_HINT=true
ENV VITE_DEMO_HINT=${VITE_DEMO_HINT}
RUN npm run build

# ---- stage 2: the API, and the built app to serve from the same address --------------------------------------------------------------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# psql: for the one-time database load (deploy/first_setup.sh runs db/setup.sh)
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
# tzdata: Windows and slim images have no time zone database. openpyxl: Excel register uploads (not in requirements.txt).
RUN pip install -r backend/requirements.txt tzdata openpyxl
# the same layout as the repository: the code finds prompts/ and db/seeds/sample_plans relative to itself
COPY backend/app backend/app
COPY prompts prompts
COPY db db
COPY scripts scripts
COPY deploy deploy
COPY --from=pwa /pwa/dist pwa/dist
# a script saved on Windows has CRLF line endings, which Linux reads as part of the command ("$'\r': command not found")
RUN sed -i 's/\r$//' deploy/*.sh db/setup.sh && chmod +x deploy/*.sh db/setup.sh
ENV PWA_DIST=/srv/pwa/dist PORT=8080
WORKDIR /srv/backend
EXPOSE 8080
# one worker: Cloud Run adds containers for more traffic, and each handles many requests at once (the app is async)
CMD ["sh", "-c", "exec uvicorn app.production:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
