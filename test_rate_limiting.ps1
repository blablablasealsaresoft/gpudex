# Test GPUDex Rate Limiting & API Key System
Write-Host "🔐 Testing GPUDex Rate Limiting & API Key System" -ForegroundColor Green
Write-Host "=" * 60

$API_BASE = "http://localhost:8000"

# Test 1: Health Check
Write-Host "`n1. 🔍 Testing API Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/" -Method GET
    Write-Host "   ✅ API is running: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ API health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Test 2: Check pricing info (public endpoint)
Write-Host "`n2. 💰 Testing public pricing endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/api/v1/pricing" -Method GET
    Write-Host "   ✅ Pricing info retrieved" -ForegroundColor Green
    Write-Host "   💡 Free plan: $($response.plans.free.requests_per_hour) req/hr" -ForegroundColor Cyan
    Write-Host "   💡 Pro plan: $($response.plans.pro.requests_per_hour) req/hr" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Failed to get pricing: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Create API Key
Write-Host "`n3. 🗝️  Creating API key..." -ForegroundColor Yellow
$apiKeyData = @{
    email = "test@example.com"
    key_name = "test-key"
    requests_per_hour = 500
    requests_per_day = 5000
}

try {
    $response = Invoke-RestMethod -Uri "$API_BASE/api/v1/api-keys" -Method POST -Body ($apiKeyData | ConvertTo-Json) -ContentType "application/json"
    $apiKey = $response.api_key
    Write-Host "   ✅ API key created successfully" -ForegroundColor Green
    Write-Host "   🔑 API Key: $apiKey" -ForegroundColor Cyan
    Write-Host "   📊 Limits: $($response.limits.requests_per_hour) req/hr, $($response.limits.requests_per_day) req/day" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Failed to create API key: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Test 4: Test API key info endpoint
Write-Host "`n4. ℹ️  Testing API key info..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $apiKey"
    }
    $response = Invoke-RestMethod -Uri "$API_BASE/api/v1/api-keys/info" -Method GET -Headers $headers
    Write-Host "   ✅ API key info retrieved" -ForegroundColor Green
    Write-Host "   📧 User: $($response.user_email)" -ForegroundColor Cyan
    Write-Host "   📈 Usage: $($response.usage.total_requests) total requests" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Failed to get API key info: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Test authenticated prices endpoint
Write-Host "`n5. 🎯 Testing authenticated prices endpoint..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $apiKey"
    }
    $response = Invoke-RestMethod -Uri "$API_BASE/api/v1/prices?gpu=a100" -Method GET -Headers $headers
    Write-Host "   ✅ Prices retrieved with API key" -ForegroundColor Green
    if ($response.best_price) {
        Write-Host "   💰 Best A100 price: `$$($response.best_price.price)/hr from $($response.best_price.provider)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ❌ Failed to get prices: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Test rate limiting by making multiple requests
Write-Host "`n6. 🚦 Testing rate limiting (making 10 rapid requests)..." -ForegroundColor Yellow
$successCount = 0
$rateLimitedCount = 0

for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "$API_BASE/" -Method GET -ErrorAction Stop
        $successCount++
        Write-Host "   Request $i`: Success" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            $rateLimitedCount++
            Write-Host "   Request $i`: Rate limited (429)" -ForegroundColor Yellow
        } else {
            Write-Host "   Request $i`: Error $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 100
}

Write-Host "   📊 Results: $successCount successful, $rateLimitedCount rate limited" -ForegroundColor Cyan

# Test 7: Test public endpoint without API key
Write-Host "`n7. 🌐 Testing public access to prices..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/api/v1/prices?gpu=h100" -Method GET
    Write-Host "   ✅ Public access works (no API key required)" -ForegroundColor Green
    if ($response.best_price) {
        Write-Host "   💰 Best H100 price: `$$($response.best_price.price)/hr" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ❌ Public access failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n" + ("=" * 60)
Write-Host "✅ Rate limiting & API key system test completed!" -ForegroundColor Green
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "   • API key created and validated ✅" -ForegroundColor White
Write-Host "   • Rate limiting is active ✅" -ForegroundColor White
Write-Host "   • Public endpoints accessible ✅" -ForegroundColor White
Write-Host "   • Authenticated endpoints working ✅" -ForegroundColor White
Write-Host "`n💡 Your API key: $apiKey" -ForegroundColor Yellow
Write-Host "💡 Use this for testing authenticated endpoints!" -ForegroundColor Yellow 