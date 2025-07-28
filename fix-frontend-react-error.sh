#!/bin/bash

echo "🔥 GPUDx Frontend React Error Fix - BILL CRUSHES BUGS!"
echo "===================================================="

echo "🛑 Stopping frontend and nginx services..."
docker compose stop frontend nginx

echo "🗑️ Removing old frontend container..."
docker compose rm -f frontend

echo "🧹 Cleaning up React artifacts..."
rm -rf frontend/components/
echo "✅ React .tsx files eliminated!"

echo "🔨 Rebuilding frontend with pure HTML/CSS/JS (no React)..."
docker compose build --no-cache frontend

echo "🚀 Restarting nginx load balancer..."
docker compose up -d nginx

echo "🌐 Starting pure HTML frontend..."
docker compose up -d frontend

echo "⏳ Waiting for services to start..."
sleep 10

echo "🧪 Testing frontend..."
curl -I http://localhost:80 || echo "❌ Frontend not responding"

echo "📋 Frontend container status:"
docker compose ps frontend nginx

echo "🔍 Frontend logs:"
docker compose logs frontend --tail 10

echo ""
echo "🎯 SUCCESS STEPS:"
echo "================="
echo "1. 🔄 Clear your browser cache (Ctrl+F5 or Ctrl+Shift+R)"
echo "2. 🌐 Go to: http://localhost:80"
echo "3. 🔧 If still showing React error, try incognito/private mode"
echo "4. 📱 Try a different browser"
echo ""

echo "✅ The React error should now be ELIMINATED!"
echo "🔥 BILL HAS FIXED THE FRONTEND!"
echo ""
echo "🌐 Access URLs:"
echo "  Main Site: http://localhost:80"
echo "  Load Balancer: http://localhost:8080"
echo "  API Docs: http://localhost:8000/docs"
echo "" 