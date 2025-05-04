# infra/docker/node/Dockerfile

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache git

# Install pnpm globally (as per project overview)
RUN npm install -g pnpm

# Copy package management files first for layer caching
# Context is now ./dashboard, so copy from the root of the context
COPY package.json pnpm-lock.yaml* ./

# Install dependencies using pnpm
RUN pnpm install --frozen-lockfile

# Copy the rest of the application code from the context root
COPY . .

# Set environment variables
ENV NODE_ENV=development

# Expose port (if needed, typically done in docker-compose)
# EXPOSE 3000

# Default command (can be overridden in docker-compose.yml)
# Example: Run the development server
CMD ["pnpm", "dev"] 