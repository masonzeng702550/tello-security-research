<#
.SYNOPSIS
    TC-L1-01 / 02 / 04 一鍵執行：切換至 Tello AP、抓包、唯讀探測、自動切回原網路。

.DESCRIPTION
    本機只有一張無線網卡，連上 Tello 的 AP 就會失去對外網路。
    因此整個流程必須自成一體、無人值守，結束後自動切回原本的 Wi-Fi。

    做的事：
      1. 記錄目前連線的 SSID（結束後要切回來）
      2. 掃描並記錄 Tello AP 的認證方式          → TC-L1-01
      3. 建立開放網路設定檔並連線
      4. 等待取得 192.168.10.x
      5. 啟動 dumpcap 抓包
      6. 執行 tello_probe.py（唯讀查詢 + 被動監聽） → TC-L1-02 / TC-L1-04
      7. 停止抓包
      8. **切回原網路**（finally 區塊保證執行，即使中途出錯）

    ⚠️ 不含任何飛行指令。無人機不會起飛。
    ⚠️ 僅可對自己持有的無人機執行。見 docs/03-ethics-legal.md。

.PARAMETER TelloSsid
    Tello 的 SSID。預設自動掃描第一個 TELLO-* 網路。

.PARAMETER ListenSeconds
    被動監聽 8890 的秒數。

.EXAMPLE
    .\run_l1_capture.ps1
    .\run_l1_capture.ps1 -TelloSsid TELLO-XXXXXX -ListenSeconds 20
#>
[CmdletBinding()]
param(
    [string]$TelloSsid = "",
    [int]$ListenSeconds = 15,
    # TC-L1-06：自不同來源埠重放唯讀查詢
    [switch]$Replay,
    # TC-L1-05：送 streamon 收 N 秒視訊後 streamoff。0 = 不做。
    # 只切換影像輸出，不會轉動馬達，但會改變裝置狀態，故需明確指定。
    [int]$VideoSeconds = 0,
    [string]$OutDir = "",
    [string]$Dumpcap = "C:\Program Files\Wireshark\dumpcap.exe"
)

$ErrorActionPreference = 'Continue'

# $PSScriptRoot 在 param 區塊的預設值中為空（PowerShell 5.1 以 -File 呼叫時的已知行為），
# 因此改在主體解析腳本目錄。
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot }
             elseif ($PSCommandPath) { Split-Path -Parent $PSCommandPath }
             else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $OutDir) { $OutDir = Join-Path $ScriptDir "..\dynamic\pcap" }

$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$log   = Join-Path $OutDir "TC-L1_$stamp.log"

function Say($msg, $color = 'Gray') {
    $line = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $log -Value $line -Encoding utf8
}

function Get-CurrentSsid {
    $o = netsh wlan show interfaces 2>&1
    $m = $o | Select-String -Pattern '^\s*SSID\s*:\s*(.+)$'
    if ($m) { return $m.Matches[0].Groups[1].Value.Trim() }
    return $null
}

function Wait-ForIp($prefix, $timeoutSec) {
    $end = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $end) {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
              Where-Object { $_.IPAddress -like $prefix }
        if ($ip) { return $ip }
        Start-Sleep -Milliseconds 800
    }
    return $null
}

# ---------------------------------------------------------------- 起始狀態
$originalSsid = Get-CurrentSsid
Say "原本連線的 SSID: $originalSsid" 'Cyan'
if (-not $originalSsid) { Say "警告：無法判定目前 SSID，結束後可能無法自動切回" 'Yellow' }

$capProc = $null

try {
    # ------------------------------------------------------------ TC-L1-01
    Say "掃描無線網路…"
    $scan = (netsh wlan show networks mode=bssid 2>&1) -join "`n"
    Add-Content -Path $log -Value "`n===== netsh wlan show networks mode=bssid =====`n$scan`n" -Encoding utf8

    if (-not $TelloSsid) {
        $m = [regex]::Match($scan, 'SSID\s+\d+\s*:\s*(TELLO-\S+)')
        if ($m.Success) { $TelloSsid = $m.Groups[1].Value }
    }
    if (-not $TelloSsid) { throw "掃描不到任何 TELLO-* 網路。無人機是否已開機？" }
    Say "目標 SSID: $TelloSsid" 'Cyan'

    # 取出該 SSID 的區塊，記錄認證方式（TC-L1-01 的證據）
    $block = ($scan -split "(?=SSID \d+)") | Where-Object { $_ -match [regex]::Escape($TelloSsid) } | Select-Object -First 1
    $auth = ([regex]::Match($block, 'Authentication\s*:\s*(.+)')).Groups[1].Value.Trim()
    $enc  = ([regex]::Match($block, 'Encryption\s*:\s*(.+)')).Groups[1].Value.Trim()
    Say "TC-L1-01  Authentication=$auth  Encryption=$enc" 'Green'

    # ------------------------------------------------------------ 連線
    # 開放網路的設定檔（無金鑰）
    $profileXml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>$TelloSsid</name>
  <SSIDConfig><SSID><name>$TelloSsid</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>manual</connectionMode>
  <MSM><security>
    <authEncryption><authentication>open</authentication><encryption>none</encryption><useOneX>false</useOneX></authEncryption>
  </security></MSM>
</WLANProfile>
"@
    $pf = Join-Path $env:TEMP "$TelloSsid.xml"
    [System.IO.File]::WriteAllText($pf, $profileXml, (New-Object System.Text.UTF8Encoding($false)))
    netsh wlan add profile filename="$pf" user=current 2>&1 | Out-Null

    Say "連線至 $TelloSsid …（本機即將失去對外網路）" 'Yellow'
    netsh wlan connect name="$TelloSsid" 2>&1 | Out-Null

    $ip = Wait-ForIp '192.168.10.*' 30
    if (-not $ip) { throw "連線後 30 秒內未取得 192.168.10.x，放棄" }
    Say "已取得 IP: $($ip.IPAddress) @ $($ip.InterfaceAlias)" 'Green'

    $ifState = (netsh wlan show interfaces 2>&1) -join "`n"
    Add-Content -Path $log -Value "`n===== 連線後 netsh wlan show interfaces =====`n$ifState`n" -Encoding utf8

    # ------------------------------------------------------------ 抓包
    $pcap = Join-Path $OutDir "TC-L1-02_$stamp.pcapng"
    $ifGuid = (Get-NetAdapter -Name $ip.InterfaceAlias).InterfaceGuid
    $dev = "\Device\NPF_$ifGuid"
    if (Test-Path $Dumpcap) {
        Say "啟動 dumpcap → $(Split-Path $pcap -Leaf)"
        $capProc = Start-Process -FilePath $Dumpcap `
            -ArgumentList @('-i', $dev, '-w', "`"$pcap`"", '-q') `
            -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 3   # 讓抓包先就緒
    } else {
        Say "找不到 dumpcap，略過抓包（探測仍會執行）" 'Yellow'
    }

    # ------------------------------------------------------------ TC-L1-02 / 04
    $probe = Join-Path $ScriptDir "tello_probe.py"
    $json  = Join-Path $OutDir "TC-L1-02_$stamp.json"
    Say "執行 tello_probe.py（唯讀查詢，不含飛行指令）…" 'Cyan'
    # 雙保險：腳本內已 reconfigure stdout，這裡再從環境變數指定一次。
    # Windows 上 Python 的 stdout 被重導向時預設 cp1252，中文輸出會拋 UnicodeEncodeError。
    $env:PYTHONIOENCODING = 'utf-8'
    $probeArgs = @($probe, '--listen', $ListenSeconds, '--json', "$json", '--outdir', "$OutDir")
    if ($Replay) { $probeArgs += '--replay' }
    if ($VideoSeconds -gt 0) { $probeArgs += @('--video', $VideoSeconds) }
    $probeOut = & python @probeArgs 2>&1
    $probeOut | ForEach-Object { Add-Content -Path $log -Value "    $_" -Encoding utf8 }
    $probeOut | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" }

} catch {
    Say "錯誤: $($_.Exception.Message)" 'Red'
} finally {
    # ------------------------------------------------------------ 收尾（保證執行）
    if ($capProc -and -not $capProc.HasExited) {
        Say "停止抓包…"
        Stop-Process -Id $capProc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    $pcapFile = Get-ChildItem $OutDir -Filter "TC-L1-02_$stamp.pcapng" -ErrorAction SilentlyContinue
    if ($pcapFile) { Say ("封包檔: {0}  ({1:N0} bytes)" -f $pcapFile.Name, $pcapFile.Length) 'Green' }

    if ($originalSsid -and $originalSsid -ne $TelloSsid) {
        Say "切回原網路 $originalSsid …" 'Yellow'
        netsh wlan connect name="$originalSsid" 2>&1 | Out-Null
        $back = Wait-ForIp '*' 25
        Start-Sleep -Seconds 3
        $now = Get-CurrentSsid
        if ($now -eq $originalSsid) { Say "已切回 $now" 'Green' }
        else { Say "自動切回失敗，目前為 '$now' —— 請手動連回 $originalSsid" 'Red' }
    }
    Say "完成。紀錄檔: $log" 'Cyan'
}
