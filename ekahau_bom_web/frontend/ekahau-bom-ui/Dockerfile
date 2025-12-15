# EkahauBOM Web Frontend Dockerfile
# Build from project root: docker build -f ekahau_bom_web/frontend/ekahau-bom-ui/Dockerfile .

# -----------------------------------
# Build stage
# -----------------------------------
FROM node:22-alpine as builder

WORKDIR /app

# Copy package files first (for layer caching)
COPY ekahau_bom_web/frontend/ekahau-bom-ui/package*.json ./

# Install dependencies
RUN npm ci --prefer-offline

# Copy source code
COPY ekahau_bom_web/frontend/ekahau-bom-ui/ ./

# Build for production
RUN npm run build -- --configuration=production

# -----------------------------------
# Production stage
# -----------------------------------
FROM nginx:alpine as runtime

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY ekahau_bom_web/frontend/ekahau-bom-ui/nginx.conf /etc/nginx/conf.d/

# Copy built Angular app
COPY --from=builder /app/dist/ekahau-bom-ui/browser /usr/share/nginx/html

# Create non-root user for nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/health || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
