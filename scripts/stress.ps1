param([int]$MaxUsers = 200, [int]$Duration = 60, [int]$Ramp = 10)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$previous = $null
$plateau = 0
$record = Join-Path $root 'results/stress-result.json'
for ($users = 20; $users -le $MaxUsers; $users += 20) {
    & "$PSScriptRoot/benchmark.ps1" -Users @($users) -Duration $Duration -Ramp $Ramp
    $latest = Get-ChildItem "$root/results" -Directory -Filter "*-$users-users" | Sort-Object Name -Descending | Select-Object -First 1
    $summary = Get-Content (Join-Path $latest.FullName 'summary.json') -Raw | ConvertFrom-Json
    if ($null -ne $previous -and $summary.throughput_rps -le $previous.throughput_rps * 1.05 -and $summary.p95_ms -ge $previous.p95_ms * 1.25) {
        $plateau++
    } else { $plateau = 0 }
    $previous = $summary
    if ($summary.p95_ms -ge 500 -or $summary.error_pct -ge 1) {
        @{users=$users; criterion='P95 >= 500 ms o errores >= 1%'; reached=$true; duration_seconds=$Duration; ramp_seconds=$Ramp; folder=$latest.Name} | ConvertTo-Json | Set-Content $record
        Write-Host "Criterio de estrés alcanzado con $users usuarios. Revisar $($latest.FullName)"
        return
    }
    if ($plateau -ge 2) {
        @{users=$users; criterion='Dos incrementos consecutivos: mejora throughput <=5% y crecimiento P95 >=25%'; reached=$true; duration_seconds=$Duration; ramp_seconds=$Ramp; folder=$latest.Name} | ConvertTo-Json | Set-Content $record
        Write-Host "Indicador de saturación con $users usuarios: dos incrementos seguidos con mejora de throughput <=5% y crecimiento de P95 >=25%. Revisar las muestras."
        return
    }
}
@{users=$MaxUsers; criterion='No alcanzado en el rango probado'; reached=$false; duration_seconds=$Duration; ramp_seconds=$Ramp} | ConvertTo-Json | Set-Content $record
Write-Host "Criterio no alcanzado hasta $MaxUsers usuarios. No equivale a capacidad máxima."
