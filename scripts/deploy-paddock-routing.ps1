#!/usr/bin/env pwsh
param(
    [string]$ResourceGroup = "motogp",
    [string]$AppName = "motogp-data",
    [string]$Environment = "motogp-env",
    [string]$RouteName = "paddock",
    [switch]$BindDomains
)

$ErrorActionPreference = "Stop"
$snapshotPath = Join-Path $PSScriptRoot "..\.azure\paddock-domain-bindings.json"
$routePath = Join-Path $PSScriptRoot "..\infra\paddock-route.json"

function Invoke-Az {
    & az @args --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI failed: $($args -join ' ')" }
}

function Assert-Endpoint([string]$Base) {
    $html = Invoke-WebRequest "$Base/" -TimeoutSec 120 -UseBasicParsing
    if ($html.Content -notmatch "streamlit") { throw "$Base/ is not serving Classic." }
    $page = Invoke-WebRequest "$Base/paddock/" -TimeoutSec 120 -UseBasicParsing
    if ($page.Content -notmatch 'type="module"') { throw "$Base/paddock/ is not serving React." }
    $health = Invoke-RestMethod "$Base/paddock/api/health" -TimeoutSec 120
    if ($health.status -ne "ok") { throw "Paddock API health failed." }
    $champ = Invoke-RestMethod "$Base/paddock/api/championship?season=2025" -TimeoutSec 120
    if ($champ.story.headline -ne "Back to the summit.") { throw "SQL-backed 2025 story was not served." }
}

function Wait-Endpoint([string]$Base) {
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        try {
            Assert-Endpoint $Base
            return
        } catch {
            if ($attempt -eq 6) { throw }
            Write-Warning "Endpoint not ready yet ($attempt/6): $($_.Exception.Message)"
            Start-Sleep -Seconds 10
        }
    }
}

$app = Invoke-Az containerapp show -g $ResourceGroup -n $AppName -o json | ConvertFrom-Json
foreach ($label in @("classic", "preview")) {
    $targets = @($app.properties.configuration.ingress.traffic | Where-Object label -eq $label)
    if ($targets.Count -ne 1) { throw "Exactly one active '$label' label is required." }
}
$production = @($app.properties.configuration.ingress.traffic | Where-Object weight -eq 100)
if ($production.Count -ne 1 -or $production[0].label -ne "classic" -or $production[0].latestRevision) {
    throw "Production must be explicitly pinned 100% to Classic before configuring routes."
}
$rules = Get-Content -LiteralPath $routePath -Raw | ConvertFrom-Json
foreach ($rule in $rules.rules) { $rule.targets[0].containerApp = $AppName }
$env = Invoke-Az containerapp env show -g $ResourceGroup -n $Environment -o json | ConvertFrom-Json
$routeUrl = "https://management.azure.com$($env.id)/httpRouteConfigs/$RouteName`?api-version=2026-07-01"
$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("paddock-" + [guid]::NewGuid() + ".json")
try {
    $existing = @(Invoke-Az containerapp env http-route-config list -g $ResourceGroup -n $Environment -o json | ConvertFrom-Json)
    $route = $existing | Where-Object name -eq $RouteName
    $properties = @{ rules = $rules.rules; customDomains = @() }
    if ($route) {
        if ($route.properties.rules.Count -ne 2 -or
            $route.properties.rules[0].targets[0].containerApp -ne $AppName -or
            $route.properties.rules[0].targets[0].label -ne "preview" -or
            $route.properties.rules[1].targets[0].label -ne "classic") {
            throw "Existing route does not match this deployment; refusing to replace unrelated rules."
        }
        $properties.customDomains = @($route.properties.customDomains | Where-Object { $_ })
        if (@($properties.customDomains | Where-Object {
            $_.name -notin @("motogp-data.com", "www.motogp-data.com")
        }).Count) { throw "Existing route contains unrelated hostnames; refusing to replace it." }
    }
    @{ properties = $properties } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tempPath -Encoding utf8
    $route = Invoke-Az rest --method put --url $routeUrl --body "@$tempPath" -o json | ConvertFrom-Json
    for ($attempt = 0; $attempt -lt 30 -and -not $route.properties.fqdn; $attempt++) {
        Start-Sleep -Seconds 5
        $route = Invoke-Az rest --method get --url $routeUrl -o json | ConvertFrom-Json
    }
    if (-not $route.properties.fqdn) { throw "Route did not receive an endpoint; domain bindings are unchanged." }
    $routeBase = "https://$($route.properties.fqdn)"
    Wait-Endpoint $routeBase
    Write-Host "Route host verified: $routeBase/paddock/"
    if (-not $BindDomains) {
        Write-Host "Custom-domain bindings unchanged. Run with -BindDomains after route-host browser verification."
        return
    }

    $domains = @($app.properties.configuration.ingress.customDomains | Where-Object {
        $_.name -in @("motogp-data.com", "www.motogp-data.com")
    })
    if ($domains.Count -eq 0) {
        if (@($properties.customDomains).Count -ne 2) { throw "Expected existing app bindings or two migrated route bindings." }
        foreach ($domain in $properties.customDomains) { Wait-Endpoint "https://$($domain.name)" }
        Write-Host "Paddock domain routing is already configured."
        return
    }
    if ($domains.Count -ne 2 -or @($domains | Where-Object { -not $_.certificateId }).Count) {
        throw "Both existing domain/certificate bindings must be present before cutover."
    }
    if (Test-Path -LiteralPath $snapshotPath) {
        throw "A previous domain snapshot exists. Inspect it before another cutover; do not overwrite rollback evidence."
    }
    $domains | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $snapshotPath -Encoding utf8
    try {
        foreach ($domain in $domains) {
            Invoke-Az containerapp hostname delete -g $ResourceGroup -n $AppName --hostname $domain.name --yes -o none
        }
        $properties.customDomains = $domains
        @{ properties = $properties } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tempPath -Encoding utf8
        Invoke-Az rest --method put --url $routeUrl --body "@$tempPath" -o none
        foreach ($domain in $domains) { Wait-Endpoint "https://$($domain.name)" }
        $live = Invoke-Az containerapp show -g $ResourceGroup -n $AppName -o json | ConvertFrom-Json
        $liveProduction = @($live.properties.configuration.ingress.traffic | Where-Object weight -eq 100)
        if ($liveProduction.Count -ne 1 -or $liveProduction[0].revisionName -ne $production[0].revisionName -or $liveProduction[0].latestRevision) {
            throw "Production revision changed during cutover; inspect concurrent app updates."
        }
    } catch {
        $failure = $_
        Write-Warning "Cutover failed; restoring original app domain bindings without deleting certificates."
        $properties.customDomains = @()
        @{ properties = $properties } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tempPath -Encoding utf8
        Invoke-Az rest --method put --url $routeUrl --body "@$tempPath" -o none
        $live = Invoke-Az containerapp show -g $ResourceGroup -n $AppName -o json | ConvertFrom-Json
        foreach ($domain in $domains) {
            if ($domain.name -notin @($live.properties.configuration.ingress.customDomains.name)) {
                Invoke-Az containerapp hostname add -g $ResourceGroup -n $AppName --hostname $domain.name -o none
            }
            Invoke-Az containerapp hostname bind -g $ResourceGroup -n $AppName --hostname $domain.name `
                --certificate $domain.certificateId --environment $Environment -o none
        }
        throw $failure
    }
    Write-Host "Classic: https://motogp-data.com/"
    Write-Host "Paddock: https://motogp-data.com/paddock/"
    Write-Host "Rollback domain bindings: $snapshotPath"
} finally {
    if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath }
}
