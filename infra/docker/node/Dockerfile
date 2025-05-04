FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git

RUN npm install -g \
    next@14 \
    typescript@5.5 \
    eslint@8 \
    prettier@3

ENV NODE_PATH=/app/node_modules
ENV PATH=/app/node_modules/.bin:$PATH 