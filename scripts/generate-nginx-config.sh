#!/bin/bash
# Script to generate nginx configuration with dynamic IP binding

set -e

# Default values
PROJECT_IP="${PROJECT_IP:-0.0.0.0}"
NGINX_CONFIG_FILE="${NGINX_CONFIG_FILE:-nginx.conf}"

echo "Generating nginx configuration with PROJECT_IP: $PROJECT_IP"

# Create nginx configuration with dynamic IP binding
cat > "$NGINX_CONFIG_FILE" << EOF
events {
    worker_connections 1024;
}

http {
    upstream ai_service {
        server ai-service:8000;
    }

    upstream elasticsearch {
        server elasticsearch:9200;
    }

    upstream kibana {
        server kibana:5601;
    }

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=search:10m rate=5r/s;

    # Logging
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # AI Service API
    server {
        listen $PROJECT_IP:80;
        server_name localhost;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Health check endpoint
        location /health {
            proxy_pass http://ai_service;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Search API with rate limiting
        location /api/v1/search {
            limit_req zone=search burst=20 nodelay;
            proxy_pass http://ai_service;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # General API with rate limiting
        location /api/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://ai_service;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Metrics endpoint
        location /metrics {
            proxy_pass http://ai_service;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Default location
        location / {
            proxy_pass http://ai_service;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }

    # Elasticsearch (for development only)
    server {
        listen $PROJECT_IP:9201;
        server_name localhost;

        location / {
            proxy_pass http://elasticsearch;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }

    # Kibana (for monitoring)
    server {
        listen $PROJECT_IP:5602;
        server_name localhost;

        location / {
            proxy_pass http://kibana;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

echo "✅ Nginx configuration generated successfully"
echo "📁 Configuration file: $NGINX_CONFIG_FILE"
echo "🌐 Binding to IP: $PROJECT_IP"
