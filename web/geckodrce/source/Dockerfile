FROM alpine:3.23 AS readflag-builder

RUN apk add --no-cache build-base
COPY readflag.c /tmp/readflag.c
RUN gcc /tmp/readflag.c -o /readflag && strip /readflag

FROM python:3.14-alpine

RUN adduser -D bot

WORKDIR /bot/

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY flag.txt /flag.txt
RUN chown root:root /flag.txt && chmod 400 /flag.txt
COPY --from=readflag-builder /readflag /readflag
RUN chown root:root /readflag && chmod 4755 /readflag

COPY requirements.txt /bot/requirements.txt
RUN pip install --no-cache-dir -r /bot/requirements.txt
RUN apk add --no-cache firefox geckodriver

COPY bot.py /bot/bot.py

USER bot
CMD ["python", "-m", "uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "3000"]
