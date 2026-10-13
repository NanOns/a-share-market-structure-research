$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765'
if ($task.Actions.Execute -notlike '*V4_PACKAGE_1.0.0_fe11c18cfdf7*') {throw 'OLD_TASK_IDENTITY_REQUIRED'}
$xml=Export-ScheduledTask -TaskName $task.TaskName
[IO.File]::WriteAllText('G:\codex work\v4-full-closeout-20261012\docs\audits\v4_daily_package_repair_20261013_r1\OLD_TASK_R1.xml',$xml,[Text.Encoding]::Unicode)
Stop-ScheduledTask -TaskName $task.TaskName
$action=New-ScheduledTaskAction -Execute 'G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.0.0_d6b09b5f0e67\DaAV4\DaAV4.exe' -Argument $task.Actions.Arguments -WorkingDirectory $task.Actions.WorkingDirectory
Set-ScheduledTask -TaskName $task.TaskName -Action $action | Out-Null
