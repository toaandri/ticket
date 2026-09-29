# =============================================================================
# Web frontend Dockerfile — Vite dev server
# =============================================================================
FROM node:20-alpine AS dev

WORKDIR /app

COPY web/package.json web/package-lock.json* ./
RUN npm ci

COPY web/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
