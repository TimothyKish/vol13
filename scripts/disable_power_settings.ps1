# Disable sleep
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0

# Disable Windows Update auto-restart (Admin PowerShell)
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v NoAutoRebootWithLoggedOnUsers /t REG_DWORD /d 1 /f