FROM golang:1.26.2-alpine

RUN apk add --no-cache gcc musl-dev socat

RUN adduser -D ctf

ENV LC_ALL=C

WORKDIR /app

COPY runner.go /app/runner.go
COPY readflag.c /app/readflag.c
COPY flag.txt /flag

RUN go build -o /runner /app/runner.go \
    && gcc /app/readflag.c -o /readflag \
    && chown root:root /readflag /flag \
    && chmod 4755 /readflag && chmod 0400 /flag \
    && chmod 0555 /runner

USER ctf

EXPOSE 1337

CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/runner,stderr"]
