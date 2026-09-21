FROM python:3.11-slim

WORKDIR /app

COPY services/api/requirements.txt ./services/api/requirements.txt

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r services/api/requirements.txt

COPY common ./common
COPY services/api ./services/api
COPY data ./data

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
