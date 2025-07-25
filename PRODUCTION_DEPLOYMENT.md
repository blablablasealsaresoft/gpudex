# 🚀 GPUDex Production Deployment Guide

Complete enterprise-grade deployment guide for GPUDex - The GPU Price Aggregation Platform.

## 📋 Table of Contents

- [🎯 Overview](#overview)
- [🔧 Prerequisites](#prerequisites)
- [🏗️ Architecture](#architecture)
- [🚀 Quick Start](#quick-start)
- [🔐 Security Configuration](#security-configuration)
- [💳 Payment Integration](#payment-integration)
- [📊 Monitoring & Analytics](#monitoring--analytics)
- [🔄 CI/CD Pipeline](#cicd-pipeline)
- [🛠️ Troubleshooting](#troubleshooting)
- [📈 Scaling](#scaling)

## 🎯 Overview

GPUDex is a production-ready, enterprise-grade GPU price aggregation platform featuring:

### 🌟 Core Features
- **Real-time Price Aggregation** from 13+ providers
- **Intelligent Caching** with Redis for performance
- **Advanced Security** with input validation & rate limiting
- **User Authentication** with JWT and session management
- **Stripe Payment Integration** for subscription billing
- **Interactive Analytics** with price history and trends
- **Mobile-Optimized UI** with responsive design
- **RESTful API** with comprehensive documentation

### 🏢 Enterprise Features
- **Multi-tier Subscriptions** (Free, Basic, Pro, Enterprise)
- **API Rate Limiting** with usage tracking
- **Real-time Alerts** via email notifications
- **Arbitrage Detection** for price optimization
- **Advanced Filtering** by specs, location, availability
- **Comprehensive Monitoring** with health checks
- **Docker Containerization** for consistent deployment
- **Production Security** headers and vulnerability protection

## 🔧 Prerequisites

### System Requirements
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 20GB+ SSD
- **OS**: Linux (Ubuntu 20.04+), Windows 10+, or macOS 10.15+

### Required Software
- **Docker** 20.10+ & **Docker Compose** 2.0+
- **Git** 2.30+
- **Node.js** 16+ (for development)
- **Python** 3.11+ (for testing scripts)

### External Services
- **PostgreSQL** 15+ (managed or self-hosted)
- **Redis** 6.0+ (for caching)
- **SendGrid** account (for emails)
- **Stripe** account (for payments)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     Frontend    │    │     Backend     │
│   (Nginx/ALB)   │◄───┤  (React/HTML)   │◄───┤   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │      Redis      │◄────────────┤
                       │   (Caching)     │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   PostgreSQL    │◄────────────┤
                       │   (Database)    │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │  External APIs  │◄────────────┘
                       │ (GPU Providers) │
                       └─────────────────┘
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/blablablasealsaresoft/gpudex.git
cd gpudex
```

### 2. Environment Configuration
```bash
# Copy production environment template
cp env.production .env

# Edit configuration with your values
nano .env
```

### 3. Configure Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://gpudex:SECURE_PASSWORD@postgres:5432/gpudex_db
POSTGRES_DB=gpudex_db
POSTGRES_USER=gpudex
POSTGRES_PASSWORD=SECURE_PASSWORD_HERE

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Security Configuration
JWT_SECRET_KEY=GENERATE_SECURE_JWT_SECRET_HERE
SECRET_KEY=GENERATE_SECURE_SECRET_KEY_HERE

# Email Configuration (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key_here
FROM_EMAIL=alerts@yourdomain.com

# Payment Configuration (Stripe)
STRIPE_PUBLISHABLE_KEY=pk_live_your_key_here
STRIPE_SECRET_KEY=sk_live_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# API Keys for Providers
VAST_AI_API_KEY=your_vast_api_key
RUNPOD_API_KEY=your_runpod_api_key
TENSORDOCK_API_KEY=your_tensordock_api_key
LAMBDA_LABS_API_KEY=your_lambda_api_key
PAPERSPACE_API_KEY=your_paperspace_api_key
```

### 4. Deploy with Docker
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Initialize Database
```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend python -c "
from database import DatabaseManager
db = DatabaseManager()
db.create_tables()
print('Database initialized successfully!')
"
```

### 6. Verify Deployment
```bash
# Install test dependencies
pip install aiohttp

# Run production tests
python test_production.py

# Manual health check
curl http://localhost:8000/
```

## 🔐 Security Configuration

### SSL/TLS Setup
```bash
# Generate SSL certificates (Let's Encrypt)
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# Update nginx configuration
# Add SSL configuration to frontend/nginx.prod.conf
```

### Firewall Configuration
```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### Security Headers
The platform automatically includes production security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security`
- `Content-Security-Policy`

### Rate Limiting
- **Public API**: 100 requests/hour, 10 requests/minute burst
- **Authenticated**: Higher limits based on subscription tier
- **Automatic IP blocking** for abuse

## 💳 Payment Integration

### Stripe Configuration
1. **Create Stripe Products**:
   ```bash
   # Create subscription products in Stripe Dashboard
   # Basic Plan: $29/month
   # Pro Plan: $99/month  
   # Enterprise Plan: $299/month
   ```

2. **Configure Webhooks**:
   ```
   Endpoint URL: https://yourdomain.com/api/v1/stripe/webhook
   Events: customer.subscription.*, invoice.payment.*, payment_intent.*
   ```

3. **Test Payment Flow**:
   ```bash
   # Use Stripe test cards
   # 4242424242424242 (Visa)
   # 4000000000000002 (Declined)
   ```

### Subscription Tiers
- **Free**: 100 API calls/month, basic features
- **Basic**: 1,000 API calls/month, advanced filtering
- **Pro**: 10,000 API calls/month, arbitrage detection
- **Enterprise**: Unlimited calls, custom features

## 📊 Monitoring & Analytics

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/v1/analytics

# Cache performance
curl http://localhost:8000/api/v1/cache/stats
```

### Monitoring Endpoints
- `/health` - Basic application health
- `/api/v1/system/stats` - System performance metrics
- `/api/v1/cache/stats` - Redis cache statistics
- `/api/v1/usage/stats` - API usage analytics

### Log Monitoring
```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs backend

# Nginx access logs
docker-compose -f docker-compose.prod.yml logs frontend

# Database logs
docker-compose -f docker-compose.prod.yml logs postgres
```

### Performance Metrics
- **Response Times**: < 500ms average
- **Cache Hit Rate**: > 80%
- **Uptime**: 99.9% target
- **Error Rate**: < 1%

## 🔄 CI/CD Pipeline

### GitHub Actions Setup
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: python test_production.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Server
        run: ./deploy_production.sh
```

### Automated Testing
```bash
# Unit tests
python -m pytest backend/tests/

# Integration tests
python test_production.py

# Security scan
bandit -r backend/

# Dependency audit
pip-audit
```

### Deployment Process
1. **Code Review** & approval
2. **Automated Testing** (unit, integration, security)
3. **Staging Deployment** for final validation
4. **Production Deployment** with zero downtime
5. **Health Checks** & rollback if needed

## 🛠️ Troubleshooting

### Common Issues

#### 🔴 Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml logs postgres

# Verify connection string
docker-compose -f docker-compose.prod.yml exec backend python -c "
import os
print('DB URL:', os.getenv('DATABASE_URL'))
"

# Reset database
docker-compose -f docker-compose.prod.yml down
docker volume rm gpudex_postgres_data
docker-compose -f docker-compose.prod.yml up -d
```

#### 🔴 Redis Connection Issues
```bash
# Check Redis status
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Clear cache
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

#### 🔴 High Memory Usage
```bash
# Monitor container resources
docker stats

# Optimize cache settings
# Edit redis.conf: maxmemory 512mb
```

#### 🔴 SSL Certificate Issues
```bash
# Renew Let's Encrypt certificates
certbot renew

# Check certificate status
openssl x509 -in /path/to/cert.pem -text -noout
```

### Performance Optimization

#### Backend Optimization
```bash
# Increase worker count
WORKERS=4

# Enable caching
REDIS_URL=redis://redis:6379/0

# Optimize database queries
ENABLE_QUERY_LOGGING=true
```

#### Frontend Optimization
```bash
# Enable Nginx caching
# Configure in frontend/nginx.prod.conf

# Compress assets
gzip on;
gzip_types text/css application/javascript;
```

### Debug Mode
```bash
# Enable debug logging
DEBUG=true
LOG_LEVEL=debug

# Restart with debug enabled
docker-compose -f docker-compose.prod.yml restart backend
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Load balancer configuration
# Configure nginx upstream for multiple backends
```

### Database Scaling
```bash
# Read replicas
# Configure PostgreSQL read replicas for analytics queries

# Connection pooling
# Use PgBouncer for connection management
```

### Cache Scaling
```bash
# Redis cluster
# Configure Redis Cluster for high availability

# Cache warming
# Implement cache pre-warming for popular data
```

### CDN Integration
```bash
# Static assets via CDN
# Configure CloudFront/CloudFlare for frontend assets

# API caching
# Use CDN edge caching for public API endpoints
```

### Monitoring & Alerting
```bash
# Prometheus metrics
# Configure metrics collection

# Grafana dashboards
# Set up monitoring dashboards

# PagerDuty alerts
# Configure critical alerts
```

---

## 🎉 Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database migrations completed
- [ ] Redis cache configured
- [ ] Stripe webhooks configured
- [ ] SendGrid email templates setup
- [ ] Health checks passing
- [ ] Security tests passing
- [ ] Performance benchmarks met
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Documentation updated

## 📞 Support

For production support:
- 📧 Email: support@gpudex.com
- 📞 Phone: Available for Enterprise customers
- 💬 Slack: Enterprise support channel
- 🐛 Issues: GitHub Issues for bug reports

## 📄 License

Copyright © 2024 GPUDex. All rights reserved. 