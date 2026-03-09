FROM node:22-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install --frozen-lockfile

COPY . .
ARG VITE_BASE_PATH=/orbvis/
ENV VITE_BASE_PATH=$VITE_BASE_PATH
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
