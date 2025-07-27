# GPUDex Production Deployment Guide

Complete guide for deploying GPUDex as a production-ready, enterprise-grade, decentralized GPU rental platform.

## 🏗️ **System Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │ Smart Contracts │
│   (React/Vue)   │◄──►│   (FastAPI)     │◄──►│   (Ethereum)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Wallet Connect  │    │   PostgreSQL    │    │   Provider      │
│ (MetaMask, etc) │    │   Redis Cache   │    │   APIs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 **Prerequisites**

### **System Requirements**
- **Server**: 8+ GB RAM, 4+ CPU cores, 100+ GB SSD
- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **Docker**: 20.10+ with Docker Compose
- **Node.js**: 18+ (for smart contract deployment)
- **Python**: 3.9+ (for backend)

### **External Services**
- **Domain & SSL**: Registered domain with SSL certificate
- **Database**: PostgreSQL 13+ (or managed service like AWS RDS)
- **Blockchain Node**: Infura, Alchemy, or self-hosted Ethereum node
- **Email Service**: SendGrid, AWS SES, or similar
- **Monitoring**: Grafana Cloud or self-hosted

---

## 🚀 **Phase 1: Smart Contract Deployment**

### **1.1 Setup Development Environment**

```bash
# Install Node.js and dependencies
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Create smart contract project
mkdir gpudex-contracts && cd gpudex-contracts
npm init -y
npm install hardhat @openzeppelin/contracts @nomiclabs/hardhat-ethers ethers

# Initialize Hardhat
npx hardhat
```

### **1.2 Configure Hardhat**

Create `hardhat.config.js`:

```javascript
require("@nomiclabs/hardhat-ethers");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    // Polygon Mainnet (recommended for lower fees)
    polygon: {
      url: "https://polygon-rpc.com/",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 35000000000
    },
    // Ethereum Mainnet
    mainnet: {
      url: `https://mainnet.infura.io/v3/${process.env.INFURA_KEY}`,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      gasPrice: 20000000000
    },
    // Testnets
    mumbai: {
      url: "https://rpc-mumbai.maticvigil.com/",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    }
  }
};
```

### **1.3 Deploy Smart Contracts**

Create deployment script `scripts/deploy.js`:

```javascript
async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with account:", deployer.address);
    
    // Deploy GPUDex Token
    const GPUDexToken = await ethers.getContractFactory("GPUDexToken");
    const token = await GPUDexToken.deploy(deployer.address);
    await token.deployed();
    console.log("GPUDexToken deployed to:", token.address);
    
    // Deploy Escrow Contract
    const GPUDexEscrow = await ethers.getContractFactory("GPUDexEscrow");
    const escrow = await GPUDexEscrow.deploy(deployer.address, token.address);
    await escrow.deployed();
    console.log("GPUDexEscrow deployed to:", escrow.address);
    
    // Save deployment info
    const deployments = {
        network: network.name,
        token: token.address,
        escrow: escrow.address,
        deployer: deployer.address,
        timestamp: new Date().toISOString()
    };
    
    require('fs').writeFileSync(
        `deployments-${network.name}.json`, 
        JSON.stringify(deployments, null, 2)
    );
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
```

Deploy to testnet first:
```bash
# Set environment variables
export DEPLOYER_PRIVATE_KEY="your_private_key"
export INFURA_KEY="your_infura_key"

# Deploy to Mumbai testnet
npx hardhat run scripts/deploy.js --network mumbai

# Deploy to Polygon mainnet
npx hardhat run scripts/deploy.js --network polygon
```

---

## 🛠️ **Phase 2: Backend Infrastructure**

### **2.1 Environment Setup**

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gpudex_prod
REDIS_URL=redis://localhost:6379/0

# Blockchain
WEB3_PROVIDER_URL=https://polygon-rpc.com/
ESCROW_CONTRACT_ADDRESS=0x...
TOKEN_CONTRACT_ADDRESS=0x...
DEPLOYER_PRIVATE_KEY=your_private_key

# Provider APIs
VAST_API_KEY=your_vast_api_key
RUNPOD_API_KEY=your_runpod_api_key
LAMBDA_API_KEY=your_lambda_api_key

# External Services
SENDGRID_API_KEY=your_sendgrid_key
STRIPE_SECRET_KEY=your_stripe_key
COINGATE_API_KEY=your_coingate_key

# Security
JWT_SECRET=your_jwt_secret_256_bits
API_ENCRYPTION_KEY=your_encryption_key

# Rate Limiting
REDIS_URL=redis://localhost:6379
RATE_LIMIT_ENABLED=true

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

### **2.2 Database Setup**

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE gpudex_prod;
CREATE USER gpudex WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE gpudex_prod TO gpudex;

# Run schema migrations
psql -U gpudex -d gpudex_prod -f backend/init.sql
psql -U gpudex -d gpudex_prod -f backend/enterprise_db_schema.sql
```

### **2.3 Docker Production Setup**

Update `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.prod
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    env_file: .env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gpudex"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 🔐 **Phase 3: Security & Authentication**

### **3.1 SSL Certificate Setup**

```bash
# Install Certbot
sudo apt install certbot

# Get SSL certificate
sudo certbot certonly --standalone -d api.gpudex.com -d app.gpudex.com

# Setup auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **3.2 Nginx Configuration**

Create `nginx.prod.conf`:

```nginx
server {
    listen 80;
    server_name app.gpudex.com api.gpudex.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.gpudex.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl http2;
    server_name api.gpudex.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}
```

### **3.3 Firewall Setup**

```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 📊 **Phase 4: Monitoring & Analytics**

### **4.1 Prometheus Configuration**

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'gpudex-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    
  - job_name: 'gpudex-frontend'
    static_configs:
      - targets: ['frontend:80']
      
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
```

### **4.2 Grafana Dashboard**

Import dashboard JSON:

```json
{
  "dashboard": {
    "title": "GPUDex Production Metrics",
    "panels": [
      {
        "title": "API Requests per Minute",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[1m])",
            "legend": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "GPU Rentals Created",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(gpu_rentals_created_total[24h])"
          }
        ]
      },
      {
        "title": "Provider Response Times",
        "type": "heatmap",
        "targets": [
          {
            "expr": "provider_response_time_seconds"
          }
        ]
      }
    ]
  }
}
```

---

## 💰 **Phase 5: Provider Integrations**

### **5.1 Provider API Keys Setup**

```bash
# Vast.ai
# 1. Sign up at console.vast.ai
# 2. Generate API key in account settings
# 3. Add to environment: VAST_API_KEY=

# RunPod
# 1. Sign up at runpod.io
# 2. Generate API key in settings
# 3. Add to environment: RUNPOD_API_KEY=

# Lambda Labs
# 1. Sign up at lambdalabs.com
# 2. Request API access
# 3. Add to environment: LAMBDA_API_KEY=
```

### **5.2 Provider Integration Testing**

```python
# Test script
import asyncio
from real_provider_integrations import provider_aggregator

async def test_providers():
    instances = await provider_aggregator.get_all_instances()
    print(f"Found {len(instances)} GPU instances")
    
    for instance in instances[:5]:
        print(f"{instance.provider}: {instance.gpu_type} - ${instance.price_per_hour}/hr")

asyncio.run(test_providers())
```

---

## 🎛️ **Phase 6: Enterprise API Management**

### **6.1 Create Default Organization**

```python
# Run in production environment
from enterprise_api_management import enterprise_api_manager

# Create default organization
org = await enterprise_api_manager.create_organization(
    name="GPUDex Platform",
    owner_email="admin@gpudex.com",
    plan="enterprise"
)

print(f"Organization created: {org['organization_id']}")
```

### **6.2 API Key Management Setup**

```python
# Create enterprise API key
api_key = await enterprise_api_manager.create_api_key(
    org_id="your_org_id",
    user_email="admin@gpudex.com",
    request={
        "name": "Production API Key",
        "scopes": ["admin:*"],
        "expires_at": None,  # No expiration
        "ip_whitelist": ["your.server.ip"]
    }
)

print(f"API Key: {api_key['api_key']}")  # Store securely!
```

---

## 📱 **Phase 7: Frontend Deployment**

### **7.1 Build Configuration**

Update `frontend/package.json`:

```json
{
  "scripts": {
    "build:prod": "NODE_ENV=production npm run build",
    "deploy": "npm run build:prod && npm run deploy:s3"
  },
  "dependencies": {
    "@coinbase/wallet-sdk": "^3.7.1",
    "@walletconnect/core": "^2.15.0",
    "web3": "^4.0.0",
    "chart.js": "^4.4.0"
  }
}
```

### **7.2 Environment Variables**

Create `frontend/.env.production`:

```bash
REACT_APP_API_BASE_URL=https://api.gpudex.com
REACT_APP_ESCROW_CONTRACT=0x...
REACT_APP_TOKEN_CONTRACT=0x...
REACT_APP_CHAIN_ID=137
REACT_APP_ANALYTICS_ID=your_analytics_id
```

---

## 🔧 **Phase 8: Deployment Scripts**

### **8.1 Automated Deployment**

Create `deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting GPUDex Production Deployment"

# Pull latest code
git pull origin main

# Build and deploy contracts (if needed)
if [ "$DEPLOY_CONTRACTS" = "true" ]; then
    echo "📄 Deploying smart contracts..."
    cd contracts
    npx hardhat run scripts/deploy.js --network polygon
    cd ..
fi

# Update environment
cp .env.production.template .env.production

# Build and start services
echo "🐳 Building Docker containers..."
docker-compose -f docker-compose.prod.yml build

echo "🔄 Restarting services..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏱️  Waiting for services to be healthy..."
sleep 30

# Run health checks
echo "🏥 Running health checks..."
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:3000 || exit 1

echo "✅ Deployment completed successfully!"
```

### **8.2 Database Migrations**

Create `migrate.sh`:

```bash
#!/bin/bash

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U gpudex -d gpudex_prod -f /backups/enterprise_db_schema.sql

# Update API key permissions
echo "🔐 Updating API key permissions..."
docker-compose -f docker-compose.prod.yml exec backend \
    python -c "
from enterprise_api_management import enterprise_api_manager
import asyncio

async def update_permissions():
    # Add any necessary permission updates here
    pass

asyncio.run(update_permissions())
"
```

---

## 📋 **Phase 9: Production Checklist**

### **9.1 Pre-Launch Checklist**

- [ ] **Smart Contracts**
  - [ ] Contracts deployed to mainnet
  - [ ] Contract addresses updated in backend
  - [ ] Initial token distribution completed
  - [ ] Escrow contract funded and tested

- [ ] **Backend Services**
  - [ ] Database migrations applied
  - [ ] All environment variables set
  - [ ] Provider APIs configured and tested
  - [ ] Rate limiting enabled
  - [ ] Monitoring endpoints active

- [ ] **Security**
  - [ ] SSL certificates installed
  - [ ] Firewall configured
  - [ ] API keys secured
  - [ ] Backup procedures tested
  - [ ] Security audit completed

- [ ] **Frontend**
  - [ ] Production build optimized
  - [ ] Wallet integrations tested
  - [ ] Analytics tracking enabled
  - [ ] Error monitoring setup

### **9.2 Post-Launch Monitoring**

```bash
# Monitor system health
watch -n 5 'docker-compose -f docker-compose.prod.yml ps'

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Monitor API performance
curl -s https://api.gpudex.com/api/v1/analytics/overview | jq .

# Monitor smart contract events
# Use Etherscan or custom monitoring tools
```

---

## 🎯 **Phase 10: Scaling & Optimization**

### **10.1 Performance Optimization**

- **Database**: Setup read replicas and connection pooling
- **Caching**: Implement Redis caching for frequently accessed data
- **CDN**: Setup CloudFlare or AWS CloudFront for static assets
- **Load Balancing**: Add multiple backend instances behind a load balancer

### **10.2 Advanced Features**

- **Auto-scaling**: Setup Kubernetes for container orchestration
- **Backup Strategy**: Automated database backups with point-in-time recovery
- **Disaster Recovery**: Multi-region deployment with failover capabilities
- **Compliance**: GDPR, SOC2, and other compliance measures

---

## 🆘 **Troubleshooting Guide**

### **Common Issues**

1. **Smart Contract Deployment Fails**
   ```bash
   # Check gas price and network congestion
   npx hardhat run scripts/check-gas.js --network polygon
   ```

2. **Provider API Errors**
   ```bash
   # Test provider connections
   docker-compose exec backend python -c "
   import asyncio
   from real_provider_integrations import provider_aggregator
   asyncio.run(provider_aggregator.get_all_instances())
   "
   ```

3. **Database Connection Issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U gpudex
   ```

---

## 📈 **Success Metrics**

Monitor these KPIs for production success:

- **API Response Times**: < 200ms average
- **Uptime**: > 99.9%
- **Provider Data Freshness**: < 5 minutes
- **Transaction Success Rate**: > 98%
- **User Satisfaction**: Monitor via analytics and feedback

---

Your GPUDex platform is now **production-ready** with enterprise features, real provider integrations, smart contract escrow, and comprehensive monitoring! 🎊 