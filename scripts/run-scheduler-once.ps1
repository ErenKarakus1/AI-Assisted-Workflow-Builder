Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
    python -m app.workers.scheduler
}
finally {
    Pop-Location
}
