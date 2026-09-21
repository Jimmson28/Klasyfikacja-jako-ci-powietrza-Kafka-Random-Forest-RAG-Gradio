FROM python:3.11-slim

WORKDIR /app

COPY services/processor/requirements.txt ./services/processor/requirements.txt
RUN pip install --no-cache-dir -r services/processor/requirements.txt

COPY common ./common
COPY services/processor ./services/processor

ENV PYTHONUNBUFFERED=1
EXPOSE 8001

CMD ["python", "-m", "services.processor.consumer"]
