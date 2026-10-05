param(
    [string]$Image = "instance-generator:local",
    [string]$ContainerName = "instance-generator",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$appUrl = "http://localhost:$Port"
$healthUrl = "$appUrl/api/health"

$existingContainerId = docker ps -aq --filter "name=^/$ContainerName$"
if ($existingContainerId) {
    docker rm -f $ContainerName | Out-Null
}
docker run -d --rm -p "${Port}:80" --name $ContainerName $Image | Out-Null

$deadline = (Get-Date).AddSeconds(30)
do {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
} while ((Get-Date) -lt $deadline)

if (-not $response -or $response.StatusCode -ne 200) {
    docker logs $ContainerName
    throw "L'application Docker n'est pas disponible sur $appUrl."
}

$env:INSTANCE_GENERATOR_URL = $appUrl
Push-Location "$PSScriptRoot\ui"
try {
    $electronCommand = Join-Path $PWD "node_modules\.bin\electron.cmd"
    if (-not (Test-Path $electronCommand)) {
        npm.cmd ci
    }

    & $electronCommand main.js
}
finally {
    Pop-Location
    docker rm -f $ContainerName 2>$null | Out-Null
}
