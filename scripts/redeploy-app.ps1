#!/usr/bin/env pwsh
# redeploy-app.ps1 — Rebuild and redeploy the dashboard after code changes
# Usage: .\scripts\redeploy-app.ps1

$RG = "motogp"
$APP = "motogp-data"
$ACR = "motogpacr"
$TAG = Get-Date -Format "yyyyMMddHHmmss"
$IMAGE = "motogp-dashboard:$TAG"

$principalId = az containerapp show --name $APP --resource-group $RG `
    --query identity.principalId --output tsv
if ($LASTEXITCODE -ne 0) {
    throw "Cannot inspect container app identity. Check az login and the selected subscription."
}
if (-not $principalId) {
    throw "Enable the app's system-assigned managed identity and grant SQL access first. See README.md."
}

Write-Host "Rebuilding and redeploying MotoGP Dashboard..." -ForegroundColor Cyan
Write-Host "Image tag: $TAG"

# Build new image in ACR
Write-Host "`n[1/2] Building Docker image in ACR..." -ForegroundColor Yellow
az acr build --registry $ACR --image $IMAGE --file Dockerfile . 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Update container app with new image
Write-Host "`n[2/2] Updating container app..." -ForegroundColor Yellow
az containerapp update --name $APP --resource-group $RG `
    --image "$ACR.azurecr.io/$IMAGE" `
    --set-env-vars "MOTOGP_SQL_AUTH=managed-identity" `
    --remove-env-vars MOTOGP_SQL_CONN_STR `
    --output none 2>&1

if ($LASTEXITCODE -eq 0) {
    $fqdn = az containerapp show --name $APP --resource-group $RG --query "properties.configuration.ingress.fqdn" -o tsv
    Write-Host "`nRedeployed successfully!" -ForegroundColor Green
    Write-Host "URL: https://$fqdn" -ForegroundColor Cyan
    Write-Host "Image: $IMAGE" -ForegroundColor Gray
} else {
    Write-Host "Redeploy failed. Check Azure portal." -ForegroundColor Red
}
