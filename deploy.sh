#!/bin/bash

# GPUDex Digital Ocean Deployment Script
set -e

echo "🚀 Starting GPUDex deployment..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🔧 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Clone repository if not present
if [ ! -d "gpudex" ]; then
    echo "📂 Cloning GPUDex repository..."
    git clone https://github.com/blablablasealsaresoft/gpudex.git
    cd gpudex
else
    echo "📂 Updating GPUDex repository..."
    cd gpudex
    git pull origin main
fi

# Create production environment file
echo "⚙️ Setting up environment..."
cat > .env << EOF
DATABASE_URL=sqlite:///./gpudex.db
ENVIRONMENT=production
PORT=8000
EOF

# Build and run containers
echo "🏗️ Building and starting containers..."
docker-compose down
docker-compose up -d --build

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Test the deployment
echo "🧪 Testing deployment..."
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend is running!"
else
    echo "❌ Backend failed to start"
    docker-compose logs backend
    exit 1
fi

if curl -f http://localhost:3000/ > /dev/null 2>&1; then
    echo "✅ Frontend is running!"
else
    echo "❌ Frontend failed to start"
    docker-compose logs frontend
    exit 1
fi

echo "🎉 GPUDex deployment completed successfully!"
echo "📊 Backend: http://your-domain:8000"
echo "🌐 Frontend: http://your-domain:3000"
echo ""
echo "Next steps:"
echo "1. Set up domain name and SSL certificate"
echo "2. Configure Nginx reverse proxy"
echo "3. Set up monitoring and backups" 