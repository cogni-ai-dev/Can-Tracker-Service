FROM node:22-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

ENV API_UPSTREAM=http://host.docker.internal:8001

COPY docker/can-tracker-frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:8080/health >/dev/null
