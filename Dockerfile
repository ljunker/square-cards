FROM python:3.13-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}"

COPY pyproject.toml README.md app.py ./
COPY square_cards ./square_cards

RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir .


FROM python:3.13-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN adduser -D -h /app appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

COPY --from=builder /opt/venv /opt/venv

USER appuser

EXPOSE 8000
VOLUME ["/app/data"]

CMD ["square-cards", "--host", "0.0.0.0", "--port", "8000", "--workspace", "/app"]
