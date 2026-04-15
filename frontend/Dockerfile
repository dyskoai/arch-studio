FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/package*.json .
RUN npm ci

COPY frontend/ .

# NEXT_PUBLIC_API_URL is baked into the JS bundle at build time
ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Runtime image ──────────────────────────────────────────────────────────────
FROM node:20-alpine
WORKDIR /app

COPY --from=builder /app/.next/standalone .
COPY --from=builder /app/.next/static     .next/static
COPY --from=builder /app/public           ./public

ENV PORT=3000
ENV NODE_ENV=production

CMD ["node", "server.js"]
