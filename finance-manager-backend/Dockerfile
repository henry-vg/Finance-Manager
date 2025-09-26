FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade "pip==25.2" \
 && python -m pip install -r requirements.txt

COPY . .

RUN useradd -r -u 10001 -g root appuser && chown -R appuser:root /app
USER appuser

EXPOSE 8000

CMD ["python", "main.py"]
