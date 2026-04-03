FROM node:20-bookworm-slim AS base

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


FROM base AS e2e

RUN npx playwright install --with-deps chromium

CMD ["npm", "run", "test:e2e:ci"]
