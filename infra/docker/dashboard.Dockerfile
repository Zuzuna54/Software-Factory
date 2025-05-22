FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci

# Copy project files
COPY dashboard/ ./

# Build the app
RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Command to run the dashboard
CMD ["npm", "run", "start"] 