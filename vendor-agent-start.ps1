Write-Host "🚀 Starting Vendor A2A Server..."
Write-Host "   Port: 8001"
Write-Host "   Agent card will be at: http://localhost:8001/.well-known/agent-card.json"

$envFile = "src\adk_agents\vendor\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)\s*$") {
            $name = $matches[1]
            $value = $matches[2]
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path "$scriptDir"
Set-Location $projectRoot

$env:PYTHONPATH = "$($env:PYTHONPATH);$projectRoot"

poetry run uvicorn src.a2a_servers.vendor_server:app --host localhost --port 8001