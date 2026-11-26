#!/usr/bin/env pwsh
# start-app.ps1 — Start the MotoGP Dashboard container app
# Usage: .\scripts\start-app.ps1

$RG = "motogp"
$APP = "motogp-data"
$ENV = "motogp-env"

Write-Host "Starting MotoGP Dashboard..." -ForegroundColor Green

# Scale to 1 instance (min=0 means it auto-scales to zero when idle)
az containerapp update --name $APP --resource-group $RG `
    --min-replicas 1 --max-replicas 1 `
    --output none 2>&1

if ($LASTEXITCODE -eq 0) {
    $fqdn = az containerapp show --name $APP --resource-group $RG --query "properties.configuration.ingress.fqdn" -o tsv
    Write-Host "Dashboard is running at: https://$fqdn" -ForegroundColor Cyan
} else {
    Write-Host "Failed to start. Check Azure portal for details." -ForegroundColor Red
}
