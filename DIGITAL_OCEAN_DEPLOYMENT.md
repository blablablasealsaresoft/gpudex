# 🌊 **Digital Ocean Deployment Guide - GPUDx Polygon Production**

## **🚀 Quick Digital Ocean Deployment (30 Minutes)**

Deploy the **production-ready GPUDx platform** with Polygon smart contracts to Digital Ocean in under 30 minutes.

### **✅ What You're Deploying**
- **Frontend**: Real GPU marketplace with 93+ GPUs from 11 providers
- **Backend**: FastAPI with live provider integrations
- **Smart Contracts**: Pre-deployed on Polygon mainnet (production ready)
- **Infrastructure**: Docker, PostgreSQL, Redis, Nginx, Prometheus, Grafana
- **Network**: Polygon-only (simplified, low-cost transactions)

---

## **📋 Prerequisites (5 minutes)**

### **Digital Ocean Account Setup**
- [ ] Digital Ocean account with payment method
- [ ] SSH key added to Digital Ocean account
- [ ] Domain name (optional for production)

### **Local Requirements**
- [ ] Git installed
- [ ] SSH client
- [ ] Text editor

---

## **⚡ Step 1: Create Digital Ocean Droplet (2 minutes)**

### **Recommended Droplet Configuration**
```bash
# Droplet Specs (Recommended)
Size: Basic - $24/month
RAM: 4 GB
CPU: 2 vCPUs  
SSD: 80 GB
OS: Ubuntu 22.04 LTS
Region: Choose closest to your users

# Or for high-traffic production
Size: General Purpose - $48/month  
RAM: 8 GB
CPU: 4 vCPUs
SSD: 160 GB
```

### **Create via Digital Ocean Dashboard**
1. **Log into Digital Ocean** → Create → Droplets
2. **Choose Ubuntu 22.04 LTS**
3. **Select size** (Basic $24/month recommended)
4. **Add your SSH key**
5. **Name**: `gpudx-production`
6. **Create Droplet** (takes ~60 seconds)

---

## **⚡ Step 2: Connect and Setup Server (5 minutes)**

### **SSH into Droplet**
```bash
# Replace with your droplet IP
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### **Setup Firewall**
```bash
# Configure UFW firewall
ufw allow ssh
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS  
ufw allow 3000/tcp  # Frontend (temporary)
ufw allow 8000/tcp  # Backend API (temporary)
ufw --force enable

# Verify firewall
ufw status
```

---

## **⚡ Step 3: Deploy GPUDx Platform (10 minutes)**

### **Clone Repository**
```bash
# Clone the production-ready repository
cd /opt
git clone https://github.com/blablablasealsaresoft/gpudex.git
cd gpudex

# Switch to production branch
git checkout release/v2.0.0

# Verify files
ls -la
# Should see: docker-compose.prod.yml, Dockerfile.prod, frontend/, backend/, etc.
```

### **Configure Environment**
```bash
# Copy production environment template
cp production.env.template production.env

# Edit production configuration
nano production.env

# REQUIRED: Update these values in production.env
DOMAIN=your-domain.com                    # Your domain (or use IP for testing)
API_DOMAIN=api.your-domain.com           # API subdomain
POSTGRES_PASSWORD=your_secure_db_password # Strong database password
POSTGRES_USER=gpudx_prod                 # Database user
POSTGRES_DB=gpudx_production             # Database name
```

### **Smart Contract Configuration (Already Set)**
```bash
# These are already configured in docker-compose.prod.yml:
ESCROW_CONTRACT_ADDRESS=0xE0107C4227A38Aae3E5163D691EFb0dc0Eb7598C
TOKEN_CONTRACT_ADDRESS=0x386FF386B396ca139E5D2dB6d0b61a0FDd5b4b47
PLATFORM_FEE_RECIPIENT=0x0B83154b85B7F6f8ec567d0F3a93B50C8b8C754A
BLOCKCHAIN_NETWORK=polygon
CHAIN_ID=137
PLATFORM_FEE_PERCENT=300  # 3%
```

---

## **⚡ Step 4: Launch Platform (5 minutes)**

### **Build and Start Services**
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start all services in background
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Expected output:
# backend      ✅ Up (healthy)
# frontend     ✅ Up (healthy)  
# postgres     ✅ Up (healthy)
# redis        ✅ Up (healthy)
# nginx        ✅ Up
# prometheus   ✅ Up
# grafana      ✅ Up
# backup       ✅ Up
```

### **Verify Deployment**
```bash
# Check backend health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "timestamp": "..."}

# Check frontend
curl http://localhost:3000
# Expected: HTML response with GPUDx marketplace

# Check backend GPU data (live test)
curl http://localhost:8000/api/v1/prices | head -20
# Expected: Real GPU data from 11+ providers
```

---

## **⚡ Step 5: Access Your Platform (2 minutes)**

### **Test Platform Access**
```bash
# Get your droplet IP
curl -4 icanhazip.com

# Test URLs (replace IP with your droplet IP):
echo "Frontend: http://YOUR_DROPLET_IP:3000"
echo "Backend API: http://YOUR_DROPLET_IP:8000"
echo "Grafana Monitoring: http://YOUR_DROPLET_IP:3001"
echo "Prometheus Metrics: http://YOUR_DROPLET_IP:9090"
```

### **Platform Features Available**
- ✅ **GPU Marketplace**: Browse 93+ real GPUs with live pricing
- ✅ **Wallet Connect**: MetaMask, Coinbase, WalletConnect support
- ✅ **Polygon Network**: Auto-switches to Polygon mainnet  
- ✅ **Smart Contract Payments**: 3% platform fee collection
- ✅ **Analytics Dashboard**: Real market data and trends
- ✅ **Monitoring**: Prometheus + Grafana dashboards

---

## **🌐 Optional: Domain Configuration (10 minutes)**

### **Point Domain to Droplet**
```bash
# Add DNS records in your domain registrar:
A     yourdomain.com        YOUR_DROPLET_IP
A     api.yourdomain.com    YOUR_DROPLET_IP
CNAME www.yourdomain.com    yourdomain.com
```

### **SSL Certificate (Let's Encrypt)**
```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Test auto-renewal
certbot renew --dry-run

# Update firewall for HTTPS
ufw allow 443/tcp
```

---

## **📊 Production Monitoring (Already Configured)**

### **Access Monitoring Dashboards**
- **Grafana**: `http://YOUR_IP:3001` (admin/admin)
- **Prometheus**: `http://YOUR_IP:9090`

### **Key Metrics Monitored**
- ✅ **API Response Times**: Backend performance
- ✅ **Database Health**: PostgreSQL metrics
- ✅ **Redis Performance**: Cache hit rates
- ✅ **Container Health**: Docker service status
- ✅ **System Resources**: CPU, RAM, disk usage

### **Automated Backups**
- ✅ **Daily Database Backups**: Stored in `/opt/gpudex/backups/`
- ✅ **7-day Retention**: Old backups automatically cleaned
- ✅ **Health Checks**: All services monitored

---

## **🚀 Production Checklist (Verification)**

### **✅ Core Platform**
```bash
# Test each component
curl http://localhost:8000/health                    # Backend health
curl http://localhost:8000/api/v1/prices | jq .total_results  # Real GPU count
curl http://localhost:3000                           # Frontend loaded
docker-compose -f docker-compose.prod.yml ps         # All services up
```

### **✅ Smart Contract Integration**
```bash
# Test smart contract endpoints
curl http://localhost:8000/api/v1/smart-contracts/status | jq
# Expected: Polygon mainnet contracts with deployed addresses
```

### **✅ Production Security**
- [x] **Firewall**: UFW configured (ports 80, 443, SSH only)
- [x] **Non-root containers**: All services run as non-root users
- [x] **Health checks**: All services have health monitoring
- [x] **Secure secrets**: Database passwords in environment files
- [x] **Rate limiting**: API endpoints protected

---

## **🎯 Quick Commands Reference**

### **Service Management**
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Update platform (after git pull)
docker-compose -f docker-compose.prod.yml down
git pull origin release/v2.0.0
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Remove everything (CAREFUL!)
docker-compose -f docker-compose.prod.yml down -v
```

### **Database Management**
```bash
# Access database
docker-compose -f docker-compose.prod.yml exec postgres psql -U gpudx_prod -d gpudx_production

# Create manual backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U gpudx_prod gpudx_production > backup_$(date +%Y%m%d).sql

# View backup files
ls -la backups/
```

---

## **💰 Cost Estimation**

### **Digital Ocean Monthly Costs**
- **Basic Droplet** (4GB RAM): $24/month
- **Bandwidth**: Free (1TB included)
- **Backups** (optional): +20% ($4.80/month)
- **Load Balancer** (optional): $12/month
- **Domain SSL**: Free (Let's Encrypt)

**Total: ~$24-41/month for production deployment**

### **Scaling Options**
- **Higher Traffic**: Upgrade to 8GB droplet ($48/month)
- **High Availability**: Add load balancer + multiple droplets
- **Database**: Switch to managed PostgreSQL ($15+/month)

---

## **🎉 Success! Platform Deployed**

**Your GPUDx platform is now live with:**

✅ **Real GPU Marketplace**: 93+ GPUs from 11 providers  
✅ **Polygon Smart Contracts**: Production deployment  
✅ **Multi-Wallet Support**: MetaMask, Coinbase, WalletConnect  
✅ **Production Infrastructure**: Docker, monitoring, backups  
✅ **Low-Cost Transactions**: ~$0.05 gas fees on Polygon  

### **Next Steps**
1. **Test the platform** → Connect wallet and browse GPUs
2. **Configure domain** → Point DNS to your droplet IP  
3. **Enable SSL** → Use Let's Encrypt for HTTPS
4. **Marketing** → Announce your GPU marketplace launch!

**Platform URLs:**
- **Frontend**: `http://YOUR_DROPLET_IP:3000`  
- **API**: `http://YOUR_DROPLET_IP:8000`
- **Monitoring**: `http://YOUR_DROPLET_IP:3001`

**Your production-ready GPU marketplace is live! 🚀** 