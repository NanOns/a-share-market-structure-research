$ErrorActionPreference = 'Stop'
$workspace = 'E:\codex work\大A交易'
$report = Join-Path $workspace 'reports\project_cleanup_20261005_r1'
function Save-Json($name, $value) {
 $destination = Join-Path $report $name
 $temporary = "$destination.tmp"
 $utf8 = New-Object System.Text.UTF8Encoding($false)
 [System.IO.File]::WriteAllText($temporary, ($value | ConvertTo-Json -Depth 12), $utf8)
 Move-Item -LiteralPath $temporary -Destination $destination -Force
}
function Check-Target($path, $boundary) {
 $resolved = (Get-Item -LiteralPath $path -Force).FullName
 $allowed = [System.IO.Path]::GetFullPath($boundary).TrimEnd('\') + '\'
 if (-not $resolved.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase)) {throw "Outside cleanup boundary: $resolved"}
 if (($resolved -eq $workspace) -or ($resolved -match '^[CD]:\\new_tdx(?:\\|$)')) {throw 'Protected root'}
 if ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {throw "Root is a reparse point: $resolved"}
 return $resolved
}
$before = @{}
foreach ($driveName in @('C','E')) {$before[$driveName] = (Get-PSDrive -Name $driveName).Free}
$originalStatus = @(& git -C $workspace status --porcelain)
$deleted = New-Object System.Collections.Generic.List[object]
$skipped = New-Object System.Collections.Generic.List[object]
Save-Json 'ENTRY.json' @{contract='PROJECT_DERIVED_TEMPORARY_STORAGE_CLEANUP_R1'; entered_at=(Get-Date -Format o); free_before=$before; stage='MAINTENANCE_NOT_E3'; original_status=$originalStatus; preserve=@('TDX roots','main source/data/runtime/reports/.git','unrelated changes','managed Codex worktrees','two final E1 PostgreSQL fixture instances','other worktrees with unique receipts'); governing_document='config/project_workspace_storage_policy_v1.json'}
$cloneNames = @('dm01-r4-baseline','dm01-r4-clean','dm01-r4r1-clean','dm01-r4r2-clean')
foreach ($name in $cloneNames) {
 $target = Check-Target (Join-Path 'E:\codex_tmp' $name) 'E:\codex_tmp'
 $status = @(& git -C $target status --porcelain --untracked-files=all)
 if ($LASTEXITCODE -ne 0 -or $status.Count -gt 0) {throw "Clone not clean: $target"}
 $head = (& git -C $target rev-parse HEAD).Trim()
 & git -C $workspace merge-base --is-ancestor $head HEAD
 if ($LASTEXITCODE -ne 0) {throw "Commit not preserved: $head"}
 $config = Join-Path $target 'config\.env'
 if (Test-Path -LiteralPath $config) {if ((Get-FileHash -LiteralPath $config).Hash -ne (Get-FileHash -LiteralPath (Join-Path $workspace 'config\.env')).Hash) {throw 'Unique configuration'}}
 Remove-Item -LiteralPath $target -Recurse -Force
 $deleted.Add(@{path=$target; reason='obsolete clean regression clone; commit in main history; ignored files audited as test-only'; head=$head})
 Save-Json 'DELETED.json' $deleted
 Write-Output "Deleted clone $name"
}
$cWorktreeNames = @('r20-clean-2cdfa91367b5','r20-clean-2cedacb6139d','r20-clean-3eb148c3c19c','r20-clean-c127a02afdfd','r20-clean-c97b1d091370')
foreach ($name in $cWorktreeNames) {
 $target = Check-Target (Join-Path 'C:\Users\lps' $name) 'C:\Users\lps'
 if ([System.IO.Path]::GetFileName($target) -notmatch '^r20-clean-[0-9a-f]{12}$') {throw 'Wrong worktree name'}
 $status = @(& git -C $target status --porcelain --untracked-files=all)
 if ($LASTEXITCODE -ne 0 -or $status.Count -gt 0) {throw "Worktree not clean: $target"}
 $head = (& git -C $target rev-parse HEAD).Trim()
 & git -C $workspace merge-base --is-ancestor $head HEAD
 if ($LASTEXITCODE -ne 0) {throw "Commit not preserved: $head"}
 & git -C $workspace worktree remove $target
 if ($LASTEXITCODE -ne 0) {throw "Worktree remove failed: $target"}
 $deleted.Add(@{path=$target;reason='obsolete detached clean r20 regression worktree; ignored simulation artifacts audited';head=$head})
 Save-Json 'DELETED.json' $deleted
 Write-Output "Removed worktree $name"
}
$testRoot = 'E:\codex_tmp\test_temp'
$testFolders = @(Get-ChildItem -LiteralPath $testRoot -Directory -Force | Where-Object {$_.Name -match '^(dm01|fep|e2-|r2[6-9]-|r30|pytest-of-lps$)'})
foreach ($folder in $testFolders) {
 try {
 $target = Check-Target $folder.FullName $testRoot
 Remove-Item -LiteralPath $target -Recurse -Force
 $deleted.Add(@{path=$target;reason='completed project pytest basetemp; formal logs/XML retained in main reports'})
 } catch { $skipped.Add(@{path=$folder.FullName;reason=$_.Exception.Message}) }
}
$cTestRoot = 'C:\Users\lps\AppData\Local\Temp\pytest-of-lps'
foreach ($folder in @(Get-ChildItem -LiteralPath $cTestRoot -Directory -Force | Where-Object {$_.Name -match '^pytest-335[1-4]$'})) {
 $target = Check-Target $folder.FullName $cTestRoot
 Remove-Item -LiteralPath $target -Recurse -Force
 $deleted.Add(@{path=$target;reason='verified project N25/N26/N27 and protected-head pytest temporary fixtures'})
}
$pgNames = @('fep_e1_pg18_fresh_v1','fep_e1_pg18_fresh_v2','fep_e1_pg18_fresh_v3','fep_e1_pg18_r1','fep_e1_pg18_upgrade_v1','fep_e1_pg18_upgrade_v2','fep_e1_pg18_upgrade_v3')
$logDirectory = Join-Path $report 'retained_postgres_logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
foreach ($name in $pgNames) {
 $target = Check-Target (Join-Path 'E:\codex_tmp' $name) 'E:\codex_tmp'
 & 'E:\Postgres\bin\pg_ctl.exe' -D $target status
 if ($LASTEXITCODE -ne 3) {throw "PostgreSQL fixture may be active: $target"}
 foreach ($log in @(Get-ChildItem -LiteralPath $target -Filter '*.log' -File)) {
 $saved = Join-Path $logDirectory ($name + '_' + $log.Name)
 Copy-Item -LiteralPath $log.FullName -Destination ($saved+'.tmp')
 Move-Item -LiteralPath ($saved+'.tmp') -Destination $saved
 }
 Remove-Item -LiteralPath $target -Recurse -Force
 $deleted.Add(@{path=$target;reason='stopped superseded engineering-only PostgreSQL fixture; logs retained; final fresh/upgrade instances preserved'})
}
Save-Json 'DELETED.json' $deleted
Save-Json 'SKIPPED.json' $skipped
$after = @{}
foreach ($driveName in @('C','E')) {$after[$driveName] = (Get-PSDrive -Name $driveName).Free}
Save-Json 'COMPLETION.json' @{status='CLEANUP_COMPLETED'; completed_at=(Get-Date -Format o); free_before=$before; free_after=$after; reclaimed_bytes=@{C=$after['C']-$before['C']; E=$after['E']-$before['E']}; deleted_count=$deleted.Count; skipped=$skipped; no_next_stage_started=$true; main_tracked_changes=@(& git -C $workspace diff --name-only); remaining_worktrees=@(& git -C $workspace worktree list --porcelain)}
Write-Output ($after | ConvertTo-Json -Compress)