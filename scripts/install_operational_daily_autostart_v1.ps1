param([int]$Port = 28765)
$ErrorActionPreference = 'Stop'
$dailyRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dailyPython = (Get-Command python).Source
$dailyPythonWindowless = Join-Path (Split-Path $dailyPython) 'pythonw.exe'
if (Test-Path -LiteralPath $dailyPythonWindowless) { $dailyPython = $dailyPythonWindowless }
$dailyEntry = Join-Path $dailyRoot 'run_workbench_service.py'
$dailyTaskName = "Codex-V4-OperationalDaily-$Port"
$dailyArguments = '-X utf8 -B "' + $dailyEntry + '" --v4-default --host 127.0.0.1 --port ' + $Port
$dailyExisting = Get-ScheduledTask -TaskName $dailyTaskName -ErrorAction SilentlyContinue
if ($dailyExisting -and ($dailyExisting.Actions.Arguments -notlike ('*' + $dailyEntry + '*'))) {
    throw 'TASK_NAME_OWNED_BY_OTHER_ACTION'
}
$dailyUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$dailyAction = New-ScheduledTaskAction -Execute $dailyPython -Argument $dailyArguments -WorkingDirectory $dailyRoot
$dailyTrigger = New-ScheduledTaskTrigger -AtLogOn -User $dailyUser
$dailyPrincipal = New-ScheduledTaskPrincipal -UserId $dailyUser -LogonType Interactive -RunLevel Limited
$dailySettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $dailyTaskName -Action $dailyAction -Trigger $dailyTrigger -Principal $dailyPrincipal -Settings $dailySettings -Description 'Read-only V4 daily worker; default AUTO ON with persisted pause and startup catch-up; no browser dependency.' -Force | Out-Null
$dailyVerified = Get-ScheduledTask -TaskName $dailyTaskName
if ($dailyVerified.Actions.Arguments -ne $dailyArguments -or $dailyVerified.State -eq 'Disabled') { throw 'AUTOSTART_READBACK_FAILED' }
$dailyEvidence = Join-Path $dailyRoot 'docs\evidence\dynamic_daily_20261009\WINDOWS_AUTOSTART.json'
$dailyRecord = @{ contract_id = 'V4_DAILY_WINDOWS_LOGON_AUTOSTART_V1'; acceptance = 'REGISTERED_AND_READ_BACK'; task_name = $dailyTaskName; user = $dailyUser; trigger = 'CURRENT_USER_LOGON'; execute = $dailyPython; arguments = $dailyArguments; working_directory = $dailyRoot; observed_at = (Get-Date).ToUniversalTime().ToString('o'); browser_required = $false; unattended_before_user_logon = $false }
$dailyTemporary = $dailyEvidence + '.tmp'
[System.IO.File]::WriteAllText($dailyTemporary, ($dailyRecord | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $dailyTemporary -Destination $dailyEvidence -Force
$dailyRecord | ConvertTo-Json -Depth 5
