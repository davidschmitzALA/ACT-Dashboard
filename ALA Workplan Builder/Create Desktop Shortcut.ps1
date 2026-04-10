# Run this once to add a shortcut to your desktop.
# Right-click the file and choose "Run with PowerShell".

$batPath  = Join-Path $PSScriptRoot "Launch Workplan Builder.bat"
$shortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "ALA Workplan Builder.lnk"

$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($shortcut)
$lnk.TargetPath       = $batPath
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description      = "ALA Workplan Builder"
$lnk.Save()

Write-Host "Shortcut created on your desktop."
