# GPUDex Environment Configuration Editor

$envFile = ".env.production"

if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env.production..." -ForegroundColor Yellow
    Copy-Item "docker-quickstart.env" $envFile
}

# Read current environment
$env = Get-Content $envFile

Write-Host "🔧 GPUDex Environment Configuration" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Function to update a key
function Set-EnvVar {
    param($Key, $Value, $Description)
    
    Write-Host ""
    Write-Host $Description -ForegroundColor Cyan
    $current = ($env | Where-Object { $_ -match "^$Key=" }) -replace "^$Key=", ""
    Write-Host "Current: $current" -ForegroundColor Gray
    
    $newValue = Read-Host "New value (press Enter to keep current)"
    if ($newValue) {
        $env = $env -replace "^$Key=.*", "$Key=$newValue"
        return $true
    }
    return $false
}

$changed = $false

# Critical configurations
Write-Host "`n📌 CRITICAL CONFIGURATIONS" -ForegroundColor Yellow
$changed = Set-EnvVar "SENDGRID_API_KEY" "SendGrid API Key for email notifications" -or $changed
$changed = Set-EnvVar "STRIPE_SECRET_KEY" "Stripe Secret Key (sk_live_...)" -or $changed
$changed = Set-EnvVar "STRIPE_PUBLISHABLE_KEY" "Stripe Publishable Key (pk_live_...)" -or $changed

# GPU Providers
Write-Host "`n🖥️ GPU PROVIDER API KEYS" -ForegroundColor Yellow
$changed = Set-EnvVar "VAST_API_KEY" "Vast.ai API Key" -or $changed
$changed = Set-EnvVar "RUNPOD_API_KEY" "RunPod API Key" -or $changed
$changed = Set-EnvVar "LAMBDA_API_KEY" "Lambda Labs API Key" -or $changed

# Save changes
if ($changed) {
    $env | Out-File $envFile -Encoding UTF8
    Write-Host "`n✅ Configuration saved to $envFile" -ForegroundColor Green
} else {
    Write-Host "`n❌ No changes made" -ForegroundColor Yellow
}