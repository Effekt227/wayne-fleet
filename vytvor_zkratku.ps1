# Wayne Fleet - Vytvoreni zkratky na plose
$WshShell = New-Object -comObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$Desktop\Wayne Fleet.lnk")
$Shortcut.TargetPath = "C:\Users\Anna S\Wayne Fleet\Wayne Fleet.bat"
$Shortcut.WorkingDirectory = "C:\Users\Anna S\Wayne Fleet"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Wayne Fleet Management System"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll, 589"
$Shortcut.Save()
Write-Host "Zkratka Wayne Fleet byla vytvorena na plose!" -ForegroundColor Yellow
Start-Sleep -Seconds 2
