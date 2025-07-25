# Test GPUDex Email Alert System
Write-Host "🧪 Testing GPUDex Email Alert System" -ForegroundColor Green
Write-Host "=" * 50

# Test 1: Health Check
Write-Host "`n1. 🔍 Testing API Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/" -Method GET
    Write-Host "   ✅ API is running" -ForegroundColor Green
} catch {
    Write-Host "   ❌ API health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Test 2: Create Alert (Should send welcome email)
Write-Host "`n2. 📧 Creating price alert (should send welcome email)..." -ForegroundColor Yellow
$alertData = @{
    email = "test@example.com"
    gpu_type = "a100"
    target_price = 5.0
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/alerts" -Method POST -Body ($alertData | ConvertTo-Json) -ContentType "application/json"
    Write-Host "   ✅ Alert created successfully" -ForegroundColor Green
    Write-Host "   📧 Welcome email sent: $($response.welcome_sent)" -ForegroundColor Cyan
    Write-Host "   🆔 Alert ID: $($response.alert_id)" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Failed to create alert: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check Current Prices
Write-Host "`n3. 💰 Checking current GPU prices..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/prices?gpu=a100&region=us-east" -Method GET
    $bestPrice = $response.best_price
    Write-Host "   ✅ Current A100 best price: `$$($bestPrice.price)/hr from $($bestPrice.provider)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to get prices: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Create Low-Price Alert (Should trigger price notification eventually)
Write-Host "`n4. 🎯 Creating low-price alert (should trigger price notification)..." -ForegroundColor Yellow
$lowPriceAlert = @{
    email = "test@example.com"
    gpu_type = "a100"
    target_price = 0.1
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/alerts" -Method POST -Body ($lowPriceAlert | ConvertTo-Json) -ContentType "application/json"
    Write-Host "   ✅ Low-price alert created" -ForegroundColor Green
    Write-Host "   ⏳ Background service will check this alert in ~5 minutes" -ForegroundColor Cyan
    Write-Host "   🆔 Alert ID: $($response.alert_id)" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Failed to create low-price alert: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Environment Check
Write-Host "`n5. 🔧 Checking email configuration..." -ForegroundColor Yellow
$sendgridKey = $env:SENDGRID_API_KEY
$fromEmail = if ($env:FROM_EMAIL) { $env:FROM_EMAIL } else { "alerts@gpudex.com" }

if ($sendgridKey) {
    Write-Host "   ✅ SendGrid API key configured" -ForegroundColor Green
    Write-Host "   📧 From email: $fromEmail" -ForegroundColor Cyan
} else {
    Write-Host "   ⚠️  SendGrid API key not set - emails will be logged but not sent" -ForegroundColor Yellow
    Write-Host "   💡 Set SENDGRID_API_KEY environment variable to enable real emails" -ForegroundColor Cyan
}

Write-Host "`n" + ("=" * 50)
Write-Host "✅ Email system test completed!" -ForegroundColor Green
Write-Host "`n📧 If SendGrid is configured, check test@example.com for:" -ForegroundColor Cyan
Write-Host "   • Welcome email (from first alert)" -ForegroundColor White
Write-Host "   • Price alert (if target was met)" -ForegroundColor White
Write-Host "`n⏳ Background alert checker runs every 5 minutes" -ForegroundColor Yellow
Write-Host "📊 Check Docker logs: docker-compose logs backend" -ForegroundColor Yellow 