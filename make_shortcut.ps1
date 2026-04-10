$shell = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop "ACT Enrichment Tool.lnk"
$shortcut = $shell.CreateShortcut($lnk)
$shortcut.TargetPath = "C:\Users\tschm\Claude Projects\dist\ACT Enrichment Tool\ACT Enrichment Tool.exe"
$shortcut.WorkingDirectory = "C:\Users\tschm\Claude Projects\dist\ACT Enrichment Tool"
$shortcut.Description = "ACT Attendee Enrichment Tool"
$shortcut.IconLocation = "C:\Windows\System32\shell32.dll,21"
$shortcut.Save()
Write-Output "Shortcut updated at: $lnk"
