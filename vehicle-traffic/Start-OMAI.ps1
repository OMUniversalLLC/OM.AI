param(
    [switch] $Recalibrate,
    [switch] $Automatic,
    [switch] $AddFuelRoad,
    [switch] $ChangeLogin,
    [switch] $InstallShortcut,
    [ValidateRange(1,10)] [int] $Fps = 4,
    [ValidateRange(1024,65535)] [int] $Port = 8765
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($InstallShortcut) {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $desktop 'OM AI Vehicle Traffic.lnk'))
    $shortcut.TargetPath = Join-Path $PSScriptRoot 'Auto Setup OM AI.cmd'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = 'Open OM AI Vehicle Traffic'
    $shortcut.Save()
    Write-Host 'OM AI Vehicle Traffic shortcut added to your desktop.'
    return
}
$oldProject = Join-Path $env:LOCALAPPDATA 'OM-AI\Vehicle-Traffic'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = Join-Path $oldProject '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'The OM AI Python environment was not found. Follow the Python recovery steps in SETUP.md.'
}
& $python -c "import cv2, torch, torchvision; from zoneinfo import ZoneInfo; ZoneInfo('America/New_York')"
if ($LASTEXITCODE -ne 0) {
    throw 'The Python dependency check failed. See SETUP.md.'
}

$calibration = Join-Path $PSScriptRoot 'calibration.json'
$data = Join-Path $PSScriptRoot 'private\vehicle-counts.json'
$siteFile = Join-Path $PSScriptRoot 'site.json'
if (-not (Test-Path -LiteralPath $siteFile -PathType Leaf)) {
    throw 'Copy site.example.json to site.json and set the recorder hostname. See SETUP.md.'
}
$site = Get-Content -LiteralPath $siteFile -Raw | ConvertFrom-Json
$nvrHost = [string] $site.nvr_host
if ([Uri]::CheckHostName($nvrHost) -notin 'Dns', 'IPv4') {
    throw 'Set nvr_host to the recorder IPv4 address or DNS hostname in site.json.'
}
$settings = Join-Path $env:LOCALAPPDATA 'OM-AI\Vehicle-Traffic-Private'
$loginFile = Join-Path $settings 'recorder-login.clixml'
$sheetsFile = Join-Path $settings 'sheets-key.clixml'
Write-Host "OM AI Vehicle Traffic uses three outdoor NVR channels on $nvrHost."
$saveLogin = $ChangeLogin -or -not (Test-Path -LiteralPath $loginFile -PathType Leaf)
if (-not $saveLogin) {
    try {
        $credential = Import-Clixml -LiteralPath $loginFile
        if ($credential -isnot [pscredential]) { throw 'Invalid saved recorder login.' }
    } catch {
        Write-Warning 'The saved login could not be loaded. Enter your recorder login again.'
        $saveLogin = $true
    }
}
if ($saveLogin) {
    $credential = Get-Credential -Message 'Enter the recorder viewer login. It will be remembered for this Windows account.'
}
if ($null -eq $credential) { return }

$channels = [ordered]@{
    OM_VEHICLE_ROAD_RTSP = 1
    OM_VEHICLE_DRIVEWAY_RTSP = 1
    OM_VEHICLE_FUEL_RTSP = 6
    OM_VEHICLE_DOOR_RTSP = 3
}
$previous = @{}
try {
    $viewer = [Uri]::EscapeDataString($credential.UserName)
    $viewerPassword = [Uri]::EscapeDataString($credential.GetNetworkCredential().Password)
    foreach ($key in $channels.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        $address = 'rtsp://{0}:{1}@{2}:554/chID={3}&streamType=sub' -f $viewer,$viewerPassword,$nvrHost,$channels[$key]
        [Environment]::SetEnvironmentVariable($key, $address, 'Process')
    }
    $viewerPassword = $null
    $address = $null
    if ($Automatic -or $saveLogin -or $Recalibrate -or -not (Test-Path -LiteralPath $calibration -PathType Leaf)) {
        $geometryArgs = @()
        $hasCalibration = Test-Path -LiteralPath $calibration -PathType Leaf
        $hasPreset = Test-Path -LiteralPath (Join-Path $PSScriptRoot 'calibration-preset.json') -PathType Leaf
        if (($Automatic -and ($hasCalibration -or $hasPreset)) -or ($saveLogin -and -not $Recalibrate -and $hasCalibration)) {
            $geometryArgs += '--automatic'
            if ($Recalibrate) { $geometryArgs += '--replace' }
            if ($AddFuelRoad) { $geometryArgs += '--add-fuel-road' }
        }
        & $python (Join-Path $PSScriptRoot 'calibration.py') $calibration @geometryArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'Calibration did not finish. Start again when the feeds are available.'
        }
    }
    if ($saveLogin) {
        New-Item -ItemType Directory -Path $settings -Force | Out-Null
        $credential | Export-Clixml -LiteralPath $loginFile
        Write-Host 'Recorder login validated and saved for this Windows account.'
    }
    $credential = $null
    if ($site.spreadsheet_id -and (Test-Path -LiteralPath $sheetsFile -PathType Leaf)) {
        foreach ($key in 'OM_TRAFFIC_SHEETS_KEY', 'OM_TRAFFIC_SPREADSHEET_ID') {
            $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        }
        try {
            $sheetsKey = Import-Clixml -LiteralPath $sheetsFile
            $env:OM_TRAFFIC_SHEETS_KEY = [pscredential]::new('sheets', $sheetsKey).GetNetworkCredential().Password
            $env:OM_TRAFFIC_SPREADSHEET_ID = [string] $site.spreadsheet_id
        } catch {
            Write-Warning 'Google Sheets key could not be loaded. Run Configure Google Sheets.cmd.'
        }
    }
    & $python (Join-Path $PSScriptRoot 'vehicle_monitor.py') $calibration --port $Port --fps $Fps --data $data --open-browser
    if ($LASTEXITCODE -ne 0) {
        throw 'The traffic monitor stopped with an error. See the message above.'
    }
} finally {
    foreach ($key in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
    }
}
