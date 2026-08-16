<#
.SYNOPSIS
    多版本 APK 快速盤點：簽章憑證、native library、第三方 SDK 套件字串、硬編碼網域。

.DESCRIPTION
    不需要 jadx / apktool / Android SDK —— 只用 .NET 的 ZipArchive 與字串掃描，
    在正式反編譯之前先取得可比對的縱向輪廓。

    做四件事：
      1. 從 META-INF/*.RSA 取出 v1 簽章憑證（PKCS#7），比對各版本是否同一把金鑰
      2. 列出 lib/<abi>/*.so，看 native 元件的增減
      3. 在 classes*.dex 裡搜尋已知第三方 SDK 的類別路徑字串
      4. 從 dex 抽出硬編碼的 http(s) 網域

    ⚠️ 這是**靜態**證據，只能證明「程式碼裡有」，不能證明「執行時會連」。
       所有結論都要等動態流量驗證後才能寫進報告。
    ⚠️ dex 字串掃描對加殼或執行期動態載入的程式碼無效。
       本 App 內含 libpatchtool.so（熱修補），因此「掃不到」不等於「不存在」。

.EXAMPLE
    .\apk_quicklook.ps1
    .\apk_quicklook.ps1 -OutJson ..\static\quicklook.json
#>
[CmdletBinding()]
param(
    [string]$SampleDir = (Join-Path $PSScriptRoot "..\samples"),
    [string]$OutJson = ""
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Security

# 已知第三方 SDK 的類別路徑前綴。要擴充就往這裡加。
$SDK_MARKERS = @(
    'Lcom/baidu/location', 'Lcom/baidu/mapapi',
    'Lcom/tencent/bugly', 'Lcom/tencent/tinker', 'Lcom/tencent/mid',
    'Lcom/tencent/connect', 'Lcom/tencent/open',
    'Lcom/umeng', 'Lcn/jpush', 'Lcn/jiguang', 'Lcom/mob/',
    'Lcom/sina/weibo', 'Lcom/alipay', 'Lcom/amap/api',
    'Lcom/google/firebase', 'Lcom/crashlytics', 'Lcom/facebook',
    'Lcom/bytedance', 'Lcom/ss/android',
    'Lcom/xiaomi/push', 'Lcom/huawei/hms', 'Lcom/meizu/cloud', 'Lcom/heytap',
    'Lcom/qq/e', 'Lorg/android/agoo', 'Lcom/taobao', 'Lcom/netease',
    'Lcom/xj/gamesir',      # GameSir 手把 SDK（小雞科技）—— 見 F02
    'Lcom/dji/', 'Lcom/ryzerobotics'
)

$DOMAIN_RE = [regex]'https?://([A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)+)'
$DOMAIN_IGNORE = '^(www\.)?(w3\.org|schemas\.|xml\.|java\.|localhost|example\.)'

function Get-DexBlob($ZipPath) {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    $ms = New-Object System.IO.MemoryStream
    try {
        foreach ($e in ($zip.Entries | Where-Object { $_.FullName -match '^classes\d*\.dex$' })) {
            $s = $e.Open(); $s.CopyTo($ms); $s.Close()
        }
    } finally { $zip.Dispose() }
    return $ms.ToArray()
}

$report = @{}

foreach ($apk in (Get-ChildItem $SampleDir -Filter *.apk | Sort-Object Name)) {
    $ver = ($apk.Name -replace '^tello-', '' -replace '-(apkmirror|apkpure)\.apk$', '')
    Write-Host "`n=== $ver ===" -ForegroundColor Cyan
    $info = [ordered]@{ file = $apk.Name; size = $apk.Length }

    $info.sha256 = (Get-FileHash $apk.FullName -Algorithm SHA256).Hash.ToLower()

    $zip = [System.IO.Compression.ZipFile]::OpenRead($apk.FullName)
    try {
        # --- 簽章憑證 ---
        $sig = $zip.Entries | Where-Object { $_.FullName -match '^META-INF/.*\.(RSA|DSA|EC)$' } | Select-Object -First 1
        if ($sig) {
            $ms = New-Object System.IO.MemoryStream
            $s = $sig.Open(); $s.CopyTo($ms); $s.Close()
            $cms = New-Object System.Security.Cryptography.Pkcs.SignedCms
            $cms.Decode($ms.ToArray())
            $c = $cms.Certificates[0]
            $sha = New-Object System.Security.Cryptography.SHA256Managed
            $info.certSubject = $c.Subject
            $info.certSerial  = $c.SerialNumber
            $info.certSha256  = [System.BitConverter]::ToString($sha.ComputeHash($c.RawData)).Replace('-', '').ToLower()
            Write-Host "  cert   : $($info.certSubject)  $($info.certSha256.Substring(0,16))…"
        }

        # --- native libs / ABI ---
        $info.abis = @($zip.Entries | Where-Object { $_.FullName -match '^lib/([^/]+)/' } |
                       ForEach-Object { ($_.FullName -split '/')[1] } | Sort-Object -Unique)
        $info.nativeLibs = @($zip.Entries | Where-Object { $_.FullName -match '^lib/[^/]+/lib.*\.so$' } |
                             ForEach-Object { Split-Path $_.FullName -Leaf } | Sort-Object -Unique)
        Write-Host "  abis   : $($info.abis -join ',')"
        Write-Host "  .so    : $($info.nativeLibs.Count) 個"
    } finally { $zip.Dispose() }

    # --- dex 掃描 ---
    $dex = Get-DexBlob $apk.FullName
    $text = [System.Text.Encoding]::ASCII.GetString($dex)
    $info.dexBytes = $dex.Length

    $sdks = [ordered]@{}
    foreach ($m in $SDK_MARKERS) {
        $n = ([regex]::Matches($text, [regex]::Escape($m))).Count
        if ($n -gt 0) { $sdks[$m] = $n }
    }
    $info.sdkMarkers = $sdks
    Write-Host "  SDK    : $($sdks.Keys -join ', ')"

    $info.domains = @($DOMAIN_RE.Matches($text) | ForEach-Object { $_.Groups[1].Value.ToLower() } |
                      Where-Object { $_ -notmatch $DOMAIN_IGNORE -and $_ -match '\.' } | Sort-Object -Unique)
    Write-Host "  網域   : $($info.domains.Count) 個"

    $report[$ver] = $info
}

# --- 交叉比對表 ---
$vers = $report.Keys | Sort-Object

Write-Host "`n`n### 簽章一致性 ###" -ForegroundColor Yellow
# @() 強制成陣列 —— 否則單一結果時 $certs[0] 會取到字串的第一個字元
$certs = @($vers | ForEach-Object { $report[$_].certSha256 } | Sort-Object -Unique)
if ($certs.Count -eq 1) {
    Write-Host "  ✅ 全部 $($vers.Count) 個版本使用同一把簽章金鑰: $($certs[0])" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ 偵測到 $($certs.Count) 把不同金鑰 —— 需逐一追查來源！" -ForegroundColor Red
    $vers | ForEach-Object { "     $_ : $($report[$_].certSha256)" }
}

Write-Host "`n### native library x 版本 ###" -ForegroundColor Yellow
$allLibs = ($vers | ForEach-Object { $report[$_].nativeLibs }) | Sort-Object -Unique
($allLibs | ForEach-Object {
    $lib = $_; $o = [ordered]@{ lib = $lib }
    foreach ($v in $vers) { $o[$v] = $(if ($report[$v].nativeLibs -contains $lib) { 'X' } else { '.' }) }
    [pscustomobject]$o
}) | Format-Table -AutoSize | Out-String | Write-Host

Write-Host "### 第三方 SDK x 版本（dex 字串出現次數）###" -ForegroundColor Yellow
$allSdk = ($vers | ForEach-Object { $report[$_].sdkMarkers.Keys }) | Sort-Object -Unique
($allSdk | ForEach-Object {
    $m = $_; $o = [ordered]@{ marker = $m }
    foreach ($v in $vers) { $n = $report[$v].sdkMarkers[$m]; $o[$v] = $(if ($n) { $n } else { 0 }) }
    [pscustomobject]$o
}) | Format-Table -AutoSize | Out-String | Write-Host

Write-Host "### 硬編碼網域 x 版本 ###" -ForegroundColor Yellow
$allDom = ($vers | ForEach-Object { $report[$_].domains }) | Sort-Object -Unique
($allDom | ForEach-Object {
    $d = $_; $o = [ordered]@{ domain = $d }
    foreach ($v in $vers) { $o[$v] = $(if ($report[$v].domains -contains $d) { 'X' } else { '.' }) }
    [pscustomobject]$o
}) | Format-Table -AutoSize | Out-String | Write-Host

if ($OutJson) {
    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding utf8
    Write-Host "`n已寫入 $OutJson" -ForegroundColor Green
}

Write-Host "`n提醒：以上皆為靜態證據。未經動態流量驗證前，不得寫成『App 會回傳資料到 X』。" -ForegroundColor Yellow
