FROM ruby:alpine

RUN apk add --no-cache \
    whois \
    build-base \
    gcc

WORKDIR /app

COPY readflag.c /tmp/readflag.c
RUN gcc -O2 -Wall -Wextra -o /readflag /tmp/readflag.c && \
    chown root:root /readflag && \
    chmod 4755 /readflag && \
    rm -f /tmp/readflag.c

COPY flag.txt /flag.txt
RUN chown root:root /flag.txt && chmod 0400 /flag.txt

RUN gem install sinatra thin rackup puma

COPY . .

EXPOSE 4567

CMD ["ruby", "app.rb", "-o", "0.0.0.0"]
