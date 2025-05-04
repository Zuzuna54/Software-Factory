# infra/docker/node/Dockerfile

FROM node:20-alpine

# Argument to set working directory, defaults to /app
ARG WORKDIR=/app
WORKDIR ${WORKDIR}

# Install system dependencies
RUN apk add --no-cache git

# Install pnpm globally (as per project overview)
RUN npm install -g pnpm

# Copy package management files first for layer caching
COPY frontend/package.json frontend/pnpm-lock.yaml* ${WORKDIR}/

# Install dependencies using pnpm
RUN pnpm install --frozen-lockfile

# Copy the rest of the frontend application code
COPY frontend/ ${WORKDIR}/

# Set environment variables
ENV NODE_ENV=development

# Default command (can be overridden in docker-compose.yml)
# Keeps the container running for exec or development overrides
CMD ["tail", "-f", "/dev/null"] 