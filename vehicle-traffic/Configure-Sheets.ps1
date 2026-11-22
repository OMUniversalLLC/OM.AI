$ErrorActionPreference = 'Stop'
$settings = Join-Path $env:LOCALAPPDATA 'OM-AI\Vehicle-Traffic-Private'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = Join-Path $env:LOCALAPPDATA 'OM-AI\Vehicle-Traffic\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'OM AI Python environment was not found.' }

$path = (Read-Host 'Path to the downloaded Google service-account JSON key').Trim().Trim('"')
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'The key file was not found.' }
$json = Get-Content -LiteralPath $path -Raw
try {
    $key = ConvertFrom-Json -InputObject $json -ErrorAction Stop
} catch {
    throw 'The key file is not valid JSON.'
}
if ($key.type -ne 'service_account' -or -not $key.client_email -or -not $key.private_key -or
    $key.token_uri -ne 'https://oauth2.googleapis.com/token') {
    throw 'Choose a Google-issued JSON service-account key.'
}
Write-Host "Share the traffic spreadsheet with $($key.client_email) as Editor."
& $python -m pip install google-auth requests
if ($LASTEXITCODE -ne 0) { throw 'Google Sheets dependencies could not be installed.' }
New-Item -ItemType Directory -Path $settings -Force | Out-Null
$secureKey = ConvertTo-SecureString -String $json -AsPlainText -Force
$secureKey | Export-Clixml -LiteralPath (Join-Path $settings 'sheets-key.clixml')
Write-Host 'Google Sheets key saved for this Windows account. Restart the monitor to enable sync.'
