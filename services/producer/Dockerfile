FROM python:3.11-slim

WORKDIR /app

COPY services/producer/requirements.txt ./services/producer/requirements.txt
RUN pip install --no-cache-dir -r services/producer/requirements.txt

COPY common ./common
COPY services/producer ./services/producer

ENV PYTHONUNBUFFERED=1
EXPOSE 8002

CMD ["python", "-m", "services.producer.producer"]
