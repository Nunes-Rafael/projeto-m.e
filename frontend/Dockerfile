FROM node:22-alpine

WORKDIR /app
COPY package.json .
COPY server.mjs .
EXPOSE 5173
CMD ["node", "server.mjs"]
