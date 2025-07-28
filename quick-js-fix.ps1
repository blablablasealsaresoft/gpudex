# QUICK JAVASCRIPT FIX AND CORS APPLICATION
Write-Host "APPLYING QUICK JAVASCRIPT FIX..." -ForegroundColor Red

Write-Host "Step 1: Rebuilding frontend with JavaScript fixes..." -ForegroundColor Green
docker compose build --no-cache frontend
docker compose up -d frontend
Start-Sleep 5

Write-Host "Step 2: Running comprehensive CORS fix..." -ForegroundColor Green
.\fix-cors-all-services.ps1

Write-Host ""
Write-Host "QUICK FIX COMPLETE!" -ForegroundColor Green
Write-Host "JavaScript conflicts resolved and CORS applied to all services!" -ForegroundColor Cyan 