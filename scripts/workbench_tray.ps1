param([switch]$OpenWorkbench)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonExe = 'E:\python\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { $pythonExe = 'python' }
$baseUrl = 'http://127.0.0.1:28765'
$configuredPostgres = $false # V4 default reads exact accepted artifacts; no legacy database dependency
$localPgConfig = Join-Path $projectRoot 'config/.env'
$confirmation = '我确认进入维护窗口'
$created = $false
$mutex = New-Object System.Threading.Mutex($true, 'Local\DaAWorkbenchTray', [ref]$created)
if (-not $created) {
    if ($OpenWorkbench) {
        try { $existing = Invoke-RestMethod -Uri ($baseUrl + '/api/operations/status') -TimeoutSec 2 } catch { $existing = $null }
        if ($null -eq $existing -or $existing.service_mode -ne 'V4_DEFAULT_WORKBENCH') {
            throw 'V4 工作台未就绪，请检查 V4 服务状态。'
        }
        Start-Process ($baseUrl + '/')
    }
    exit 0
}

function Get-ServiceStatus {
    try { return Invoke-RestMethod -Uri ($baseUrl + '/api/operations/status') -TimeoutSec 2 }
    catch { return $null }
}

function Start-WorkbenchService {
    $status = Get-ServiceStatus
    if ($null -ne $status) {
        if ($status.service_mode -ne 'V4_DEFAULT_WORKBENCH') {
            throw '当前端口由其他版本服务占用，请停止旧服务后启动 V4 工作台。'
        }
        return $status
    }
    if ($configuredPostgres -and -not $env:WORKBENCH_PG_DSN -and -not (Test-Path -LiteralPath $localPgConfig)) {
        throw '缺少 WORKBENCH_PG_DSN，无法启动 PostgreSQL 工作台；不会回退到旧 DuckDB。'
    }
    Start-Process -FilePath $pythonExe -ArgumentList @('run_workbench_service.py','--v4-default','--host','127.0.0.1','--port','28765') -WorkingDirectory $projectRoot -WindowStyle Hidden | Out-Null
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $status = Get-ServiceStatus
        if ($null -ne $status) {
            if ($status.service_mode -ne 'V4_DEFAULT_WORKBENCH') { throw '启动后的服务不是 V4 工作台。' }
            return $status
        }
    } while ((Get-Date) -lt $deadline)
    throw '服务启动超时'
}

function Get-CsrfToken {
    $page = Invoke-WebRequest -UseBasicParsing -Uri ($baseUrl + '/v4#health') -TimeoutSec 3
    $match = [regex]::Match($page.Content, "const csrf='([^']+)'")
    if (-not $match.Success) { throw '无法读取服务控制令牌' }
    return $match.Groups[1].Value
}

function Invoke-ServiceControl([string]$action) {
    $token = Get-CsrfToken
    $headers = @{'X-CSRF-Token'=$token}
    $body = @{confirmation=$confirmation} | ConvertTo-Json -Compress
    # Windows PowerShell 5.1 otherwise serializes a string request body using
    # its legacy default encoding.  The Chinese maintenance confirmation then
    # reaches the service corrupted and is correctly rejected with HTTP 400.
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    try {
        return Invoke-RestMethod -Uri ($baseUrl + '/api/operations/' + $action) -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $bodyBytes -TimeoutSec 5
    } catch {
        $detail = $null
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $errorPayload = $_.ErrorDetails.Message | ConvertFrom-Json
                $detail = $errorPayload.message
            } catch {}
        }
        if ($detail) { throw $detail }
        throw
    }
}

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Application
$notify.Text = '大A交易工作台：正在检查'
$notify.Visible = $true
$menu = New-Object System.Windows.Forms.ContextMenuStrip

$statusItem = New-Object System.Windows.Forms.ToolStripMenuItem('服务状态：检查中')
$statusItem.Enabled = $false
$openItem = New-Object System.Windows.Forms.ToolStripMenuItem('打开 V4 工作台')
$opsItem = New-Object System.Windows.Forms.ToolStripMenuItem('打开运维中心')
$startItem = New-Object System.Windows.Forms.ToolStripMenuItem('启动服务')
$restartItem = New-Object System.Windows.Forms.ToolStripMenuItem('重启服务')
$stopItem = New-Object System.Windows.Forms.ToolStripMenuItem('停止服务')
$exitItem = New-Object System.Windows.Forms.ToolStripMenuItem('退出托盘（服务继续）')
$stopExitItem = New-Object System.Windows.Forms.ToolStripMenuItem('停止服务并退出')

[void]$menu.Items.Add($statusItem)
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
[void]$menu.Items.Add($openItem); [void]$menu.Items.Add($opsItem)
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
[void]$menu.Items.Add($startItem); [void]$menu.Items.Add($restartItem); [void]$menu.Items.Add($stopItem)
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
[void]$menu.Items.Add($exitItem); [void]$menu.Items.Add($stopExitItem)
$notify.ContextMenuStrip = $menu

function Refresh-TrayStatus {
    $status = Get-ServiceStatus
    $ready = $null -ne $status -and $status.service_mode -eq 'V4_DEFAULT_WORKBENCH' -and $status.service_state -eq 'READY'
    if ($ready) {
        $statusItem.Text = '服务状态：V4 运行中（只读）'
        $notify.Text = '大A交易工作台：运行中'
    } else {
        $statusItem.Text = '服务状态：未就绪'
        $notify.Text = '大A交易工作台：未就绪'
    }
    $startItem.Enabled = -not $ready
    $restartItem.Enabled = $false # Read-only V4 HTTP service exposes no control writes
    $stopItem.Enabled = $false
    $stopExitItem.Enabled = $false
}

$openItem.Add_Click({ try { Start-WorkbenchService | Out-Null; Start-Process ($baseUrl + '/') } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'工作台') | Out-Null } })
$opsItem.Add_Click({ try { Start-WorkbenchService | Out-Null; Start-Process ($baseUrl + '/v4#health') } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'工作台') | Out-Null } })
$startItem.Add_Click({ try { Start-WorkbenchService | Out-Null; Refresh-TrayStatus } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'启动失败') | Out-Null } })
$restartItem.Add_Click({ try { Invoke-ServiceControl 'restart' | Out-Null; $notify.ShowBalloonTip(2500,'大A交易工作台','服务正在受控重启',[System.Windows.Forms.ToolTipIcon]::Info) } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'重启失败') | Out-Null } })
$stopItem.Add_Click({ try { Invoke-ServiceControl 'stop' | Out-Null; $notify.ShowBalloonTip(2000,'大A交易工作台','服务正在停止',[System.Windows.Forms.ToolTipIcon]::Info) } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'停止失败') | Out-Null } })
$exitItem.Add_Click({ $notify.Visible=$false; $notify.Dispose(); [System.Windows.Forms.Application]::Exit() })
$stopExitItem.Add_Click({ try { Invoke-ServiceControl 'stop' | Out-Null } catch {}; $notify.Visible=$false; $notify.Dispose(); [System.Windows.Forms.Application]::Exit() })
$notify.Add_DoubleClick({ try { Start-WorkbenchService | Out-Null; Start-Process ($baseUrl + '/') } catch {} })

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 3000
$timer.Add_Tick({ Refresh-TrayStatus })
$timer.Start()
try { Start-WorkbenchService | Out-Null } catch { $notify.ShowBalloonTip(4000,'工作台启动失败',$_.Exception.Message,[System.Windows.Forms.ToolTipIcon]::Error) }
Refresh-TrayStatus
if ($OpenWorkbench) {
    $status = Get-ServiceStatus
    if ($null -ne $status -and $status.service_mode -eq 'V4_DEFAULT_WORKBENCH') { Start-Process ($baseUrl + '/') }
}
[System.Windows.Forms.Application]::Run()
$timer.Dispose()
$mutex.ReleaseMutex()
$mutex.Dispose()
