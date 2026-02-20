# Open ports 8080 (frontend) and 5001 (backend API) in Windows Firewall for external access
# Run as Administrator: Right-click PowerShell -> Run as Administrator, then:
#   cd C:\1-webapp\1-forwarder
#   .\scripts\open-firewall-port.ps1
# Or: npm run firewall:open (still needs Admin PowerShell)

$ports = @(
    @{ Port = 8080; Name = "Forwarder Frontend (Vite) - 8080" },
    @{ Port = 5001; Name = "Forwarder Backend (Flask API) - 5001" }
)

Write-Host "`nOpening Windows Firewall for external access (Inbound TCP):" -ForegroundColor Cyan
foreach ($item in $ports) {
    $ruleName = $item.Name
    $port = $item.Port
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  Rule already exists: $ruleName" -ForegroundColor Yellow
        continue
    }
    try {
        New-NetFirewallRule -DisplayName $ruleName `
            -Direction Inbound `
            -LocalPort $port `
            -Protocol TCP `
            -Action Allow `
            -Profile Any
        Write-Host "  Port $port opened: $ruleName" -ForegroundColor Green
    } catch {
        Write-Host "  Error: $ruleName - $_" -ForegroundColor Red
    }
}
Write-Host "`nFrom outside server use:  http://YOUR_SERVER_IP:8080  and  http://YOUR_SERVER_IP:5001" -ForegroundColor Cyan
Write-Host "Replace YOUR_SERVER_IP with this machine's IP (e.g. 130.185.77.25).`n" -ForegroundColor Gray
