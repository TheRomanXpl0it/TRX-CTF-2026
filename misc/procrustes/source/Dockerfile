FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/chall.py /app/chall.py
COPY flag /app/flag

RUN chmod 0555 /app/chall.py && \
    chmod 0444 /app/flag

ENV PYTHONUNBUFFERED=1

USER nobody:nogroup

EXPOSE 5000

CMD ["socat", "-T30", "TCP-LISTEN:5000,reuseaddr,fork", "EXEC:timeout 30 /usr/local/bin/python3.11 /app/chall.py,stderr"]
