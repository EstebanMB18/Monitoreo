param(
    [Parameter(Mandatory=$true)][ValidateSet("PASARELAS","AWS","HERCULES","TODOS")] [string]$Monitor,
    [ValidateSet("actual","acumulado-hoy","dia-anterior","fecha")] [string]$Modo = "actual",
    [ValidateSet("09","13","17")] [string]$Corte = "09",
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

$args = @("$Root\run.py", "--monitor", $Monitor.ToLower(), "--modo", $Modo, "--corte", $Corte, "--hora-inicio", $HoraInicio, "--hora-fin", $HoraFin)
if ($Fecha -and $Modo -eq "fecha") { $args += @("--fecha", $Fecha) }

# PASARELAS y AWS no regeneran GENERAL. HERCULES es el Ãºltimo del corte.
if ($Monitor -eq "PASARELAS" -or $Monitor -eq "AWS") {
    $args += "--no-finalize"
}

# PASARELAS y AWS no regeneran GENERAL. HERCULES es el Ãºltimo del corte.
if ($Monitor -eq "PASARELAS" -or $Monitor -eq "AWS") {
    $args += "--no-finalize"
}

if ($Python -eq "py") {
    & py -3.12 @args
    $rc = $LASTEXITCODE
} else {
    & $Python @args
    $rc = $LASTEXITCODE
}

if ($rc -eq 0 -and $Modo -eq "dia-anterior" -and $SoloSiNoEjecutadoHoy) {
    $general = Join-Path (Get-OutputRoot) "GENERAL"
    $stateDir = Join-Path $general "state"
    $marker = Join-Path $stateDir "day_before_last_run.txt"
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    Set-Content -Path $marker -Value (Get-Date -Format "yyyy-MM-dd") -Encoding UTF8
}

exit $rc
