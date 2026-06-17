FROM node:latest

WORKDIR /app

COPY package*.json ./

RUN npm install

RUN mkdir /secrets
COPY flag.txt /secrets/super_secret_flag.txt

COPY server.js index.html ./

EXPOSE 3000

CMD ["node", "server.js"]
