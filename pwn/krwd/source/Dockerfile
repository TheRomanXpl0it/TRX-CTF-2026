FROM ubuntu:25.04

# Update and install packages
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    qemu-system-x86 \
    python3 \
    socat

# Copy challenge entrypoint
COPY bzImage /opt/
COPY initramfs.cpio.gz/ /opt/initramfs.cpio.gz
COPY run.sh /opt/
COPY run.py /opt/
COPY hashcash.py /opt/
COPY flag.txt /opt/

RUN chmod +x /opt/run.sh
RUN chmod +x /opt/run.py
RUN chmod +x /opt/hashcash.py

WORKDIR /opt/


# Socat listening port
EXPOSE 1337

# Change entrypoint to launch challenge
CMD ["socat", "TCP-LISTEN:1337,reuseaddr", "EXEC:./run.py"]