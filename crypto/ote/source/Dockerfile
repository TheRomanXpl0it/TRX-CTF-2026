FROM cybersecnatlab/socaz:ubuntu-noble

RUN apt-get update && apt-get install -y python3-pip

COPY ./requirements.txt ./
RUN pip install -r requirements.txt --break-system-packages

COPY ./server.py /home/user/server
COPY ./gf2.py /home/user/gf2.py
COPY ./channel.py /home/user/channel.py
COPY ./ot.py /home/user/ot.py
COPY ./ote.py /home/user/ote.py

CMD socaz --timeout 300 --flag-from-env FLAG --bind 1337 --cmd "python3 /home/user/server"
