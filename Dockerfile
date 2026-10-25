FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MATCHSENSE_DATA_DIR=/app/data \
    MATCHSENSE_NARRATIVE_PROVIDER=template

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime user (guide section 11 container controls)
RUN useradd --create-home --uid 10001 matchsense \
    && chown -R matchsense:matchsense /app
USER matchsense

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

# Default: API. Override command to run the dashboard:
#   docker run -p 8501:8501 matchsense-ai streamlit run src/ui/app.py --server.address 0.0.0.0
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
