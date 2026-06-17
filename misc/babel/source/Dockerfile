FROM gcc:12-bookworm AS build-readflag

WORKDIR /src

COPY readflag.c ./

RUN mkdir -p /out && \
    gcc -O2 -Wall -Wextra -o /out/readflag readflag.c

FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -M -d /app -s /usr/sbin/nologin ctf

WORKDIR /app

COPY chall.py ./
COPY flag /flag.txt
COPY --from=build-readflag /out/readflag /readflag

RUN printf '%s\n' '#!/bin/sh' 'exec /usr/local/bin/python3.11 -u /app/chall.py' > /app/run && \
    chown -R root:root /app /flag.txt /readflag && \
    chmod 0555 /app/run /app/chall.py && \
    chmod 0400 /flag.txt && \
    chmod 4555 /readflag

USER ctf
EXPOSE 5000

CMD ["socat", "-T", "30", "TCP-LISTEN:5000,reuseaddr,fork", "EXEC:/app/run,stderr"]
