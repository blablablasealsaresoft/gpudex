# GPUDex PowerShell Deployment Script

param(
    [string]$Action = "deploy"
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { Write-Host $args[0] -ForegroundColor Green }
function Write-Info { Write-Host $args[0] -ForegroundColor Cyan }
function Write-Warning { Write-Host $args[0] -ForegroundColor Yellow }
function Write-Error { Write-Host $args[0] -ForegroundColor Red }

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "[ERROR] Docker is not installed. Please install Docker Desktop."
        exit 1
    }
    
    # Check Docker Compose
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "[ERROR] Docker Compose is not installed."
        exit 1
    }
    
    # Check if Docker is running
    try {
        docker info | Out-Null
    } catch {
        Write-Error "[ERROR] Docker is not running. Please start Docker Desktop."
        exit 1
    }
    
    Write-Success "[OK] All prerequisites satisfied"
}

# Create environment file
function New-EnvFile {
    Write-Info "Creating .env.production file..."
    
    if (Test-Path ".env.production") {
        $overwrite = Read-Host ".env.production exists. Overwrite? (y/n)"
        if ($overwrite -ne 'y') {
            return
        }
    }
    
    Copy-Item "docker-quickstart.env" ".env.production"
    Write-Success "[OK] Created .env.production from template"
    Write-Warning "[WARNING] Please edit .env.production with your API keys"
}

# Deploy application
function Start-Deployment {
    Write-Info "Deploying GPUDex..."
    
    # Check environment file
    if (-not (Test-Path ".env.production")) {
        Write-Error "[ERROR] .env.production not found. Run: .\deploy-gpudex.ps1 -Action setup"
        exit 1
    }
    
    # Stop existing containers
    Write-Info "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down
    
    # Build images
    Write-Info "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Start services
    Write-Info "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services
    Write-Info "Waiting for services to start..."
    Start-Sleep -Seconds 30
    
    # Health check
    Write-Info "Running health checks..."
    try {
        $backendHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
        if ($backendHealth) {
            Write-Success "[OK] Backend is healthy"
        }
    } catch {
        Write-Warning "[WARNING] Backend health check failed"
    }
    
    Write-Success "[SUCCESS] Deployment completed!"
    Write-Info ""
    Write-Info "Access your platform:"
    Write-Info "  Frontend: http://localhost:3000"
    Write-Info "  Backend API: http://localhost:8000"
    Write-Info "  API Docs: http://localhost:8000/docs"
    Write-Info "  Grafana: http://localhost:3001 (admin/grafana_secure_2024)"
}

# Main script logic
switch ($Action) {
    "deploy" {
        Test-Prerequisites
        Start-Deployment
    }
    "setup" {
        Test-Prerequisites
        New-EnvFile
        if (Test-Path ".\generate-keys.ps1") {
            & ".\generate-keys.ps1"
        }
    }
    "status" {
        docker-compose -f docker-compose.prod.yml ps
    }
    "logs" {
        docker-compose -f docker-compose.prod.yml logs -f
    }
    "stop" {
        docker-compose -f docker-compose.prod.yml down
        Write-Success "[OK] Services stopped"
    }
    default {
        Write-Host "Usage: .\deploy-gpudex.ps1 -Action {deploy|setup|status|logs|stop}"
        Write-Host "  setup  - Create environment file and generate keys"
        Write-Host "  deploy - Deploy GPUDex to production"
        Write-Host "  status - Show service status"
        Write-Host "  logs   - View application logs"
        Write-Host "  stop   - Stop all services"
    }
}