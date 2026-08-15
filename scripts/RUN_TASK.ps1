param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("PASARELAS","AWS","HERCULES","TODOS")]
    [string]$Monitor,

    [ValidateSet("actual","acumulado-hoy","dia-anterior","fecha")]
    [string]$Modo = "actual",

    [ValidateSet("09","13","17")]
    [string]$Corte = "09",

    [string]$Fecha = "",
    [string]$HoraInicio = "00:00",
    [string]$HoraFin = "23:59",
    [switch]$SoloSiNoEjecutadoHoy
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) { $Python = "py" }
Set-Location $Root

function Get-OutputRoot {
    $cfgPath = Join-Path $Root "config\app.json"
    if (!(Test-Path $cfgPath)) { throw "No existe config\app.json" }
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    return [Environment]::ExpandEnvironmentVariables($cfg.output_root)
}

if ($Modo -eq "dia-anterior" -and $SoloSiNoEjecutadoHoy) {
    $general = Join-Path (Get-OutputRoot) "GENERAL"
    $stateDir = Join-Path $general "state"
    $marker = Join-Path $stateDir "day_before_last_run.txt"
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    $today = Get-Date -Format "yyyy-MM-dd"

    if (Test-Path $marker) {
        $last = (Get-Content $marker -Raw).Trim()
        if ($last -eq $today) {
            Write-Host "Día anterior ya fue ejecutado hoy ($today). Se omite." -ForegroundColor Yellow
            exit 0
        }
    }
}

$argsRun = @(
    "$Root\run.py",
    "--monitor", $Monitor.ToLower(),
    "--modo", $Modo,
    "--corte", $Corte,
    "--hora-inicio", $HoraInicio,
    "--hora-fin", $HoraFin
)

if ($Fecha -and $Modo -eq "fecha") {
    $argsRun += @("--fecha", $Fecha)
}

# Sólo Hércules/TODOS publican General.
if ($Monitor -eq "PASARELAS" -or $Monitor -eq "AWS") {
    $argsRun += "--no-finalize"
}

if ($Python -eq "py") {
    & py -3.12 @argsRun
    $rc = $LASTEXITCODE
}
else {
    & $Python @argsRun
    $rc = $LASTEXITCODE
}

# Si Hércules falló antes de publicar, hacer un segundo intento de GENERAL
# en un proceso independiente.
if ($Monitor -eq "HERCULES" -and $rc -ne 0) {
    Write-Host ""
    Write-Host "HERCULES terminó con código $rc. Intentando generar GENERAL..." -ForegroundColor Yellow

    $finalArgs = @(
        "$Root\run.py",
        "--finalize-only",
        "--corte", $Corte
    )

    if ($Python -eq "py") {
        & py -3.12 @finalArgs
    }
    else {
        & $Python @finalArgs
    }
}

if ($rc -eq 0 -and $Modo -eq "dia-anterior" -and $SoloSiNoEjecutadoHoy) {
    $general = Join-Path (Get-OutputRoot) "GENERAL"
    $stateDir = Join-Path $general "state"
    $marker = Join-Path $stateDir "day_before_last_run.txt"
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    Set-Content $marker (Get-Date -Format "yyyy-MM-dd") -Encoding UTF8
}

exit $rc
