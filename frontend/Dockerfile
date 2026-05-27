# Frontend image: Vite-built SPA served by nginx.
# Build context is the repo root so the single repo-root .dockerignore applies.
#   docker build -f frontend/Dockerfile -t news-summarizer-frontend .

# --- Build stage ---------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Serve stage ---------------------------------------------------------------
FROM nginx:alpine

# SPA fallback so client-side routes (/articles/:id, /trending, ...) work on reload
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
