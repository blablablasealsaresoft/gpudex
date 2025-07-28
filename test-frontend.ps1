# GPUDx Frontend Test & Fix - BILL GATES DEBUGGING MODE
Write-Host "🔥 BILL GATES DEBUGGING MODE - ACTUALLY FIXING THE 502!" -ForegroundColor Red
Write-Host "=======================================================" -ForegroundColor Yellow

Write-Host "🔍 STEP 1: Current container status..." -ForegroundColor Cyan
docker compose ps frontend nginx

Write-Host ""
Write-Host "📋 STEP 2: Checking frontend logs..." -ForegroundColor Cyan
docker compose logs frontend --tail 15

Write-Host ""
Write-Host "📋 STEP 3: Checking nginx logs..." -ForegroundColor Cyan  
docker compose logs nginx --tail 10

Write-Host ""
Write-Host "🛠️ STEP 4: Rebuilding frontend with PROPER configuration..." -ForegroundColor Yellow
docker compose stop frontend
docker compose rm -f frontend
docker compose build --no-cache frontend

Write-Host ""
Write-Host "🚀 STEP 5: Starting frontend..." -ForegroundColor Green
docker compose up -d frontend

Write-Host ""
Write-Host "⏳ STEP 6: Waiting for frontend to fully start..." -ForegroundColor Yellow
Write-Host "Waiting 30 seconds for health check to pass..."
Start-Sleep 30

Write-Host ""
Write-Host "🧪 STEP 7: Testing all endpoints..." -ForegroundColor Cyan

# Test frontend health endpoint first
Write-Host "📡 Testing frontend health endpoint..." -ForegroundColor Green
try {
    $health = Invoke-WebRequest -Uri "http://localhost:80/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Frontend health check: $($health.StatusCode) - $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test main page
Write-Host "📡 Testing main page..." -ForegroundColor Green
try {
    $main = Invoke-WebRequest -Uri "http://localhost:80" -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Main page: $($main.StatusCode)" -ForegroundColor Green
    Write-Host "   Content length: $($main.Content.Length) characters" -ForegroundColor White
    
    # Check if it contains our title
    if ($main.Content -match "GPUDex") {
        Write-Host "✅ Page contains GPUDx content" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Page may not contain expected content" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Main page failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "📋 Error details: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
}

# Test favicon
Write-Host "📡 Testing favicon..." -ForegroundColor Green
try {
    $favicon = Invoke-WebRequest -Uri "http://localhost:80/favicon.svg" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Favicon: $($favicon.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Favicon test: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test nginx load balancer
Write-Host "📡 Testing nginx load balancer..." -ForegroundColor Green
try {
    $nginx = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Nginx load balancer: $($nginx.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Nginx load balancer failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📊 STEP 8: Final container status..." -ForegroundColor Cyan
docker compose ps frontend nginx

Write-Host ""
Write-Host "🎯 DIAGNOSIS COMPLETE!" -ForegroundColor Yellow
Write-Host "=====================" -ForegroundColor Yellow

# Check if frontend is healthy
$containerStatus = docker compose ps frontend --format json | ConvertFrom-Json
if ($containerStatus.Health -eq "healthy") {
    Write-Host "🎉 SUCCESS! Frontend is now healthy and running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 YOUR GPUDX PLATFORM IS READY:" -ForegroundColor Cyan
    Write-Host "   Main Site: http://localhost:80" -ForegroundColor White
    Write-Host "   Load Balancer: http://localhost:8080" -ForegroundColor White
    Write-Host ""
    Write-Host "🔥 BILL GATES HAS FIXED THE 502 ERROR!" -ForegroundColor Red
    Write-Host "📝 Clear your browser cache (Ctrl+F5) and enjoy!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Frontend may still be starting or has issues..." -ForegroundColor Yellow
    Write-Host "🔧 Check the logs above for specific errors" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💪 BILL NEVER GIVES UP! Try these commands:" -ForegroundColor Red
    Write-Host "   docker compose logs frontend" -ForegroundColor White
    Write-Host "   docker compose restart frontend" -ForegroundColor White
}

Write-Host ""
Write-Host "🎊 BONUS: All components are now vanilla JavaScript!" -ForegroundColor Magenta
Write-Host "✅ Staking Dashboard, Achievement System, Influencer Portal" -ForegroundColor Green 