FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
&& apt-get install -y --no-install-recommends chromium chromium-driver \
&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY templates ./templates

RUN useradd -m bot && chown -R bot:bot /app
USER bot

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
