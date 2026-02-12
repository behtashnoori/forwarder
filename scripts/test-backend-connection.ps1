# Test Backend API connection from network/internet perspective
# This script checks if the backend is accessible

$serverIP = "130.185.77.25"
$apiPort = 5000
$frontendPort = 8080

Write-Host "Testing Backend API Connection..." -ForegroundColor Cyan
Write-Host "Server IP: $serverIP" -ForegroundColor Yellow
Write-Host ""

# Test 1: Check if backend is running locally
Write-Host "Test 1: Checking local backend (127.0.0.1:$apiPort)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$apiPort/api/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Backend is running locally" -ForegroundColor Green
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Backend is NOT running locally" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Solution: Start backend with:" -ForegroundColor Yellow
    Write-Host "    python backend/wsgi.py" -ForegroundColor White
    Write-Host "  Or set FLASK_RUN_HOST=0.0.0.0" -ForegroundColor White
}

Write-Host ""

# Test 2: Check if backend is accessible from network IP
Write-Host "Test 2: Checking network backend ($serverIP`:$apiPort)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://$serverIP`:$apiPort/api/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Backend is accessible from network" -ForegroundColor Green
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Backend is NOT accessible from network" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Possible causes:" -ForegroundColor Yellow
    Write-Host "  1. Backend is running on 127.0.0.1 instead of 0.0.0.0" -ForegroundColor White
    Write-Host "  2. Firewall is blocking port $apiPort" -ForegroundColor White
    Write-Host "  3. External firewall/router is blocking port $apiPort" -ForegroundColor White
    Write-Host ""
    Write-Host "  Solutions:" -ForegroundColor Yellow
    Write-Host "  - Set FLASK_RUN_HOST=0.0.0.0 in .env or environment" -ForegroundColor White
    Write-Host "  - Run: python backend/wsgi.py (defaults to 0.0.0.0)" -ForegroundColor White
    Write-Host "  - Check firewall: Get-NetFirewallRule -DisplayName '*5000*'" -ForegroundColor White
}

Write-Host ""

# Test 3: Test provinces endpoint
Write-Host "Test 3: Testing provinces API endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://$serverIP`:$apiPort/api/provinces" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $data = $response.Content | ConvertFrom-Json
    Write-Host "  ✓ Provinces endpoint works" -ForegroundColor Green
    Write-Host "  Found $($data.Count) provinces" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Provinces endpoint failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Frontend URL: http://$serverIP`:$frontendPort" -ForegroundColor White
Write-Host "  Backend API URL: http://$serverIP`:$apiPort" -ForegroundColor White
Write-Host ""
Write-Host "If tests fail, check:" -ForegroundColor Yellow
Write-Host "  1. Backend is running: python backend/wsgi.py" -ForegroundColor White
Write-Host "  2. Backend listens on 0.0.0.0 (check wsgi.py or FLASK_RUN_HOST)" -ForegroundColor White
Write-Host "  3. Firewall allows port $apiPort: npm run firewall:open" -ForegroundColor White
Write-Host "  4. External firewall/router allows port $apiPort" -ForegroundColor White
