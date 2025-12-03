# Multi-stage build for Next.js application
# Using node:20 (Debian-based) instead of alpine for better compatibility with Next.js/Turbopack

# Stage 1: Dependencies
FROM node:20 AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Create .npmrc for better network reliability during installs
RUN echo "network-timeout=100000" > .npmrc && \
    echo "fetch-retries=3" >> .npmrc && \
    echo "fetch-retry-factor=2" >> .npmrc

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Stage 2: Builder
FROM node:20 AS builder
WORKDIR /app

# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Increase Node.js memory limit for build (helps with large builds)
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variable for build time
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Verify files are copied correctly before building
RUN echo "Files in /app:" && ls -la && \
    echo "Node version:" && node --version && \
    echo "NPM version:" && npm --version && \
    echo "Checking for empty files..." && \
    find . -type f -empty -not -path "./node_modules/*" -not -path "./.next/*" | head -10 || echo "No empty files found"

# Build the application with explicit NODE_ENV
RUN NODE_ENV=production npm run build

# Stage 3: Runner
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN groupadd --system --gid 1001 nodejs && \
    useradd --system --uid 1001 --gid nodejs nextjs

# Copy the standalone output from builder
# The standalone output includes server.js, node_modules, and other required files
# Note: public directory (if it exists) is automatically included in standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

