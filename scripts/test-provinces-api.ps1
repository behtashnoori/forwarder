# Test provinces API endpoint from network perspective
$serverIP = "130.185.77.25"
$apiPort = 5000

Write-Host "Testing Provinces API Endpoint..." -ForegroundColor Cyan
Write-Host "Server IP: $serverIP`:$apiPort" -ForegroundColor Yellow
Write-Host ""

# Test OPTIONS (CORS preflight)
Write-Host "Test 1: OPTIONS request (CORS preflight)..." -ForegroundColor Cyan
try {
    $optionsResponse = Invoke-WebRequest -Uri "http://${serverIP}:${apiPort}/api/provinces" `
        -Method OPTIONS `
        -Headers @{
            "Origin" = "http://${serverIP}:8080"
            "Access-Control-Request-Method" = "GET"
        } `
        -TimeoutSec 5 `
        -ErrorAction Stop
    
    Write-Host "  OK OPTIONS successful" -ForegroundColor Green
    Write-Host "  Status: $($optionsResponse.StatusCode)" -ForegroundColor Green
    Write-Host "  CORS Headers:" -ForegroundColor Cyan
    $ao = $optionsResponse.Headers['Access-Control-Allow-Origin']; if ($ao) { Write-Host "    Access-Control-Allow-Origin: $ao" -ForegroundColor White }
    $am = $optionsResponse.Headers['Access-Control-Allow-Methods']; if ($am) { Write-Host "    Access-Control-Allow-Methods: $am" -ForegroundColor White }
} catch {
    Write-Host "  OPTIONS failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test GET request
Write-Host "Test 2: GET request (actual data)..." -ForegroundColor Cyan
try {
    $getResponse = Invoke-WebRequest -Uri "http://${serverIP}:${apiPort}/api/provinces" `
        -Method GET `
        -Headers @{
            "Origin" = "http://${serverIP}:8080"
        } `
        -TimeoutSec 5 `
        -ErrorAction Stop
    
    Write-Host "  OK GET successful" -ForegroundColor Green
    Write-Host "  Status: $($getResponse.StatusCode)" -ForegroundColor Green
    
    $data = $getResponse.Content | ConvertFrom-Json
    $count = if ($data -is [Array]) { $data.Count } else { @($data).Count }
    Write-Host "  Found $count provinces" -ForegroundColor Green
    
    if ($count -gt 0) {
        Write-Host "  Sample provinces:" -ForegroundColor Cyan
        $arr = @($data)
        $arr[0..([Math]::Min(2, $arr.Count - 1))] | ForEach-Object {
            Write-Host "    - $($_.name) (ID: $($_.id))" -ForegroundColor White
        }
    }
    
    $ao = $getResponse.Headers['Access-Control-Allow-Origin']
    if ($ao) { Write-Host "  CORS Access-Control-Allow-Origin: $ao" -ForegroundColor Cyan }
    
} catch {
    Write-Host "  GET failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        try { Write-Host "  Status Code: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Yellow } catch {}
    }
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  If OPTIONS works but GET fails, check:" -ForegroundColor Yellow
Write-Host "  1. Backend was restarted after code changes" -ForegroundColor White
Write-Host "  2. Database connection is working" -ForegroundColor White
Write-Host "  3. CORS headers are correct (not using '*')" -ForegroundColor White
Write-Host ""
Write-Host "  If both fail, check:" -ForegroundColor Yellow
Write-Host "  1. Backend is running: python backend/wsgi.py" -ForegroundColor White
Write-Host "  2. Backend listens on 0.0.0.0 (not 127.0.0.1)" -ForegroundColor White
Write-Host "  3. Firewall allows port $apiPort" -ForegroundColor White
