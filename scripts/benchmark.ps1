param(
    [int[]]$Users = @(10, 50, 100),
    [int]$Duration = 60,
    [int]$Ramp = 10,
    [string]$JMeter = "$PSScriptRoot\..\tools\apache-jmeter-5.6.3\bin\jmeter.bat"
)
$ErrorActionPreference = 'Stop'
if ($Duration -le $Ramp -or $Ramp -lt 0) { throw 'Duration debe ser mayor que Ramp y Ramp no negativo.' }
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if (!(Test-Path -LiteralPath $JMeter)) { throw "No se encuentra JMeter: $JMeter" }
Invoke-RestMethod http://localhost:5001/health | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($count in $Users) {
    if ($count -lt 1) { throw 'Users debe ser positivo.' }
    $dir = Join-Path $root "results/$stamp-$count-users"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    @{users=$count; duration_seconds=$Duration; ramp_seconds=$Ramp; started_utc=(Get-Date).ToUniversalTime().ToString('o'); payload='examples/order.json'; pool_connections=20} | ConvertTo-Json | Set-Content "$dir/config.json"
    docker compose ps | Out-File "$dir/containers.txt"
    $ids = @(docker compose ps -q)
    $monitor = Start-Job -ArgumentList $dir,($ids -join ',') -ScriptBlock {
        param($folder, $containerIDs)
        while ($true) {
            $now = (Get-Date).ToUniversalTime().ToString('o')
            docker stats --no-stream --format '{{json .}}' @($containerIDs.Split(',')) | ForEach-Object {
                $sample = $_ | ConvertFrom-Json
                $sample | Add-Member -NotePropertyName Timestamp -NotePropertyValue $now
                $sample | ConvertTo-Json -Compress | Add-Content "$folder/docker-stats.jsonl"
            }
            Start-Sleep -Seconds 2
        }
    }
    try {
        & $JMeter -n -t jmeter/orders.jmx "-Jusers=$count" "-Jduration=$Duration" "-Jramp=$Ramp" -l "$dir/samples.jtl" -j "$dir/jmeter.log" -e -o "$dir/dashboard"
        if ($LASTEXITCODE -ne 0) { throw "JMeter falló; revisar $dir/jmeter.log" }
    } finally { Stop-Job $monitor; Remove-Job $monitor }
    python scripts/summarize.py "$dir/samples.jtl" --users $count
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el resumen.' }
}
