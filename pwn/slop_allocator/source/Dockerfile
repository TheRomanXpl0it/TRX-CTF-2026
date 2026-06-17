FROM cybersecnatlab/challenge-jail@sha256:8f6f5cd84a2014f6123d2ae51c19a963c173140c1cba262e4f3fb9ef1c570c74 AS jail

COPY slop /home/user/chall
COPY ld-linux-x86-64.so.2 /home/user/libs/ld-linux.so
COPY libc.so.6 /home/user/libs/libc.so.6

RUN chmod +x-w /home/user/chall /home/user/libs/ld-linux.so /home/user/libs/libc.so.6

ENV TIMEOUT=60
ENV SET_INTERPRETER=/home/user/libs/ld-linux.so
ENV SET_RPATH=/home/user/libs
ENV FLAG=TRX{placeholder}
