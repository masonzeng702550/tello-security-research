<#
.SYNOPSIS
    從 APKMirror 下載指定版本的 Tello APK。

.DESCRIPTION
    APKMirror 的下載是三段跳轉，且會擋掉 Invoke-WebRequest（TLS 指紋偵測），
    因此改用系統內建的 curl.exe：

        1. 版本頁          → 取出 /download/?key=<k1>
        2. /download/?key= → 取出 /wp-content/themes/APKMirror/download.php?id=<id>&key=<k2>
        3. download.php    → 實際 APK

    key 是每次產生的，不能硬編碼，所以每次都要重跑這三步。

    APKMirror 會驗證上傳的 APK 簽章與 Google Play 上的發行者一致，
    因此在本研究中優先於 APKPure。下載後務必跑 verify_apk.ps1。

.EXAMPLE
    .\fetch_apkmirror.ps1
    .\fetch_apkmirror.ps1 -Versions 1.6.8.0,1.6.4.0
#>
[CmdletBinding()]
param(
    [string[]]$Versions = @("1.6.8.0", "1.6.4.0", "1.6.0.1", "1.6.0.0"),
    [string]$OutDir = (Join-Path $PSScriptRoot "..\samples")
)

$ErrorActionPreference = 'Stop'
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
$BASE = "https://www.apkmirror.com"
$curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
if (-not $curl) { throw "找不到 curl.exe（Windows 10 1803+ 內建）" }

$jar = Join-Path $env:TEMP "apkmirror-$PID.cookies"
$tmp = Join-Path $env:TEMP "apkmirror-$PID.html"

function Get-Html([string]$Url, [string]$Referer) {
    # 注意：不要用 $args，那是 PowerShell 的自動變數
    $curlArgs = @("-sSL", "-c", $jar, "-b", $jar, "-A", $UA, "-o", $tmp, "--max-time", "90", $Url)
    if ($Referer) { $curlArgs = @("-H", "Referer: $Referer") + $curlArgs }
    & $curl @curlArgs | Out-Null
    if (-not (Test-Path $tmp)) { return $null }
    Get-Content $tmp -Raw
}

foreach ($v in $Versions) {
    $slug = $v.Replace(".", "-")
    $pageUrl = "$BASE/apk/shenzhen-ryze-tech-co-ltd/tello/tello-$slug-release/tello-$slug-android-apk-download/"
    Write-Host "`n=== Tello $v ===" -ForegroundColor Cyan

    # --- 1. 版本頁 → download key ---
    $html = Get-Html $pageUrl
    if (-not $html) { Write-Warning "  版本頁抓取失敗"; continue }
    $m1 = [regex]::Match($html, 'href="([^"]*/download/\?key=[a-f0-9]+)"')
    if (-not $m1.Success) { Write-Warning "  找不到 download key（頁面結構可能已改）"; continue }
    $step2 = $BASE + ($m1.Groups[1].Value -replace '^https?://[^/]+', '')
    Write-Host "  [1/3] download key OK" -ForegroundColor DarkGray

    # --- 2. download 頁 → download.php ---
    $html2 = Get-Html $step2 $pageUrl
    if (-not $html2) { Write-Warning "  下載頁抓取失敗"; continue }
    $m2 = [regex]::Match($html2, 'download\.php\?id=(\d+)&(?:amp;)?key=([a-f0-9]+)')
    if (-not $m2.Success) { Write-Warning "  找不到 download.php 連結"; continue }
    $final = "$BASE/wp-content/themes/APKMirror/download.php?id=$($m2.Groups[1].Value)&key=$($m2.Groups[2].Value)"
    Write-Host "  [2/3] file id=$($m2.Groups[1].Value)" -ForegroundColor DarkGray

    # --- 3. 實際下載 ---
    $out = Join-Path $OutDir "tello-$v-apkmirror.apk"
    $res = & $curl -sSL -c $jar -b $jar -A $UA -H "Referer: $step2" -o $out `
                   -w "%{http_code} %{size_download}" --max-time 600 $final
    $code, $size = $res -split '\s+'

    if ($code -eq "200" -and [int]$size -gt 1MB) {
        # 檢查 ZIP magic (PK\x03\x04)，確認拿到的是 APK 而不是錯誤頁
        $fs = [System.IO.File]::OpenRead($out)
        $magic = New-Object byte[] 4
        $fs.Read($magic, 0, 4) | Out-Null
        $fs.Close()
        $isZip = ($magic[0] -eq 0x50 -and $magic[1] -eq 0x4B)
        $tag = if ($isZip) { "OK" } else { "警告：非 ZIP 格式！" }
        Write-Host ("  [3/3] {0}  {1:N0} bytes  {2}" -f $tag, [int]$size, (Split-Path $out -Leaf)) `
                   -ForegroundColor $(if ($isZip) { "Green" } else { "Red" })
    } else {
        Write-Warning "  下載失敗 http=$code size=$size"
        if (Test-Path $out) { Remove-Item $out }
    }
}

Remove-Item $jar, $tmp -ErrorAction SilentlyContinue
Write-Host "`n下一步: .\verify_apk.ps1 -Path ..\samples" -ForegroundColor Yellow
