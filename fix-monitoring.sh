#!/bin/bash

echo "🔧 GPUDx Monitoring Fix Script"
echo "==============================="

echo "🔄 Restarting affected services..."

# Restart services with monitoring fixes
docker compose restart api_service
docker compose restart enterprise_revenue_dashboard  
docker compose restart utility_validation_service
docker compose restart real_api_service
docker compose restart frontend
docker compose restart nginx

echo "⏳ Waiting for services to start..."
sleep 15

echo "🧪 Testing endpoints..."

# Test all metrics endpoints
echo "📊 Testing metrics endpoints:"

echo "  - API Service (/metrics):"
curl -s http://localhost:8000/metrics | head -3

echo "  - API Service (/api/v2/health):"
curl -s http://localhost:8000/api/v2/health

echo "  - Enterprise Dashboard (/metrics):"
curl -s http://localhost:8002/metrics | head -3

echo "  - Enterprise Dashboard (/status):"
curl -s http://localhost:8002/status

echo "  - Real API Service (/metrics):"
curl -s http://localhost:8001/metrics | head -3

echo "  - Utility Validation (/metrics):"
curl -s http://localhost:8010/metrics | head -3

echo "  - Frontend (/metrics):"
curl -s http://localhost:80/metrics | head -3

echo "  - Nginx Load Balancer (/metrics):"
curl -s http://localhost:8080/metrics | head -3

echo ""
echo "✅ Monitoring fix complete!"
echo ""
echo "🔍 Check Docker logs with:"
echo "  docker compose logs -f enterprise_revenue_dashboard"
echo "  docker compose logs -f api_service"
echo "  docker compose logs -f frontend"
echo ""
echo "📊 Check Prometheus targets:"
echo "  http://localhost:9090/targets"
echo "" 