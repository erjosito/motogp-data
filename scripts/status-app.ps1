#!/usr/bin/env pwsh
# status-app.ps1 — Check the status of the MotoGP Dashboard
# Usage: .\scripts\status-app.ps1

$RG = "motogp"
$APP = "motogp-data"

Write-Host "MotoGP Dashboard Status" -ForegroundColor Cyan
Write-Host "========================"

$info = az containerapp show --name $APP --resource-group $RG -o json 2>&1 | ConvertFrom-Json

if ($info) {
    $fqdn = $info.properties.configuration.ingress.fqdn
    $replicas = $info.properties.template.scale.minReplicas
    $maxReplicas = $info.properties.template.scale.maxReplicas
    $status = $info.properties.runningStatus

    Write-Host "URL:      https://$fqdn"
    Write-Host "Status:   $status"
    Write-Host "Replicas: min=$replicas, max=$maxReplicas"

    if ($replicas -eq 0 -and $maxReplicas -eq 0) {
        Write-Host "State:    STOPPED (no cost)" -ForegroundColor Yellow
    } else {
        Write-Host "State:    RUNNING" -ForegroundColor Green
    }
} else {
    Write-Host "Container app not found. Has it been deployed?" -ForegroundColor Red
}
