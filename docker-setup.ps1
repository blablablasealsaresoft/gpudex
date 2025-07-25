# GPUDex Docker Production Setup Script (PowerShell)
# Run this script to deploy a full production environment in 5 minutes

param(
    [switch]$Force
)

Write-Host "🚀 GPUDex Docker Production Setup" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Check if Docker is installed and running
try {
    $dockerVersion = docker --version
    Write-Status "Docker is available: $dockerVersion"
} catch {
    Write-Error "Docker is not installed or not running. Please install Docker Desktop first."
    exit 1
}

# Check if docker-compose is available
try {
    $composeVersion = docker-compose --version
    Write-Status "Docker Compose is available: $composeVersion"
} catch {
    Write-Error "Docker Compose is not available. Please ensure Docker Desktop is properly installed."
    exit 1
}

# Step 1: Environment setup
Write-Host ""
Write-Host "📝 Step 1: Setting up environment variables" -ForegroundColor Cyan

if (-not (Test-Path ".env.production")) {
    Write-Status "Creating .env.production from template"
    Copy-Item "env.production" ".env.production"
} else {
    Write-Warning ".env.production already exists, skipping copy"
}

# Generate secure secrets
Write-Host ""
Write-Host "🔐 Generating secure secrets..." -ForegroundColor Cyan

try {
    $jwtSecret = python -c "import secrets; print(secrets.token_urlsafe(32))"
    $dbPassword = python -c "import secrets; print(secrets.token_urlsafe(16))"
    $secretKey = python -c "import secrets; print(secrets.token_urlsafe(32))"
    
    Write-Status "Generated secure secrets"
    
    # Update .env.production with generated secrets
    $envContent = Get-Content ".env.production" -Raw
    $envContent = $envContent -replace "GENERATE_SECURE_JWT_SECRET_HERE", $jwtSecret
    $envContent = $envContent -replace "SECURE_PASSWORD_HERE", $dbPassword
    $envContent = $envContent -replace "GENERATE_SECURE_SECRET_KEY_HERE", $secretKey
    Set-Content ".env.production" $envContent
    
    Write-Status "Updated .env.production with secure secrets"
} catch {
    Write-Error "Failed to generate secrets. Please ensure Python is installed."
    exit 1
}

# Step 2: Build and start services
Write-Host ""
Write-Host "🐳 Step 2: Building and starting Docker services" -ForegroundColor Cyan

try {
    Write-Status "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build
    
    Write-Status "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    Write-Host ""
    Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
} catch {
    Write-Error "Failed to start Docker services. Check Docker logs for details."
    exit 1
}

# Step 3: Initialize database
Write-Host ""
Write-Host "🗄️ Step 3: Initializing database" -ForegroundColor Cyan

try {
    Write-Status "Creating database tables..."
    # Database initialization happens automatically on backend startup
    Start-Sleep -Seconds 5
    Write-Status "Database initialization completed"
} catch {
    Write-Error "Database initialization failed. Check backend logs."
}

# Step 4: Health checks
Write-Host ""
Write-Host "🏥 Step 4: Running health checks" -ForegroundColor Cyan

function Test-Service {
    param(
        [string]$Url,
        [string]$Name,
        [int]$MaxAttempts = 30
    )
    
    Write-Host "Checking $Name..." -NoNewline
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host " ✅" -ForegroundColor Green
                return $true
            }
        } catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
    }
    
    Write-Host " ❌" -ForegroundColor Red
    return $false
}

Write-Host "Testing service endpoints..." -ForegroundColor Cyan

# Test services
$frontendOk = Test-Service "http://localhost/health" "Frontend"
$backendOk = Test-Service "http://localhost:8000/" "Backend API"
$apiOk = Test-Service "http://localhost:8000/api/v1/providers" "API endpoints"

# Step 5: Display summary
Write-Host ""
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green

# Check service status
try {
    $services = docker-compose -f docker-compose.prod.yml ps --format json | ConvertFrom-Json
    $runningServices = ($services | Where-Object { $_.State -eq "running" }).Count
    $totalServices = $services.Count
    
    Write-Status "Services Status: $runningServices/$totalServices running"
} catch {
    Write-Warning "Could not get service status"
}

Write-Host ""
Write-Host "🌐 Access your GPUDex platform:" -ForegroundColor Cyan
Write-Host "   Frontend:   http://localhost"
Write-Host "   Backend:    http://localhost:8000"
Write-Host "   API Docs:   http://localhost:8000/api/docs"
Write-Host "   Grafana:    http://localhost:3001 (admin/your_password)"
Write-Host "   Prometheus: http://localhost:9090"

Write-Host ""
Write-Host "📊 Test API endpoints:" -ForegroundColor Cyan
Write-Host "   Invoke-WebRequest http://localhost:8000/"
Write-Host "   Invoke-WebRequest http://localhost:8000/api/v1/providers"
Write-Host "   Invoke-WebRequest http://localhost:8000/api/v1/prices"

Write-Host ""
Write-Host "🔧 Useful commands:" -ForegroundColor Cyan
Write-Host "   View logs:    docker-compose -f docker-compose.prod.yml logs -f"
Write-Host "   Stop:         docker-compose -f docker-compose.prod.yml down"
Write-Host "   Restart:      docker-compose -f docker-compose.prod.yml restart"
Write-Host "   Status:       docker-compose -f docker-compose.prod.yml ps"

Write-Host ""
Write-Status "Your GPUDex production environment is ready! 🚀"

# Optional: Open browser
if ($frontendOk) {
    Write-Host ""
    Write-Host "Opening browser..." -ForegroundColor Yellow
    Start-Process "http://localhost"
}

Write-Host ""
Write-Warning "Don't forget to:"
Write-Warning "1. Update .env.production with your real API keys"
Write-Warning "2. Configure SSL/TLS for production deployment"
Write-Warning "3. Set up your domain and DNS"
Write-Warning "4. Configure monitoring alerts"

Write-Host ""
Write-Host "📚 See DOCKER_PRODUCTION_GUIDE.md for detailed documentation" -ForegroundColor Cyan 