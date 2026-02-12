# Open ports 8080 (frontend) and 5000 (backend API) in Windows Firewall for network/internet access
# Run this script as Administrator (Right-click PowerShell -> Run as Administrator)

$ports = @(
    @{ Port = 8080; Name = "Vite Dev Server - Port 8080" },
    @{ Port = 5000; Name = "Flask API - Port 5000" }
)

foreach ($item in $ports) {
    $ruleName = $item.Name
    $port = $item.Port
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Firewall rule '$ruleName' already exists." -ForegroundColor Yellow
        continue
    }
    try {
        New-NetFirewallRule -DisplayName $ruleName `
            -Direction Inbound `
            -LocalPort $port `
            -Protocol TCP `
            -Action Allow `
            -Profile Any
        Write-Host "Port $port opened in firewall successfully." -ForegroundColor Green
    } catch {
        Write-Host "Error adding $ruleName : $_" -ForegroundColor Red
    }
}
Write-Host "Frontend: http://YOUR_SERVER_IP:8080  |  API: http://YOUR_SERVER_IP:5000" -ForegroundColor Cyan
