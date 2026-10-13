$ErrorActionPreference='Stop'
$env:TMP='G:/codex_tmp'; $env:TEMP=$env:TMP; $env:TMPDIR=$env:TMP
$evidenceRoot='G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3'
$regression=Get-Content -LiteralPath 'G:/codex work/v4-full-closeout-20261012/docs/audits/v4_full_closeout_20261012/continuation_20261013/FINAL_REGRESSION_R4/RESULT.json' -Raw | ConvertFrom-Json
if ($regression.acceptance -ne 'PASS_COMPLETE_FROZEN_LEGAL_REGRESSION' -or $regression.denominator -ne 7288 -or $regression.counts.failure -ne 0 -or $regression.counts.error -ne 0) { throw 'FINAL_REGRESSION_GATE_REQUIRED' }
$installedExe='G:/codex work/v4-production-20261012/versions/V4_PACKAGE_1.0.0_fe11c18cfdf7/DaAV4/DaAV4.exe'
if ((Get-FileHash -LiteralPath $installedExe -Algorithm SHA256).Hash -ne 'F9F3B6A3A41C8EEC05C4E9FC337B0CC4248496AD87A5075836B01FE9414C6145') { throw 'INSTALLED_FROZEN_BINARY_MISMATCH' }
$oldProcess=Get-CimInstance Win32_Process -Filter 'ProcessId=12528'
$stagingProcess=Get-CimInstance Win32_Process -Filter 'ProcessId=36936'
if ($oldProcess.CommandLine -notlike '*大A交易*run_workbench_service.py*--port 28765*' -or $stagingProcess.CommandLine -notlike '*windows_package_frozen_delivery_r4*--port*28871*') { throw 'OWNED_PROCESS_IDENTITY_REQUIRED' }
$oldContext=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/context' -NoProxy -TimeoutSec 60
$newContext=Invoke-RestMethod 'http://127.0.0.1:28871/api/v4/context' -NoProxy -TimeoutSec 60
if ($oldContext.context_token -ne '55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e' -or $newContext.context_token -ne 'd86b5a003704b52e72fefb81a23dc9d96c73df4db79d6c22f86ba08e7c6fcbfc') { throw 'EXPECTED_BUSINESS_TOKEN_REQUIRED' }
foreach ($port in @(28765,28871)) {
 $daily=Invoke-RestMethod "http://127.0.0.1:$port/api/v4/operations/daily-update/status" -NoProxy -TimeoutSec 30
 if ($null -ne $daily.active_job) { throw "ACTIVE_DAILY_BOUNDARY_NOT_REACHED_$port" }
}
$task=Get-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765' -TaskPath '\'
$oldAction=$task.Actions
$oldTaskXml=Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
[IO.File]::WriteAllText((Join-Path $evidenceRoot 'OLD_SCHEDULED_TASK_AT_CUTOVER_R4.xml'),$oldTaskXml,[Text.Encoding]::Unicode)
$newAction=New-ScheduledTaskAction -Execute $installedExe -Argument '--workspace "G:/codex work/v4-production-20261012" --port 28765 --no-browser' -WorkingDirectory 'G:/codex work/v4-production-20261012'
try {
 Set-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Action $newAction | Out-Null
 Stop-Process -Id 36936
 Stop-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
 if (Get-Process -Id 12528 -ErrorAction SilentlyContinue) { Stop-Process -Id 12528 }
 $unexpected=Get-NetTCPConnection -LocalPort 28765 -State Listen -ErrorAction SilentlyContinue
 if ($unexpected) { throw 'UNEXPECTED_PORT_OWNER_PRESERVED' }
 Start-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
 $started=$false
 for ($attempt=0;$attempt -lt 90;$attempt++) {
  try {
   $status=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/desktop/status' -NoProxy -TimeoutSec 2
   if ($status.engine_state -eq 'RUNNING' -and $status.SOURCE_SHA -eq 'fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744') { $started=$true; break }
  } catch {}
  Start-Sleep -Seconds 1
 }
 if (-not $started) { throw 'NEW_PACKAGE_NOT_RUNNING' }
 $context=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/context' -NoProxy -TimeoutSec 60
 if ($context.context_token -ne $newContext.context_token -or $context.context.trade_date -ne '2026-10-12') { throw 'POST_CUTOVER_CONTEXT_MISMATCH' }
 $settings=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/operations/daily-update/settings' -Method Put -Headers @{'X-V4-Operation'='daily-update';Origin='http://127.0.0.1:28765'} -ContentType 'application/json' -Body '{"auto_enabled":true}' -NoProxy -TimeoutSec 30
 if (-not $settings.auto_enabled) { throw 'ORIGINAL_AUTO_DAILY_PREFERENCE_NOT_PRESERVED' }
 $listeners=@(Get-NetTCPConnection -LocalPort 28765 -State Listen)
 if ($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $status.pid) { throw 'UNIQUE_EXPECTED_PRODUCTION_LISTENER_REQUIRED' }
 $result=[ordered]@{contract_id='V4_AUTHORIZED_ORIGINAL_PORT_CUTOVER_EXECUTION_R4';state='NEW_PACKAGE_RUNNING_SUBSEQUENT_BROWSER_AND_RESTART_REQUIRED';observed_at=(Get-Date).ToUniversalTime().ToString('o');old_pid=12528;staging_pid=36936;new_pid=$status.pid;port=28765;executable=$installedExe;source_commit=$regression.source_commit;status=$status;context_token=$context.context_token;T0=$context.context.trade_date;settings=$settings;old_context_token=$oldContext.context_token;production_cutover=$true}
 [IO.File]::WriteAllText((Join-Path $evidenceRoot 'ACTUAL_ORIGINAL_PORT_START_R4.json'),($result|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
 $newTaskXml=Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
 [IO.File]::WriteAllText((Join-Path $evidenceRoot 'NEW_SCHEDULED_TASK_R4.xml'),$newTaskXml,[Text.Encoding]::Unicode)
 [pscustomobject]@{State=$result.state;PID=$status.pid;T0=$result.T0;Auto=$settings.auto_enabled;Port=28765}|ConvertTo-Json
} catch {
 $failure=$_.Exception.Message
 Stop-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
 Set-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Action $oldAction | Out-Null
 Start-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
 [IO.File]::WriteAllText((Join-Path $evidenceRoot 'CUTOVER_FAILED_OLD_TASK_RESTORED_R4.json'),(@{reason=$failure;old_task_restored=$true;production_acceptance=$false}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 throw
}
