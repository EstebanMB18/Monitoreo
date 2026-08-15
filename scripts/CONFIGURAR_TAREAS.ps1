$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot "RUN_TASK.ps1"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

Write-Host "Eliminando tareas antiguas conocidas..." -ForegroundColor Cyan
$old = @(
"Monitoreo AWS - Corte 1","Monitoreo AWS - Corte 2","Monitoreo AWS - Corte 3",
"Monitoreo AWS - 09 AM","Monitoreo AWS - 01 PM","Monitoreo AWS - 05 PM",
"Monitoreo Verticales Dia Anterior","Monitoreo Verticales 0840","Monitoreo Verticales 1640",
"Monitoreo Hercules Diario","Monitoreo Hercules 09","Monitoreo Hercules 13","Monitoreo Hercules 17",
"Monitoreo Hercules 0905","Monitoreo Hercules 1305","Monitoreo Hercules 1705"
)
foreach($n in $old){ Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
Get-ScheduledTask -TaskName "Compensar Monitoreo *" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false

$tasks = @(
 @{M="PASARELAS"; C="09"; T="08:45"}, @{M="AWS"; C="09"; T="08:52"}, @{M="HERCULES"; C="09"; T="08:57"},
 @{M="PASARELAS"; C="13"; T="12:45"}, @{M="AWS"; C="13"; T="12:52"}, @{M="HERCULES"; C="13"; T="12:57"},
 @{M="PASARELAS"; C="17"; T="16:45"}, @{M="AWS"; C="17"; T="16:52"}, @{M="HERCULES"; C="17"; T="16:57"}
)

foreach($t in $tasks){
    $name = "Compensar Monitoreo $($t.M) $($t.C)"
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Monitor $($t.M) -Modo actual -Corte $($t.C)"
    $action = New-ScheduledTaskAction -Execute $PowerShell -Argument $arg -WorkingDirectory $Root
    $trigger = New-ScheduledTaskTrigger -Daily -At $t.T
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description "Monitoreo Compensar unificado" -Force | Out-Null
    Write-Host "OK $name -> $($t.T)" -ForegroundColor Green
}

$name = "Compensar Monitoreo DIA_ANTERIOR"
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Monitor TODOS -Modo dia-anterior -Corte 09 -HoraInicio 00:00 -HoraFin 23:59 -SoloSiNoEjecutadoHoy"
$action = New-ScheduledTaskAction -Execute $PowerShell -Argument $arg -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description "Monitoreo Compensar día anterior (una vez al día al iniciar sesión)" -Force | Out-Null
Write-Host "OK $name -> al iniciar sesión (una vez al día)" -ForegroundColor Green

Write-Host "`nTareas nuevas creadas. Pasarelas inicia 15 minutos antes; AWS 8 minutos antes; Hércules 3 minutos antes del corte." -ForegroundColor Green
Get-ScheduledTask -TaskName "Compensar Monitoreo *" | Select-Object TaskName,State
