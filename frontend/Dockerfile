FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
COPY VERSION /VERSION

ARG VITE_BASE_PATH=/orbvis/
ENV VITE_BASE_PATH=$VITE_BASE_PATH

# BUILD_TARGET=standalone produces a Checkmk-free frontend bundle —
# default for Docker because the container runs without a CMK site.
# Override with --build-arg BUILD_TARGET=cmk to bundle the vendored CMK
# components (only useful when serving alongside an actual Checkmk site).
ARG BUILD_TARGET=standalone
RUN if [ "$BUILD_TARGET" = "standalone" ]; then \
        npm run build:standalone; \
    else \
        npm run build; \
    fi

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
