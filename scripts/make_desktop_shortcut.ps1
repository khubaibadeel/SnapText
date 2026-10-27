$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$exePath = Join-Path $projectRoot 'dist\SnapText\SnapText.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    Write-Error "EXE not found: $exePath. Run BUILD_SNAPTEXT_EXE.bat first."
    exit 1
}
$desktop = [Environment]::GetFolderPath('DesktopDirectory')
if (-not $desktop) { throw 'Windows desktop location was not found.' }
$shortcutPath = Join-Path $desktop 'SnapText.lnk'
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.IconLocation = "$exePath,0"
$shortcut.Description = 'SnapText - capture text from your screen'
$shortcut.Save()
Write-Host "Desktop shortcut created: $shortcutPath"
