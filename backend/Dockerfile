FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer -- only re-runs when
# requirements.txt actually changes, not on every code edit)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary

COPY app ./app

EXPOSE 8123

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8123"]


