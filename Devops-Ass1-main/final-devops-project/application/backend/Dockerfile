FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd --uid 10001 --no-create-home api
USER api

EXPOSE 8000
# migrations run separately: python -m app.migrate (compose service / Helm initContainer)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
