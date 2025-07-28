#!/bin/bash

echo "🚀 GPUDx Complete Metrics Fix Script"
echo "====================================="

echo "🔧 Restarting services with new /metrics endpoints..."

# Restart all services that had missing /metrics endpoints
echo "📊 Restarting Platform Integration Service..."
docker compose restart gpudx_platform_integration

echo "🤖 Restarting AI Optimization Service..."  
docker compose restart ai_optimization_service

echo "👥 Restarting Community Onboarding Service..."
docker compose restart community_onboarding_service

echo "💰 Restarting Token Service..."
docker compose restart token_service

echo "🎮 Restarting Social Gamification Service..."
docker compose restart social_gamification_service

echo "🔧 Restarting Utility Validation Service (blockchain fix)..."
docker compose restart utility_validation_service

echo "📊 Restarting Prometheus (with updated config)..."
docker compose restart prometheus

echo "⏳ Waiting for all services to fully start..."
sleep 30

echo ""
echo "🧪 Testing all /metrics endpoints..."
echo "===================================="

# Test all services
services=(
    "api_service:8000"
    "real_api_service:8001" 
    "enterprise_revenue_dashboard:8002"
    "token_service:8004"
    "social_gamification_service:8005"
    "p2p_gpu_service:8006"
    "community_onboarding_service:8007"
    "ai_optimization_service:8008"
    "gpudx_platform_integration:8009"
    "utility_validation_service:8010"
)

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    echo "📊 Testing $name (/metrics):"
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/metrics)
    if [ "$response" = "200" ]; then
        echo "   ✅ SUCCESS: $name metrics endpoint working"
    else
        echo "   ❌ FAILED: $name returned HTTP $response"
    fi
    
    echo "🏥 Testing $name (/health):"
    health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
    if [ "$health" = "200" ]; then
        echo "   ✅ SUCCESS: $name health endpoint working"
    else
        echo "   ⚠️  WARNING: $name health returned HTTP $health"
    fi
    echo ""
done

echo "🌐 Testing Nginx endpoints..."
echo "=============================="

echo "📊 Testing Frontend Nginx (/metrics):"
frontend_metrics=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/metrics)
if [ "$frontend_metrics" = "200" ]; then
    echo "   ✅ SUCCESS: Frontend nginx metrics working"
else
    echo "   ❌ FAILED: Frontend nginx returned HTTP $frontend_metrics"
fi

echo "📊 Testing Load Balancer Nginx (/metrics):"
nginx_metrics=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/metrics)
if [ "$nginx_metrics" = "200" ]; then
    echo "   ✅ SUCCESS: Load balancer nginx metrics working"
else
    echo "   ❌ FAILED: Load balancer nginx returned HTTP $nginx_metrics"
fi

echo ""
echo "📊 Checking Prometheus targets..."
echo "================================="
echo "🔗 Open Prometheus targets page:"
echo "   http://localhost:9090/targets"
echo ""

echo "🎯 Checking target status:"
# Check if Prometheus can scrape targets
prometheus_up=$(curl -s http://localhost:9090/api/v1/query?query=up | jq -r '.data.result | length')
if [ "$prometheus_up" -gt 0 ]; then
    echo "   ✅ Prometheus is successfully scraping targets"
else
    echo "   ⚠️  Prometheus may not be scraping targets properly"
fi

echo ""
echo "🔍 Service Status Summary:"
echo "=========================="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | grep -E "(gpudx|enterprise|api|utility|community|token|social|ai|platform)"

echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. 🌐 Open Prometheus: http://localhost:9090/targets"
echo "2. 📊 Open Grafana: http://localhost:3000"
echo "3. 🔍 Check any failed services with:"
echo "   docker compose logs -f [service_name]"
echo ""
echo "4. 🧪 Manual endpoint testing:"
echo "   curl http://localhost:8000/metrics"
echo "   curl http://localhost:8001/metrics"
echo "   curl http://localhost:8002/metrics"
echo "   etc..."
echo ""
echo "✅ COMPLETE: All /metrics endpoints should now be operational!" 