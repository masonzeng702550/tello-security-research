<#
.SYNOPSIS
    啟動一次互動式擷取工作階段（mitmdump + Frida 解 pinning + 啟動 App）。

.DESCRIPTION
    與 run_permission_ab.ps1 不同：本腳本不做固定秒數的待機觀測，
    而是啟動後即返回，讓使用者實際操作 App（連機、飛行、點選功能），
    再以 -Stop 收尾。用於需要人為互動的測試案例。

    留下的行程 id 寫入 .capture-session.json，供 -Stop 使用。

.PARAMETER Tag
    本次擷取的標籤，決定輸出檔名

.PARAMETER Stop
    結束目前的擷取工作階段

.PARAMETER NoFrida
    不掛 Frida。用於觀察 App 原生的 pinning 行為
    （此時被 pin 的端點會出現 TLS handshake 失敗，這正是要觀察的現象）

.EXAMPLE
    .\capture_session.ps1 -Tag TC-L1-07-fwcheck
    # …實際操作 App…
    .\capture_session.ps1 -Stop
#>
[CmdletBinding()]
param(
    [string]$Tag = 'session',
    [switch]$Stop,
    [switch]$NoFrida,
    [switch]$NoLaunch,
    [string]$Adb = 'adb',
    [string]$Pkg = 'com.ryzerobotics.tello'
)

$ErrorActionPreference = 'Stop'

$root = if ($PSScriptRoot) { $PSScriptRoot }
        elseif ($PSCommandPath) { Split-Path -Parent $PSCommandPath }
        else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$repo    = Split-Path -Parent $root
$outDir  = Join-Path $repo 'dynamic\mitm'
$fridaJs = Join-Path $repo 'dynamic\frida\unpin-targeted.js'
$state   = Join-Path $repo '.capture-session.json'

# ------------------------------------------------------------------ 收尾
if ($Stop) {
    if (-not (Test-Path $state)) { Write-Host '沒有進行中的擷取工作階段'; return }
    $s = Get-Content $state -Raw | ConvertFrom-Json
    Write-Host "結束擷取：$($s.tag)"
    & $Adb shell "am force-stop $Pkg" | Out-Null
    foreach ($id in @($s.fridaPid, $s.mitmPid)) {
        if ($id) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep -Seconds 2      # 讓 mitmdump 把緩衝寫入 flow 檔
    if (Test-Path $s.flow) {
        Write-Host ("  flow → {0}  ({1} bytes)" -f $s.flow, (Get-Item $s.flow).Length)
    }
    Remove-Item $state -Force
    return
}

# ------------------------------------------------------------------ 啟動
$flow = Join-Path $outDir "$Tag.flow"
$log  = Join-Path $outDir "$Tag.frida.log"

# 舊工作階段殘留的行程會佔用 8080，先清掉
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='mitmdump.exe'" |
    Where-Object { $_.CommandLine -match 'mitmdump' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

if (Test-Path $flow) { Remove-Item $flow -Force }
Write-Host "啟動 mitmdump → $(Split-Path -Leaf $flow)"
$mitm = Start-Process -PassThru -WindowStyle Hidden -FilePath 'mitmdump' `
    -ArgumentList @('--listen-port','8080',
                    '--set',"confdir=$env:USERPROFILE\.mitmproxy",
                    '-w',$flow,'--set','flow_detail=1')
Start-Sleep -Seconds 3

# adb reverse 讓手機即使連在無人機 Wi-Fi（無對外網路）也能經 USB 抵達 proxy
& $Adb reverse tcp:8080 tcp:8080 | Out-Null
& $Adb shell "settings put global http_proxy 127.0.0.1:8080" | Out-Null

$fridaPid = $null
if ($NoLaunch) {
    Write-Host '不啟動 App（-NoLaunch），請自行開啟'
} elseif ($NoFrida) {
    Write-Host '啟動 App（不掛 Frida，觀察原生 pinning 行為）'
    & $Adb shell "am force-stop $Pkg" | Out-Null
    Start-Sleep -Seconds 1
    & $Adb shell "monkey -p $Pkg -c android.intent.category.LAUNCHER 1" | Out-Null
} else {
    Write-Host 'Frida spawn（延遲掛載解 pinning）'
    & $Adb shell "am force-stop $Pkg" | Out-Null
    Start-Sleep -Seconds 1
    $f = Start-Process -PassThru -WindowStyle Hidden -FilePath 'frida' `
        -ArgumentList @('-U','-f',$Pkg,'-l',$fridaJs,'-o',$log,'--runtime=v8','-q')
    $fridaPid = $f.Id
}

@{ tag=$Tag; flow=$flow; log=$log; mitmPid=$mitm.Id; fridaPid=$fridaPid } |
    ConvertTo-Json | Set-Content -Path $state -Encoding UTF8

Write-Host ''
Write-Host '擷取進行中。現在可以操作 App。'
Write-Host '結束時執行：  .\tools\capture_session.ps1 -Stop'
