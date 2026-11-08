<#
.SYNOPSIS
    權限 A/B 對照測試 — 驗證「拒絕位置／相簿權限」是否為待機無外送流量的原因。

.DESCRIPTION
    研究問題：先前觀察到 App 在待機時幾乎不發出網路請求。
    一個直覺的解釋是「因為使用者拒絕了位置與相簿權限」。
    本腳本以受控 A/B 檢驗該假設。

    A 組：位置、相片、影片、儲存空間 全部 denied
    B 組：上述全部 granted
    其餘條件完全相同。

    ⚠️ 關鍵的混淆變因控制：
    GameSir SDK 以 shared_prefs 的 gamesir_lastTime 做節流，
    若不重置，兩組都會因節流而無流量，A/B 將測不出任何差異。
    故兩組在啟動前都會把該值歸零。這是本測試成立的前提。

    其餘控制項：
    - 只 force-stop，不清除 App 資料 —— 避免 B 組多跑一次首次啟動流程
    - 免責聲明已接受（DisclaimerShowState=1），兩組 UI 起點相同
    - 兩組使用相同的 Frida 解 pinning 腳本與相同待機秒數

.PARAMETER Arm
    A = 拒絕權限；B = 授予權限

.PARAMETER IdleSeconds
    啟動後的待機觀測秒數，兩組須相同

.EXAMPLE
    .\run_permission_ab.ps1 -Arm A
    .\run_permission_ab.ps1 -Arm B
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('A','B')][string]$Arm,
    [int]$IdleSeconds = 180,
    [string]$Adb  = 'adb',
    [string]$Pkg  = 'com.ryzerobotics.tello'
)

$ErrorActionPreference = 'Stop'

# $PSScriptRoot 在以 -File 呼叫時可能為空，三段 fallback（本專案既有慣例）
$root = if ($PSScriptRoot) { $PSScriptRoot }
        elseif ($PSCommandPath) { Split-Path -Parent $PSCommandPath }
        else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$repo    = Split-Path -Parent $root
$outDir  = Join-Path $repo 'dynamic\mitm'
$fridaJs = Join-Path $repo 'dynamic\frida\unpin-targeted.js'

$tag  = "AB-perm-$Arm"
$flow = Join-Path $outDir "$tag.flow"
$log  = Join-Path $outDir "$tag.frida.log"

# 受測權限：使用者假設中提到的位置與相簿，加上連帶的儲存權限
$PERMS = @(
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.READ_MEDIA_IMAGES',
    'android.permission.READ_MEDIA_VIDEO',
    'android.permission.READ_EXTERNAL_STORAGE',
    'android.permission.WRITE_EXTERNAL_STORAGE'
)

function Say($m) { Write-Host "[$Arm] $m" }

# ---------------------------------------------------------------- 0. 前置檢查
& $Adb get-state 1>$null 2>$null
if ($LASTEXITCODE -ne 0) { throw '裝置未連線' }
$fs = & $Adb shell "su -c 'ps -A' | grep frida-server"
if (-not $fs) { throw 'frida-server 未執行，請先啟動' }

# ---------------------------------------------------------------- 1. 停止 App
Say '停止 App'
& $Adb shell "am force-stop $Pkg" | Out-Null
Start-Sleep -Seconds 2

# ---------------------------------------------------------------- 2. 設定權限
$verb = if ($Arm -eq 'B') { 'grant' } else { 'revoke' }
Say "$verb 受測權限"
foreach ($p in $PERMS) {
    # revoke 對從未授予過的權限會回非零，屬預期，不視為失敗
    & $Adb shell "pm $verb $Pkg $p" 2>&1 | Out-Null
}

# ---------------------------------------------------------------- 3. 重置節流
# 以裝置端 shell script 執行，避開 PowerShell → adb shell → su 的三層引號地獄
Say '重置 gamesir_lastTime（解除節流）'
$sh = @'
#!/system/bin/sh
F=/data/data/com.ryzerobotics.tello/shared_prefs/gamesir_config.xml
[ -f "$F" ] || { echo "MISSING"; exit 0; }
sed -i 's/name="gamesir_lastTime" value="[0-9]*"/name="gamesir_lastTime" value="0"/' "$F"
grep -o 'gamesir_lastTime" value="[0-9]*"' "$F"
'@
$tmpSh = Join-Path $env:TEMP 'reset_throttle.sh'
[System.IO.File]::WriteAllText($tmpSh, ($sh -replace "`r`n","`n"),
    (New-Object System.Text.UTF8Encoding($false)))
& $Adb push $tmpSh /data/local/tmp/reset_throttle.sh | Out-Null
Say ('  → ' + (& $Adb shell "su -c 'sh /data/local/tmp/reset_throttle.sh'"))

# ---------------------------------------------------------------- 4. 起 mitmdump
Get-Process mitmdump,python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'mitmdump' } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'mitmdump' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

if (Test-Path $flow) { Remove-Item $flow -Force }
Say "啟動 mitmdump → $(Split-Path -Leaf $flow)"
$mitm = Start-Process -PassThru -WindowStyle Hidden -FilePath 'mitmdump' `
    -ArgumentList @('--listen-port','8080',
                    '--set',"confdir=$env:USERPROFILE\.mitmproxy",
                    '-w',$flow,'--set','flow_detail=1')
Start-Sleep -Seconds 3
& $Adb reverse tcp:8080 tcp:8080 | Out-Null

# ---------------------------------------------------------------- 5. 啟動 App
Say 'Frida spawn（延遲掛載解 pinning）'
$frida = Start-Process -PassThru -WindowStyle Hidden -FilePath 'frida' `
    -ArgumentList @('-U','-f',$Pkg,'-l',$fridaJs,'-o',$log,'--runtime=v8','-q')

# ---------------------------------------------------------------- 6. 待機觀測
Say "待機觀測 $IdleSeconds 秒（不觸碰畫面）"
$deadline = (Get-Date).AddSeconds($IdleSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 15
    $left = [int]($deadline - (Get-Date)).TotalSeconds
    $alive = & $Adb shell "pidof $Pkg"
    if (-not $alive) { Say "  ⚠ App 已結束（可能崩潰），剩餘 ${left}s"; break }
    Say "  …剩餘 ${left}s，App 存活 pid=$($alive.Trim())"
}

# ---------------------------------------------------------------- 7. 收尾
Say '結束擷取'
& $Adb shell "am force-stop $Pkg" | Out-Null
foreach ($p in @($frida,$mitm)) {
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 2   # 讓 mitmdump 把緩衝寫入 flow 檔

Say "完成 → $flow"
if (Test-Path $flow) { Say ('flow 大小 = ' + (Get-Item $flow).Length + ' bytes') }
