<#
.SYNOPSIS
    記錄 APK 樣本的完整性與來源資訊，輸出可直接貼進 samples/MANIFEST.md 的表格列。

.DESCRIPTION
    對每支 APK 計算 MD5 / SHA-1 / SHA-256，並在工具可用時取出：
      - 簽章憑證指紋（apksigner）
      - package / versionCode / versionName / targetSdk / 權限（aapt 或 aapt2）
    簽章憑證指紋是判斷「這支 APK 是不是真的出自 Ryze」的唯一依據——
    不同版本之間憑證必須一致，不一致即為重大發現。

.PARAMETER Path
    APK 檔案或含 APK 的資料夾。預設為 ../samples。

.PARAMETER SourceUrl
    下載來源 URL，寫入輸出以保留出處。

.EXAMPLE
    .\verify_apk.ps1 -Path ..\samples\tello-1.6.8.0.apk -SourceUrl "https://www.apkmirror.com/..."

.NOTES
    apksigner / aapt 由 Android SDK build-tools 提供。若不在 PATH，用 -BuildTools 指定路徑，
    或設定環境變數 ANDROID_HOME（會自動搜尋最新的 build-tools）。
#>
[CmdletBinding()]
param(
    [string]$Path = (Join-Path $PSScriptRoot "..\samples"),
    [string]$SourceUrl = "",
    [string]$BuildTools = ""
)

$ErrorActionPreference = 'Stop'

function Find-BuildTools {
    param([string]$Explicit)

    if ($Explicit) {
        if (Test-Path $Explicit) { return $Explicit }
        Write-Warning "指定的 build-tools 路徑不存在: $Explicit"
    }

    # 已在 PATH 中
    $sig = Get-Command apksigner.bat, apksigner -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($sig) { return (Split-Path $sig.Source -Parent) }

    # 從 ANDROID_HOME / ANDROID_SDK_ROOT 找最新版
    foreach ($root in @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT, "$env:LOCALAPPDATA\Android\Sdk")) {
        if (-not $root) { continue }
        $bt = Join-Path $root "build-tools"
        if (-not (Test-Path $bt)) { continue }
        $latest = Get-ChildItem $bt -Directory | Sort-Object Name -Descending | Select-Object -First 1
        if ($latest) { return $latest.FullName }
    }
    return $null
}

$bt = Find-BuildTools -Explicit $BuildTools
if ($bt) {
    Write-Host "build-tools: $bt" -ForegroundColor DarkGray
} else {
    Write-Warning "找不到 Android build-tools，將只計算雜湊（跳過簽章與 manifest 解析）。"
    Write-Warning "安裝方式: Android Studio > SDK Manager > SDK Tools > Android SDK Build-Tools"
}

$apks = if (Test-Path $Path -PathType Container) {
    Get-ChildItem $Path -Filter *.apk -File
} else {
    Get-Item $Path
}

if (-not $apks) { Write-Warning "在 $Path 找不到任何 .apk"; return }

$rows = @()

foreach ($apk in $apks) {
    Write-Host "`n=== $($apk.Name) ===" -ForegroundColor Cyan
    Write-Host ("大小 : {0:N0} bytes" -f $apk.Length)

    $md5    = (Get-FileHash $apk.FullName -Algorithm MD5).Hash.ToLower()
    $sha1   = (Get-FileHash $apk.FullName -Algorithm SHA1).Hash.ToLower()
    $sha256 = (Get-FileHash $apk.FullName -Algorithm SHA256).Hash.ToLower()

    Write-Host "MD5    : $md5"
    Write-Host "SHA1   : $sha1"
    Write-Host "SHA256 : $sha256" -ForegroundColor Green

    $certSha256 = "(未取得)"
    $pkgInfo    = @{}

    if ($bt) {
        # --- 簽章 ---
        $apksigner = Join-Path $bt "apksigner.bat"
        if (Test-Path $apksigner) {
            Write-Host "`n-- 簽章 --" -ForegroundColor Yellow
            $out = & $apksigner verify --print-certs --verbose $apk.FullName
            $out | Where-Object { $_ -match 'Signer|SHA-256 digest|SHA-1 digest|DN:|Verified using' } | ForEach-Object {
                Write-Host "  $_"
            }
            $certLine = $out | Where-Object { $_ -match 'certificate SHA-256 digest' } | Select-Object -First 1
            if ($certLine) { $certSha256 = ($certLine -split ':\s*')[-1].Trim() }
        }

        # --- manifest ---
        $aapt = @("aapt2.exe","aapt.exe") | ForEach-Object { Join-Path $bt $_ } | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($aapt) {
            Write-Host "`n-- Manifest --" -ForegroundColor Yellow
            $dump = if ($aapt -like "*aapt2*") { & $aapt dump badging $apk.FullName } else { & $aapt dump badging $apk.FullName }
            $dump | Where-Object { $_ -match "^(package|sdkVersion|targetSdkVersion|application-label:|native-code|uses-permission)" } | ForEach-Object {
                Write-Host "  $_"
            }
            $pkgLine = $dump | Where-Object { $_ -match "^package:" } | Select-Object -First 1
            if ($pkgLine -match "versionName='([^']+)'") { $pkgInfo.versionName = $Matches[1] }
            if ($pkgLine -match "versionCode='([^']+)'") { $pkgInfo.versionCode = $Matches[1] }

            $permCount = ($dump | Where-Object { $_ -match "^uses-permission" }).Count
            Write-Host "`n  權限總數: $permCount" -ForegroundColor Magenta
        }
    }

    $rows += [pscustomobject]@{
        File        = $apk.Name
        Version     = $pkgInfo.versionName
        VersionCode = $pkgInfo.versionCode
        Sha256      = $sha256
        CertSha256  = $certSha256
    }
}

# --- 輸出 MANIFEST.md 表格列 ---
Write-Host "`n`n貼進 samples/MANIFEST.md 的樣本紀錄表:" -ForegroundColor Cyan
$today = Get-Date -Format "yyyy-MM-dd"
foreach ($r in $rows) {
    "| $($r.File) | $($r.Version) | $SourceUrl | $today | ``$($r.Sha256)`` | ``$($r.CertSha256)`` | ⬜ | |"
}

Write-Host "`n提醒: 所有版本的『簽章憑證 SHA-256』必須一致。不一致 → 樣本來源有問題，記錄後排除。" -ForegroundColor Yellow
