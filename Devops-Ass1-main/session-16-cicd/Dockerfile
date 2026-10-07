FROM python:3.12-slim
WORKDIR /app
COPY app/ ./app/
RUN useradd --uid 10001 --create-home calc
USER calc
CMD ["python", "app/calculator.py"]
