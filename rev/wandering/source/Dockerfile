FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends socat \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY vm /app/vm
COPY run.sh /app/run.sh
COPY flag.txt /flag.txt

RUN chmod +x /app/vm /app/run.sh

EXPOSE 1337
ENTRYPOINT ["socat", "-T", "60", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/app/run.sh,stderr"]
