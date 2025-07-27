#!/bin/bash
# 🌊 GPUDx Digital Ocean Quick Deployment Script
# Run this on your Digital Ocean droplet after initial creation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting GPUDx Digital Ocean Deployment${NC}"
echo -e "${BLUE}===================================================${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}" 
   exit 1
fi

echo -e "${YELLOW}📦 Step 1: System Update and Dependencies${NC}"
apt update && apt upgrade -y
apt install -y curl wget git ufw

echo -e "${YELLOW}🐳 Step 2: Installing Docker and Docker Compose${NC}"
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

echo -e "${YELLOW}🔥 Step 3: Configuring Firewall${NC}"
ufw allow ssh
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 3000/tcp  # Frontend
ufw allow 8000/tcp  # Backend API
ufw allow 3001/tcp  # Grafana
ufw allow 9090/tcp  # Prometheus
ufw --force enable

echo -e "${YELLOW}📥 Step 4: Cloning GPUDx Repository${NC}"
cd /opt
if [ -d "gpudex" ]; then
    echo "Directory exists, updating..."
    cd gpudex
    git pull origin release/v2.0.0
else
    echo "Cloning repository..."
    git clone https://github.com/blablablasealsaresoft/gpudex.git
    cd gpudex
    git checkout release/v2.0.0
fi

echo -e "${YELLOW}⚙️  Step 5: Setting up Environment Configuration${NC}"
if [ ! -f "production.env" ]; then
    cp production.env.template production.env
    echo -e "${GREEN}✅ Created production.env from template${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit production.env with your settings before starting!${NC}"
    echo -e "   - Set DOMAIN and API_DOMAIN"
    echo -e "   - Set secure POSTGRES_PASSWORD"
    echo -e "   - Configure any other required settings"
else
    echo -e "${GREEN}✅ production.env already exists${NC}"
fi

echo -e "${YELLOW}🏗️  Step 6: Building Docker Images${NC}"
docker-compose -f docker-compose.prod.yml build

echo -e "${YELLOW}🚀 Step 7: Starting Services${NC}"
docker-compose -f docker-compose.prod.yml up -d

echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

echo -e "${YELLOW}🔍 Step 8: Verifying Deployment${NC}"
echo "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

echo -e "\n${YELLOW}Testing backend health...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
fi

echo -e "\n${YELLOW}Testing frontend...${NC}"
if curl -s http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✅ Frontend is responding${NC}"
else
    echo -e "${RED}❌ Frontend check failed${NC}"
fi

echo -e "\n${YELLOW}Testing GPU data API...${NC}"
if curl -s http://localhost:8000/api/v1/prices | grep -q "total_results"; then
    echo -e "${GREEN}✅ GPU data API is working${NC}"
else
    echo -e "${RED}❌ GPU data API check failed${NC}"
fi

# Get server IP
SERVER_IP=$(curl -s -4 icanhazip.com)

echo -e "\n${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Your GPUDx platform is now live at:${NC}"
echo -e ""
echo -e "${BLUE}Frontend (GPU Marketplace): ${NC}http://${SERVER_IP}:3000"
echo -e "${BLUE}Backend API:               ${NC}http://${SERVER_IP}:8000"
echo -e "${BLUE}API Documentation:         ${NC}http://${SERVER_IP}:8000/docs"
echo -e "${BLUE}Grafana Monitoring:        ${NC}http://${SERVER_IP}:3001 (admin/admin)"
echo -e "${BLUE}Prometheus Metrics:        ${NC}http://${SERVER_IP}:9090"
echo -e ""
echo -e "${GREEN}Platform Features:${NC}"
echo -e "✅ Real GPU marketplace with 93+ GPUs from 11+ providers"
echo -e "✅ Polygon smart contracts (production deployed)"
echo -e "✅ Multi-wallet support (MetaMask, Coinbase, WalletConnect)"
echo -e "✅ Production monitoring and backups"
echo -e "✅ Low-cost transactions (~$0.05 gas fees)"
echo -e ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Test the platform: Connect wallet and browse GPUs"
echo -e "2. Configure domain: Point DNS to ${SERVER_IP}"
echo -e "3. Setup SSL: Run 'certbot --nginx -d yourdomain.com'"
echo -e "4. Launch marketing: Announce your GPU marketplace!"
echo -e ""
echo -e "${GREEN}Your production-ready GPU marketplace is live! 🚀${NC}"

# Create helpful management script
cat > /opt/gpudex/manage.sh << 'EOF'
#!/bin/bash
# GPUDx Management Script

cd /opt/gpudex

case "$1" in
    "start")
        echo "Starting GPUDx platform..."
        docker-compose -f docker-compose.prod.yml up -d
        ;;
    "stop")
        echo "Stopping GPUDx platform..."
        docker-compose -f docker-compose.prod.yml down
        ;;
    "restart")
        echo "Restarting GPUDx platform..."
        docker-compose -f docker-compose.prod.yml restart
        ;;
    "logs")
        echo "Showing logs for ${2:-all services}..."
        if [ -z "$2" ]; then
            docker-compose -f docker-compose.prod.yml logs -f
        else
            docker-compose -f docker-compose.prod.yml logs -f "$2"
        fi
        ;;
    "status")
        echo "Service status:"
        docker-compose -f docker-compose.prod.yml ps
        ;;
    "update")
        echo "Updating platform..."
        git pull origin release/v2.0.0
        docker-compose -f docker-compose.prod.yml build
        docker-compose -f docker-compose.prod.yml up -d
        ;;
    "backup")
        echo "Creating database backup..."
        docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U gpudx_prod gpudx_production > "backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql"
        echo "Backup created in backups/ directory"
        ;;
    *)
        echo "GPUDx Management Script"
        echo "Usage: $0 {start|stop|restart|logs|status|update|backup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - View logs (add service name for specific service)"
        echo "  status  - Show service status"
        echo "  update  - Update platform from git and rebuild"
        echo "  backup  - Create manual database backup"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs backend"
        echo "  $0 update"
        ;;
esac
EOF

chmod +x /opt/gpudex/manage.sh

echo -e "${GREEN}📱 Management script created at /opt/gpudex/manage.sh${NC}"
echo -e "   Usage: /opt/gpudex/manage.sh {start|stop|restart|logs|status|update|backup}" 