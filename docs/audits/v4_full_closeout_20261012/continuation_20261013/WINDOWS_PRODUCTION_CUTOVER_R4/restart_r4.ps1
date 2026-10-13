$ErrorActionPreference='Stop'
$env:TMP='G:/codex_tmp'; $env:TEMP=$env:TMP; $env:TMPDIR=$env:TMP
$evidenceRoot='G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3'
$recordPath=Join-Path $evidenceRoot 'ACTUAL_ORIGINAL_PORT_RESTART_R4.json'
if (Test-Path -LiteralPath $recordPath) { throw 'PRESERVE_PRIOR_RESTART' }
$before=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/desktop/status' -NoProxy -TimeoutSec 15
$beforeContext=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/context' -NoProxy -TimeoutSec 60
$daily=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/operations/daily-update/status' -NoProxy -TimeoutSec 30
if ($daily.active_job) { throw 'WAIT_ACTUAL_ACTIVE_JOB_BOUNDARY' }
if ($before.engine_state -ne 'RUNNING' -or $before.SOURCE_SHA -ne 'fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744' -or -not $before.auto_daily_enabled) { throw 'EXPECTED_FROZEN_RUNNING_PACKAGE_REQUIRED' }
$owned=Get-CimInstance Win32_Process -Filter "ProcessId=$($before.pid)"
if ($owned.CommandLine -notlike '*v4-production-20261012*V4_PACKAGE_1.0.0_fe11c18cfdf7*--port 28765*') { throw 'OWNED_PACKAGE_COMMAND_REQUIRED' }
$task=Get-ScheduledTask -TaskName 'Codex-V4-OperationalDaily-28765' -TaskPath '\'
if ([IO.Path]::GetFullPath($task.Actions.Execute) -ne [IO.Path]::GetFullPath('G:/codex work/v4-production-20261012/versions/V4_PACKAGE_1.0.0_fe11c18cfdf7/DaAV4/DaAV4.exe')) { throw 'EXPECTED_STARTUP_ENTRY_REQUIRED' }
$headPaths=@('data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','config/v4_joint_release_authority_v1.json','config/v4_current_native_joint_authority_v3.json')
$beforeHeads=@{}
foreach ($headRelative in $headPaths) { $beforeHeads[$headRelative]=(Get-FileHash -LiteralPath (Join-Path $before.WORKSPACE_ROOT $headRelative) -Algorithm SHA256).Hash }
Stop-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
if (Get-Process -Id $before.pid -ErrorAction SilentlyContinue) { Stop-Process -Id $before.pid }
Start-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
$ready=$false
for ($attempt=0;$attempt -lt 90;$attempt++) {
 try {
  $after=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/desktop/status' -NoProxy -TimeoutSec 2
  if ($after.engine_state -eq 'RUNNING' -and $after.pid -ne $before.pid -and $after.SOURCE_SHA -eq $before.SOURCE_SHA) { $ready=$true; break }
 } catch {}
 Start-Sleep -Seconds 1
}
if (-not $ready) { throw 'ACTUAL_RESTART_FAILED' }
$afterContext=Invoke-RestMethod 'http://127.0.0.1:28765/api/v4/context' -NoProxy -TimeoutSec 60
if ($afterContext.context_token -ne $beforeContext.context_token -or $afterContext.context.trade_date -ne $beforeContext.context.trade_date -or -not $after.auto_daily_enabled) { throw 'RESTART_IDENTITY_OR_SCHEDULER_MISMATCH' }
$afterHeads=@{}
foreach ($headRelative in $headPaths) {
 $afterHeads[$headRelative]=(Get-FileHash -LiteralPath (Join-Path $after.WORKSPACE_ROOT $headRelative) -Algorithm SHA256).Hash
 if ($afterHeads[$headRelative] -ne $beforeHeads[$headRelative]) { throw "RESTART_HEAD_DRIFT_$headRelative" }
}
$record=[ordered]@{contract_id='V4_ACTUAL_INSTALLED_PACKAGE_RESTART_R4';acceptance='PASS_RESTART_IDENTITY_AND_AUTO_DAILY';before=$before;after=$after;before_heads=$beforeHeads;after_heads=$afterHeads;business_token=$afterContext.context_token;T0=$afterContext.context.trade_date;actual_new_pid=$true;observed_at=(Get-Date).ToUniversalTime().ToString('o');performance_test=$false;rollback_drill=$false}
[IO.File]::WriteAllText($recordPath,($record|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{BeforePID=$before.pid;AfterPID=$after.pid;T0=$record.T0;Auto=$after.auto_daily_enabled;Acceptance=$record.acceptance}|ConvertTo-Json
