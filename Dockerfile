FROM python:3.11-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 fonts-inter fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY . .

ENV DEMO_MODE=1 STUDIO_HOST=0.0.0.0 STUDIO_PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn studio.app:app --host $STUDIO_HOST --port $STUDIO_PORT"]
