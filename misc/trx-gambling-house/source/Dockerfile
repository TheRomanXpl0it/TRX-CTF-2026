FROM debian:trixie-slim AS sui_build

ARG SUI_VERSION=testnet-1.70.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSfL https://raw.githubusercontent.com/MystenLabs/suiup/main/install.sh \
    | SUIUP_INSTALL_DIR=/usr/local/bin sh \
 && suiup install "sui@${SUI_VERSION}" -y \
 && install -Dm755 "/root/.local/share/suiup/binaries/testnet/sui-v${SUI_VERSION#testnet-}" /out/sui \
 && /out/sui --version

FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    cargo \
    gcc \
    git \
    libc6-dev \
    libssl-dev \
    make \
    pkg-config \
    rustc \
    socat \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY --from=sui_build /out/sui /usr/local/bin/sui
COPY contracts/ /app/contracts/
COPY backend/ /app/backend

RUN useradd -m ctf
RUN mkdir -p /state && chown -R ctf:ctf /state /app/contracts

USER ctf

ENTRYPOINT ["/app/backend/entrypoint.sh"]
