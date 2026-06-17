FROM cybersecnatlab/challenge-jail@sha256:bdb4f33f2c4604c8818b86fc7d52ce50c047a9556b43a8005c3d61ca1622dd43

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && apt-get install -y \
    --no-install-recommends --no-install-suggests \
    wget gpg ca-certificates

RUN mkdir -pm755 /etc/apt/keyrings

RUN wget -O - https://dl.winehq.org/wine-builds/winehq.key | sudo gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key -
RUN wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources

RUN dpkg --add-architecture i386
RUN apt-get update -y && apt-get install -y \
    --no-install-recommends --no-install-suggests \
    winehq-stable

USER user
RUN wineboot 2>/dev/null && \
    rm /home/user/.wine/drive_c/windows/system32/*.exe /home/user/.wine/drive_c/windows/syswow64/*.exe

USER 0

RUN apt-get remove -y \
    --no-install-recommends --no-install-suggests \
    wget gpg ca-certificates && \
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/* && \
    rm -rf /etc/apt/keyrings/winehq-archive.key && rm -rf /etc/apt/sources.list.d/winehq-noble.sources

CMD ["/usr/bin/wine", "chall.exe"]
