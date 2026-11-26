#!/usr/bin/env pwsh
param(
    [string]$ResourceGroup = "motogp",
    [string]$AppName = "motogp-data",
    [string]$Registry = "motogpacr",
    [string]$Tag = (Get-Date -Format "yyyyMMddHHmmss"),
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Az {
    & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($args -join ' ')"
    }
}

$app = Invoke-Az containerapp show --name $AppName --resource-group $ResourceGroup -o json --only-show-errors | ConvertFrom-Json
if (-not $app.identity.principalId) {
    throw "The app needs its system-assigned identity and read-only SQL access configured first."
}
$production = @($app.properties.configuration.ingress.traffic | Where-Object { $_.weight -eq 100 })
if ($production.Count -ne 1) {
    throw "Expected one production revision at 100%. Resolve existing traffic splits explicitly before deploying."
}
$classic = $production[0].revisionName
if ($production[0].latestRevision) { $classic = $app.properties.latestReadyRevisionName }
if (-not $classic) { throw "Cannot resolve the current production revision." }
$classicImages = Invoke-Az containerapp revision show --name $AppName --resource-group $ResourceGroup `
    --revision $classic --query "properties.template.containers[].image" -o tsv --only-show-errors
if ($classicImages -match "/motogp-preview:") {
    throw "Production already targets a preview image. Refusing to relabel it as classic."
}

$image = "$Registry.azurecr.io/motogp-preview:$Tag"
if ($SkipBuild) {
    Invoke-Az acr repository show --name $Registry --image "motogp-preview:$Tag" --output none --only-show-errors
} else {
    Invoke-Az acr build --registry $Registry --image "motogp-preview:$Tag" --file Dockerfile.preview . --no-logs --output none --only-show-errors
}

Invoke-Az containerapp revision set-mode --name $AppName --resource-group $ResourceGroup --mode multiple --output none --only-show-errors
Invoke-Az containerapp ingress traffic set --name $AppName --resource-group $ResourceGroup `
    --revision-weight "$classic=100" --output none --only-show-errors
Invoke-Az containerapp revision label add --name $AppName --resource-group $ResourceGroup `
    --revision $classic --label classic --yes --output none --only-show-errors

$revision = "$AppName--preview-$Tag"
Invoke-Az containerapp update --name $AppName --resource-group $ResourceGroup `
    --image $image --revision-suffix "preview-$Tag" --set-env-vars "MOTOGP_SQL_AUTH=managed-identity" `
    --query properties.provisioningState -o tsv --only-show-errors

$ready = $false
for ($attempt = 0; $attempt -lt 36; $attempt++) {
    $health = Invoke-Az containerapp revision show --name $AppName --resource-group $ResourceGroup `
        --revision $revision --query properties.healthState -o tsv --only-show-errors
    if ($health -eq "Healthy") { $ready = $true; break }
    if ($health -eq "Unhealthy") { throw "Preview revision is unhealthy; classic traffic has not changed." }
    Start-Sleep -Seconds 5
}
if (-not $ready) { throw "Preview did not become healthy in time; classic traffic has not changed." }

Invoke-Az containerapp revision label add --name $AppName --resource-group $ResourceGroup `
    --revision $revision --label preview --yes --output none --only-show-errors
$live = Invoke-Az containerapp show --name $AppName --resource-group $ResourceGroup `
    --query properties.configuration.ingress -o json --only-show-errors | ConvertFrom-Json
$production = @($live.traffic | Where-Object { $_.weight -eq 100 })
if ($production.Count -ne 1 -or $production[0].revisionName -ne $classic -or $production[0].latestRevision) {
    throw "Production traffic changed unexpectedly. Inspect ingress traffic before continuing."
}
$previewHost = $live.fqdn -replace "^[^.]+", "$AppName---preview"
Write-Host "Classic remains at: https://$($live.fqdn)"
Write-Host "Preview URL: https://$previewHost"
Write-Host "Preview revision: $revision"
