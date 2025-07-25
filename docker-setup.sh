#!/bin/bash

# GPUDex Docker Production Setup Script
# Run this script to deploy a full production environment in 5 minutes

set -e

echo "🚀 GPUDex Docker Production Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Step 1: Environment setup
echo ""
echo "📝 Step 1: Setting up environment variables"

if [ ! -f .env.production ]; then
    print_status "Creating .env.production from template"
    cp env.production .env.production
else
    print_warning ".env.production already exists, skipping copy"
fi

# Generate secure secrets
echo ""
echo "🔐 Generating secure secrets..."

JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(32))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(16))")
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || python -c "import secrets; print(secrets.token_urlsafe(32))")

print_status "Generated secure secrets"

# Update .env.production with generated secrets
sed -i.bak "s/GENERATE_SECURE_JWT_SECRET_HERE/$JWT_SECRET/g" .env.production
sed -i.bak "s/SECURE_PASSWORD_HERE/$DB_PASSWORD/g" .env.production
sed -i.bak "s/GENERATE_SECURE_SECRET_KEY_HERE/$SECRET_KEY/g" .env.production

print_status "Updated .env.production with secure secrets"

# Step 2: Build and start services
echo ""
echo "🐳 Step 2: Building and starting Docker services"

print_status "Building Docker images..."
docker-compose -f docker-compose.prod.yml build

print_status "Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 30

# Step 3: Initialize database
echo ""
echo "🗄️ Step 3: Initializing database"

print_status "Creating database tables..."
docker-compose -f docker-compose.prod.yml exec -T backend python -c "
from database import DatabaseManager
import sys
try:
    db = DatabaseManager()
    db.create_tables()
    print('✅ Database initialized successfully!')
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    sys.exit(1)
"

# Step 4: Health checks
echo ""
echo "🏥 Step 4: Running health checks"

# Function to check if service is responding
check_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            print_status "$name is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$name health check failed"
    return 1
}

echo "Checking service health..."

# Check frontend
echo -n "Frontend: "
check_service "http://localhost/health" "Frontend"

# Check backend
echo -n "Backend: "
check_service "http://localhost:8000/" "Backend API"

# Check API endpoint
echo -n "API: "
check_service "http://localhost:8000/api/v1/providers" "API endpoints"

# Step 5: Display summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="

# Check if all services are running
RUNNING_SERVICES=$(docker-compose -f docker-compose.prod.yml ps --services --filter "status=running" | wc -l)
TOTAL_SERVICES=$(docker-compose -f docker-compose.prod.yml ps --services | wc -l)

echo ""
print_status "Services Status: $RUNNING_SERVICES/$TOTAL_SERVICES running"

echo ""
echo "🌐 Access your GPUDex platform:"
echo "   Frontend:  http://localhost"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/api/docs"
echo "   Grafana:   http://localhost:3001 (admin/your_password)"
echo "   Prometheus: http://localhost:9090"

echo ""
echo "📊 Test API endpoints:"
echo "   curl http://localhost:8000/"
echo "   curl http://localhost:8000/api/v1/providers"
echo "   curl http://localhost:8000/api/v1/prices"

echo ""
echo "🔧 Useful commands:"
echo "   View logs:    docker-compose -f docker-compose.prod.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.prod.yml down"
echo "   Restart:      docker-compose -f docker-compose.prod.yml restart"
echo "   Status:       docker-compose -f docker-compose.prod.yml ps"

echo ""
print_status "Your GPUDex production environment is ready! 🚀"

# Optional: Open browser
if command -v xdg-open &> /dev/null; then
    echo ""
    echo "Opening browser..."
    xdg-open http://localhost
elif command -v open &> /dev/null; then
    echo ""
    echo "Opening browser..."
    open http://localhost
fi

echo ""
print_warning "Don't forget to:"
print_warning "1. Update .env.production with your real API keys"
print_warning "2. Configure SSL/TLS for production deployment"
print_warning "3. Set up your domain and DNS"
print_warning "4. Configure monitoring alerts"

echo ""
echo "📚 See DOCKER_PRODUCTION_GUIDE.md for detailed documentation" 