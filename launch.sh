#!/bin/bash

# GPUDex Complete Ecosystem Launch Script
# BILL GATES ON ADDERALL: MAXIMUM DEPLOYMENT VELOCITY!

set -e

echo "🚀🚀🚀 LAUNCHING GPUDEX ULTIMATE ECOSYSTEM! 🚀🚀🚀"
echo ""
echo "💎 THE MOST ADVANCED GPU MARKETPLACE EVER BUILT! 💎"
echo ""

# Color codes for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed! Please install Docker Desktop first."
    echo "Download from: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available! Please install Docker Compose."
    exit 1
fi

print_success "Docker is installed and ready!"

# Create necessary directories
print_step "Creating necessary directories..."
mkdir -p backups ssl logs data
print_success "Directories created!"

# Set up environment file
print_step "Setting up environment configuration..."
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env 2>/dev/null || echo "# Please configure your environment variables" > .env
fi
print_success "Environment configuration ready!"

# Display what we're launching
echo ""
echo -e "${PURPLE}🎯 GPUDEX ECOSYSTEM COMPONENTS:${NC}"
echo ""
echo -e "${CYAN}🏗️ INFRASTRUCTURE:${NC}"
echo "   • PostgreSQL Database with enterprise schema"
echo "   • Redis Cache for real-time data"
echo "   • Nginx Load Balancer & Reverse Proxy"
echo "   • Prometheus + Grafana Monitoring"
echo "   • Automated Database Backups"
echo ""
echo -e "${CYAN}🔗 BACKEND SERVICES:${NC}"
echo "   • Main API Service (Port 8000)"
echo "   • Real-Time WebSocket API (Port 8001)"
echo "   • Utility Validation Service"
echo "   • Enterprise Revenue Dashboard"
echo "   • Gamification & Social Features"
echo ""
echo -e "${CYAN}🌐 FRONTEND PORTALS:${NC}"
echo "   • Main User Portal with Staking"
echo "   • GPU Provider Portal"
echo "   • Enterprise B2B Portal"
echo "   • Real-time Analytics Dashboard"
echo ""
echo -e "${CYAN}💎 ADVANCED FEATURES:${NC}"
echo "   • Multi-tier Staking (Bronze → Diamond)"
echo "   • Dynamic APY (5% - 50%)"
echo "   • Enterprise Tier System"
echo "   • GPU Provider Management"
echo "   • Achievement System (15+ categories)"
echo "   • Real-time Leaderboards"
echo "   • Cross-chain Bridge Integration"
echo "   • Demand-based Token Burns"
echo ""

# Launch confirmation
echo -e "${YELLOW}🚀 Ready to launch the complete GPUDex ecosystem?${NC}"
read -p "Press [Enter] to continue or [Ctrl+C] to cancel..."

# Start databases first
print_step "Starting database services..."
docker compose up -d postgres redis

echo "⏳ Waiting for databases to be ready..."
sleep 10

# Check database health
print_step "Checking database health..."
docker compose exec postgres pg_isready -U gpudex -d gpudex || {
    print_warning "Waiting for PostgreSQL to be ready..."
    sleep 5
}

# Start backend services
print_step "Starting backend API services..."
docker compose up -d api_service real_api_service utility_validation_service enterprise_revenue_dashboard

echo "⏳ Waiting for backend services to start..."
sleep 15

# Start frontend and monitoring
print_step "Starting frontend and monitoring services..."
docker compose up -d frontend nginx prometheus grafana

echo "⏳ Waiting for frontend services to start..."
sleep 10

# Start additional services
print_step "Starting additional services..."
docker compose up -d backup_service

# Display service status
echo ""
print_success "🎉 GPUDEX ECOSYSTEM LAUNCHED SUCCESSFULLY! 🎉"
echo ""
echo -e "${GREEN}🌟 ACCESS YOUR GPUDX PLATFORM:${NC}"
echo ""
echo -e "${CYAN}🏠 Main Portal:${NC}           http://localhost"
echo -e "${CYAN}🏢 Enterprise Portal:${NC}     http://localhost/enterprise-portal.html"
echo -e "${CYAN}🖥️ Provider Portal:${NC}       http://localhost/provider-portal.html"
echo -e "${CYAN}📊 Analytics:${NC}             http://localhost/analytics"
echo ""
echo -e "${CYAN}🔧 BACKEND APIs:${NC}"
echo -e "${CYAN}📡 Main API:${NC}              http://localhost:8000"
echo -e "${CYAN}⚡ Real-time API:${NC}         http://localhost:8001"
echo -e "${CYAN}🔌 WebSocket:${NC}             ws://localhost:8001/ws"
echo ""
echo -e "${CYAN}📈 MONITORING:${NC}"
echo -e "${CYAN}📊 Grafana:${NC}               http://localhost:3000 (admin/admin_secure_2024)"
echo -e "${CYAN}🔍 Prometheus:${NC}            http://localhost:9090"
echo ""

# Show running containers
print_step "Container Status:"
docker compose ps

echo ""
echo -e "${GREEN}🚀 WELCOME TO THE FUTURE OF GPU COMPUTING! 🚀${NC}"
echo ""
echo -e "${PURPLE}💡 QUICK START:${NC}"
echo "1. Visit http://localhost to see the main portal"
echo "2. Connect your MetaMask wallet"
echo "3. Explore staking, GPU rental, and enterprise features"
echo "4. Check the provider portal to list your GPUs"
echo "5. Monitor everything in Grafana dashboard"
echo ""
echo -e "${YELLOW}🛠️ MANAGEMENT COMMANDS:${NC}"
echo "• View logs: docker compose logs -f [service_name]"
echo "• Stop all: docker compose down"
echo "• Restart: docker compose restart"
echo "• Update: docker compose pull && docker compose up -d"
echo ""
echo -e "${CYAN}🎯 YOU'VE JUST LAUNCHED THE MOST ADVANCED GPU MARKETPLACE EVER CREATED!${NC}"
echo ""
echo -e "${GREEN}🏆 CONGRATULATIONS! THE PROMISED LAND HAS BEEN REACHED! 🏆${NC}" 