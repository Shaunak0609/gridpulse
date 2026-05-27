# ════════════════════════════════════════════════════════════════════════════════
# Stage 1 — Build
# ════════════════════════════════════════════════════════════════════════════════
# node:20-slim gives us Node 20 LTS on a minimal Debian base.
FROM node:20-slim AS builder

# All build commands run inside /app.
WORKDIR /app

# Copy package files first so Docker can cache the npm install layer.
# If only source files change, this layer is reused and npm ci is skipped.
COPY package.json package-lock.json ./

# Install exact versions from package-lock.json.
# "ci" (clean install) is faster and stricter than "npm install" — it never
# modifies package-lock.json and fails if the lockfile is out of date.
RUN npm ci

# ── API URL ───────────────────────────────────────────────────────────────────
# Vite bakes environment variables into the JS bundle at build time, not at
# runtime. VITE_API_URL must be set before "npm run build" runs.
# ARG lets you pass a value at build time: docker build --build-arg VITE_API_URL=...
# ENV makes the ARG visible to the Vite build process.
# The default (http://localhost:8000) works when testing the image locally.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

# Copy the rest of the frontend source code.
# node_modules/ is excluded by .dockerignore — we already installed them above.
COPY . .

# Compile TypeScript and bundle everything into the dist/ folder.
RUN npm run build

# ════════════════════════════════════════════════════════════════════════════════
# Stage 2 — Serve
# ════════════════════════════════════════════════════════════════════════════════
# Start fresh from a tiny nginx image — the final image contains only nginx
# and the compiled static files, not Node, npm, or any source code.
FROM nginx:alpine

# Copy the compiled output from the builder stage.
COPY --from=builder /app/dist /usr/share/nginx/html

# Replace nginx's default config with ours.
# The key addition is "try_files $uri /index.html" for SPA routing.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx listens on port 80 by default.
EXPOSE 80

# "daemon off" keeps nginx running in the foreground so Docker can manage it.
CMD ["nginx", "-g", "daemon off;"]
