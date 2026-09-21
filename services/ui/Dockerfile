FROM python:3.11-slim

WORKDIR /app

COPY services/ui/requirements.txt ./services/ui/requirements.txt
RUN pip install --no-cache-dir -r services/ui/requirements.txt

COPY common ./common
COPY services/ui ./services/ui

ENV PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["python", "-m", "services.ui.app"]
