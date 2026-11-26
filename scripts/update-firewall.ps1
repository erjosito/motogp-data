#!/usr/bin/env pwsh
# update-firewall.ps1 — Update the SQL firewall rule for your current IP
# Usage: .\scripts\update-firewall.ps1

$RG = "motogp"
$SERVER = "motogp-sql-srv"

$myIp = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10)
Write-Host "Your current IP: $myIp" -ForegroundColor Cyan

az sql server firewall-rule update --resource-group $RG --server $SERVER `
    --name AllowMyIP --start-ip-address $myIp --end-ip-address $myIp `
    --output none 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Firewall updated. You can now connect to the database." -ForegroundColor Green
} else {
    Write-Host "Failed to update firewall." -ForegroundColor Red
}
