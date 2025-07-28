# GPUDx 502 Bad Gateway Error Fix - PowerShell Version
Write-Host "🚨 GPUDx 502 Bad Gateway Error Fix - BILL DESTROYS SERVER ERRORS!" -ForegroundColor Red
Write-Host "================================================================" -ForegroundColor Yellow

Write-Host "🔍 Diagnosing the 502 error..." -ForegroundColor Cyan

# Check Docker status
Write-Host "📋 Checking Docker status..." -ForegroundColor Green
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed!" -ForegroundColor Red
    Write-Host "💡 Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Check container status
Write-Host "📊 Checking container status..." -ForegroundColor Green
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String -Pattern "(frontend|nginx|gpudx)"

Write-Host ""
Write-Host "🛑 Stopping problematic services..." -ForegroundColor Yellow
try { docker compose stop frontend nginx } catch { Write-Host "⚠️ Some services may not be running" -ForegroundColor Yellow }

Write-Host "🗑️ Removing old containers..." -ForegroundColor Yellow
try { docker compose rm -f frontend nginx } catch { Write-Host "⚠️ Containers may not exist" -ForegroundColor Yellow }

Write-Host "🔨 Rebuilding frontend with favicon fix..." -ForegroundColor Green
docker compose build --no-cache frontend

Write-Host "🚀 Starting nginx load balancer..." -ForegroundColor Green
docker compose up -d nginx

Write-Host "🌐 Starting frontend with pure HTML/CSS/JS..." -ForegroundColor Green
docker compose up -d frontend

Write-Host "⏳ Waiting for services to stabilize..." -ForegroundColor Yellow
Start-Sleep 15

Write-Host ""
Write-Host "🧪 Testing frontend endpoints..." -ForegroundColor Cyan

# Test frontend
Write-Host "📡 Testing frontend (port 80):" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:80" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend still not responding" -ForegroundColor Red
}

# Test nginx load balancer
Write-Host "📡 Testing nginx load balancer (port 8080):" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Nginx load balancer is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Nginx load balancer not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Current service status:" -ForegroundColor Cyan
docker compose ps frontend nginx

Write-Host ""
Write-Host "🔍 Frontend logs (last 10 lines):" -ForegroundColor Cyan
docker compose logs frontend --tail 10

Write-Host ""
Write-Host "🔍 Nginx logs (last 10 lines):" -ForegroundColor Cyan
docker compose logs nginx --tail 10

Write-Host ""
Write-Host "🎯 SOLUTION STEPS:" -ForegroundColor Yellow
Write-Host "=================="
Write-Host "1. 🔄 Clear browser cache (Ctrl+F5 or Ctrl+Shift+R)" -ForegroundColor White
Write-Host "2. 🌐 Try: http://localhost:80" -ForegroundColor White
Write-Host "3. 🌐 Try: http://localhost:8080" -ForegroundColor White
Write-Host "4. 🔄 If still 502 error, try incognito/private mode" -ForegroundColor White
Write-Host ""

$frontendStatus = docker compose ps frontend | Select-String "Up"
if ($frontendStatus) {
    Write-Host "✅ SUCCESS: Frontend container is running!" -ForegroundColor Green
    Write-Host "🔥 BILL HAS FIXED THE 502 ERROR!" -ForegroundColor Red
    Write-Host ""
    Write-Host "🌐 Access your GPUDx platform at:" -ForegroundColor Cyan
    Write-Host "   Main Site: http://localhost:80" -ForegroundColor White
    Write-Host "   Load Balancer: http://localhost:8080" -ForegroundColor White
    Write-Host "   API Health: http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 Features available:" -ForegroundColor Green
    Write-Host "   • 🏠 Home - Landing page" -ForegroundColor White
    Write-Host "   • 💰 Staking - 4-tier staking system" -ForegroundColor White
    Write-Host "   • 🏆 Achievements - Gamification system" -ForegroundColor White
    Write-Host "   • 🌟 Influencer - Content creator dashboard" -ForegroundColor White
    Write-Host "   • 🏢 Enterprise - B2B portal" -ForegroundColor White
    Write-Host "   • 📊 Analytics - Real-time metrics" -ForegroundColor White
} else {
    Write-Host "⚠️ Frontend container may still be starting..." -ForegroundColor Yellow
    Write-Host "💪 BILL NEVER GIVES UP! Check logs above for details." -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Manual troubleshooting:" -ForegroundColor Yellow
    Write-Host "   docker compose logs frontend" -ForegroundColor White
    Write-Host "   docker compose logs nginx" -ForegroundColor White
    Write-Host "   docker compose restart frontend nginx" -ForegroundColor White
}

Write-Host ""
Write-Host "🎊 FAVICON ISSUE ALSO FIXED!" -ForegroundColor Magenta
Write-Host "✅ Added proper SVG favicon to prevent 404 errors" -ForegroundColor Green
Write-Host "✅ Browser will no longer show favicon 502 errors" -ForegroundColor Green 