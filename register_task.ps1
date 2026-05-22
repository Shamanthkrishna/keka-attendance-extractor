# register_task.ps1
# Run this once as Administrator to register the background server task.
# After that, it starts automatically on every Windows login - no terminal window.

$TaskName = "KekaAttendanceServer"
$VbsPath  = "D:\Shamanth_Krishna\Other\Keka Attendance Extractor\start_server_hidden.vbs"
$WorkDir  = "D:\Shamanth_Krishna\Other\Keka Attendance Extractor"

# Remove old task if it exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Action: run wscript.exe (hidden VBS launcher)
$Action  = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$VbsPath`"" `
    -WorkingDirectory $WorkDir

# Trigger: at logon of the current user
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: allow running on battery, don't stop on idle, restart if it fails
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Principal: run as current user with standard privileges
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal `
    -Description "Starts the Keka Attendance Flask server silently on every Windows login." `
    -Force

Write-Host ""
Write-Host "Task '$TaskName' registered successfully." -ForegroundColor Green
Write-Host "The server will start hidden automatically every time you log in." -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  Start now  : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Stop server: Get-Process pythonw | Stop-Process -Force"
Write-Host "  Remove task: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
