FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.txt

COPY app ./app
COPY ui ./ui
COPY prompts ./prompts
COPY data/records.json ./data/records.json
COPY data/raw ./data/raw
COPY data/chroma ./data/chroma
COPY docs ./docs

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
