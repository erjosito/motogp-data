#!/usr/bin/env pwsh
# stop-app.ps1 — Stop the MotoGP Dashboard container app (scale to zero)
# Usage: .\scripts\stop-app.ps1

$RG = "motogp"
$APP = "motogp-data"

Write-Host "Stopping MotoGP Dashboard..." -ForegroundColor Yellow

# Scale to 0 min replicas, 1 max — app will auto-scale to zero when idle
az containerapp update --name $APP --resource-group $RG `
    --min-replicas 0 --max-replicas 1 `
    --output none 2>&1

# Then deactivate the latest revision to fully stop it
$revision = az containerapp revision list --name $APP --resource-group $RG --query "[0].name" -o tsv
if ($revision) {
    az containerapp revision deactivate --name $APP --resource-group $RG --revision $revision --output none 2>&1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Dashboard stopped. No instances running, no cost incurred." -ForegroundColor Green
} else {
    Write-Host "Failed to stop. Check Azure portal for details." -ForegroundColor Red
}
