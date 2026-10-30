# Builds the React dashboard and serves it from nginx on Cloud Run.
# Build from the repo root: docker build -f deploy/cloudrun/frontend.Dockerfile --build-arg VITE_API_BASE_URL=<api url> .
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npx vite build

FROM nginx:1.27-alpine
COPY deploy/cloudrun/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
# The nginx image fills ${PORT} into the template at start-up; Cloud Run sets PORT to 8080.
ENV PORT=8080
EXPOSE 8080
