# GPUDex Quick Deploy Script
# Starts the full production environment with one command

Write-Host "🚀 GPUDex Quick Deploy" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

# Check Docker
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check Docker Compose
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose not found. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host ""
Write-Host "🧹 Cleaning up any existing containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.prod.yml down 2>$null

# Start the production environment
Write-Host ""
Write-Host "🚀 Starting GPUDex production environment..." -ForegroundColor Cyan
docker-compose -f docker-compose.prod.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 GPUDex is starting up!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Services:" -ForegroundColor Yellow
    Write-Host "• Frontend:    http://localhost" -ForegroundColor White
    Write-Host "• Backend API: http://localhost:8000" -ForegroundColor White
    Write-Host "• Grafana:     http://localhost:3001 (admin/grafana_secure_2024)" -ForegroundColor White
    Write-Host "• Prometheus:  http://localhost:9090" -ForegroundColor White
    Write-Host ""
    Write-Host "⏳ Services are starting... Give it 30-60 seconds to fully initialize." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📋 To check status: docker-compose -f docker-compose.prod.yml ps" -ForegroundColor Cyan
    Write-Host "📋 To view logs:    docker-compose -f docker-compose.prod.yml logs -f" -ForegroundColor Cyan
    Write-Host "📋 To stop:        docker-compose -f docker-compose.prod.yml down" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Failed to start services. Check the logs:" -ForegroundColor Red
    Write-Host "docker-compose -f docker-compose.prod.yml logs" -ForegroundColor Yellow
} 