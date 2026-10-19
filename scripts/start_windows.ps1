# Start the FinAlly container. Pass -Build to force an image rebuild.
param([switch]$Build)

$Image = "finally"
$Container = "finally"
$Url = "http://localhost:8000"

Push-Location (Join-Path $PSScriptRoot "..")
try {
    if (-not (Test-Path ".env")) {
        Write-Host "No .env found, copying .env.example"
        Copy-Item ".env.example" ".env"
    }

    docker image inspect $Image *> $null
    if ($Build -or $LASTEXITCODE -ne 0) {
        docker build -t $Image .
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    docker rm -f $Container *> $null
    docker run -d --name $Container -v finally-data:/app/db -p 8000:8000 --env-file .env $Image | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

Write-Host "Waiting for FinAlly to start..."
$deadline = (Get-Date).AddSeconds(60)
while ($true) {
    try {
        Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        break
    }
    catch {
        if ((Get-Date) -gt $deadline) {
            Write-Host "FinAlly did not become healthy within 60s. Check: docker logs $Container"
            exit 1
        }
        Start-Sleep -Milliseconds 500
    }
}

Write-Host "FinAlly is running at $Url"
Start-Process $Url
