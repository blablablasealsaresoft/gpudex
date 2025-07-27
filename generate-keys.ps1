# GPUDex Security Key Generator for PowerShell

Write-Host "Generating secure keys for GPUDex Production..." -ForegroundColor Green
Write-Host ""

# Function to generate secure random string
function New-SecureString {
    param([int]$Length = 32)
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*'
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::Create()
    $rng.GetBytes($bytes)
    
    $result = ''
    foreach ($byte in $bytes) {
        $result += $chars[$byte % $chars.Length]
    }
    return $result
}

# Generate keys
$keys = @{
    'JWT_SECRET_KEY' = New-SecureString -Length 32
    'SECRET_KEY' = New-SecureString -Length 32
    'ENCRYPTION_KEY' = New-SecureString -Length 32
    'POSTGRES_PASSWORD' = New-SecureString -Length 24
}

# Display keys
Write-Host "Copy these to your .env.production file:" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow
foreach ($key in $keys.GetEnumerator()) {
    Write-Host "$($key.Name)=$($key.Value)" -ForegroundColor Cyan
}
Write-Host "=========================================" -ForegroundColor Yellow

# Save to file option
$save = Read-Host "Save to keys.txt? (y/n)"
if ($save -eq 'y') {
    $keys.GetEnumerator() | ForEach-Object {
        "$($_.Name)=$($_.Value)"
    } | Out-File -FilePath "keys.txt"
    Write-Host "[SUCCESS] Keys saved to keys.txt" -ForegroundColor Green
}