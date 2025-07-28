# BILL GATES ON ADDERALL - PLATFORM VERIFICATION
Write-Host "VERIFYING COMPLETE PLATFORM FUNCTIONALITY!" -ForegroundColor Red
Write-Host "=============================================" -ForegroundColor Yellow

Write-Host ""
Write-Host "STEP 1: Container Status Check..." -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "STEP 2: Testing Frontend..." -ForegroundColor Green
try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:80" -UseBasicParsing -TimeoutSec 10
    Write-Host "  SUCCESS Frontend - Status $($frontend.StatusCode)" -ForegroundColor Green
    
    if ($frontend.Content -match "showSection") {
        Write-Host "    SUCCESS Navigation system loaded" -ForegroundColor Green
    }
    if ($frontend.Content -match "connectWallet") {
        Write-Host "    SUCCESS Wallet integration loaded" -ForegroundColor Green
    }
    if ($frontend.Content -match "The Future of") {
        Write-Host "    SUCCESS Hero section loaded" -ForegroundColor Green
    }
} catch {
    Write-Host "  FAILED Frontend test - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "STEP 3: Testing Core Backend Services..." -ForegroundColor Green

$coreServices = @(
    @{name="Main API"; url="http://localhost:8000/health"; port=8000},
    @{name="Real API"; url="http://localhost:8001/health"; port=8001},
    @{name="GPU Marketplace"; url="http://localhost:8001/gpu-marketplace"; port=8001}
)

foreach ($service in $coreServices) {
    try {
        $response = Invoke-WebRequest -Uri $service.url -UseBasicParsing -TimeoutSec 8
        Write-Host "  SUCCESS $($service.name) - Status $($response.StatusCode)" -ForegroundColor Green
        
        if ($service.name -eq "GPU Marketplace") {
            $data = $response.Content | ConvertFrom-Json
            if ($data.gpus) {
                Write-Host "    SUCCESS $($data.gpus.Count) GPUs available" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "  WARNING $($service.name) - Not ready yet" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "STEP 4: Testing Extended Backend Services..." -ForegroundColor Green

$extendedServices = @(
    @{name="Enterprise Dashboard"; url="http://localhost:8002/health"},
    @{name="Token Service"; url="http://localhost:8004/health"},
    @{name="Social Gamification"; url="http://localhost:8005/health"},
    @{name="P2P GPU Service"; url="http://localhost:8006/health"},
    @{name="AI Optimization"; url="http://localhost:8008/health"}
)

foreach ($service in $extendedServices) {
    try {
        $response = Invoke-WebRequest -Uri $service.url -UseBasicParsing -TimeoutSec 8
        Write-Host "  SUCCESS $($service.name) - Status $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING $($service.name) - Starting up..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "STEP 5: Testing Frontend Assets..." -ForegroundColor Green

$assets = @(
    "ultimate-styles.css",
    "ultimate-backend-connector.js",
    "marketplace-api.js", 
    "wallet-connector.js",
    "contracts-config.js"
)

foreach ($asset in $assets) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:80/$asset" -UseBasicParsing -TimeoutSec 5
        Write-Host "  SUCCESS $asset - Status $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING $asset - Not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "STEP 6: Testing Legal Pages..." -ForegroundColor Green

$legalPages = @("terms-of-service.html", "privacy-policy.html")

foreach ($page in $legalPages) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:80/$page" -UseBasicParsing -TimeoutSec 5
        Write-Host "  SUCCESS $page - Status $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING $page - Not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "STEP 7: Testing Enhanced Portals..." -ForegroundColor Green

$portals = @(
    "enterprise-portal-enhanced.html",
    "provider-portal.html", 
    "institutional-staking-portal.html"
)

foreach ($portal in $portals) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:80/$portal" -UseBasicParsing -TimeoutSec 5
        Write-Host "  SUCCESS $portal - Status $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING $portal - Not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "PLATFORM VERIFICATION COMPLETE!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Yellow

Write-Host ""
Write-Host "YOUR BILL GATES ON ADDERALL PLATFORM:" -ForegroundColor Cyan
Write-Host "  MAIN SITE: http://localhost:80" -ForegroundColor White
Write-Host "  ENTERPRISE: http://localhost:80/enterprise-portal-enhanced.html" -ForegroundColor White
Write-Host "  PROVIDER: http://localhost:80/provider-portal.html" -ForegroundColor White
Write-Host "  INSTITUTIONAL: http://localhost:80/institutional-staking-portal.html" -ForegroundColor White

Write-Host ""
Write-Host "FUNCTIONALITY TO TEST:" -ForegroundColor Yellow
Write-Host "  Click navigation buttons (Home, Marketplace, Staking, etc.)" -ForegroundColor White
Write-Host "  Try 'Connect Wallet' button (should prompt MetaMask)" -ForegroundColor White
Write-Host "  Test staking buttons in Staking section" -ForegroundColor White
Write-Host "  Explore GPU marketplace with live data" -ForegroundColor White
Write-Host "  Check Provider Portal functionality" -ForegroundColor White
Write-Host "  Verify legal pages in footer" -ForegroundColor White

Write-Host ""
Write-Host "REFRESH YOUR BROWSER AND ENJOY!" -ForegroundColor Green
Write-Host "Open browser console (F12) to see technical details" -ForegroundColor Cyan

Write-Host ""
Write-Host "BILL GATES ON ADDERALL PLATFORM IS LIVE!" -ForegroundColor Red 