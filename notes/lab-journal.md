# 實驗日誌

> 逐筆、依時間順序記錄。**沒寫在這裡的實驗等於沒做過。**
> 每筆至少要有：時間、目的、環境、指令、原始輸出、判讀。
> 失敗與否證結果同樣要記——「測了但沒發現」是有價值的結果，不是白費。

---

## 2026-08-16 — 前置調查（桌面研究，尚無實機與樣本）

**目的**：確認研究可行性與樣本可得性。

**做了什麼**
- 查證 Google Play 上架狀態
- 盤點第三方鏡像上的版本
- 初步文獻回顧

**結果**

1. **Google Play 已下架。** `play.google.com/store/apps/details?id=com.ryzerobotics.tello`
   在 `hl=en_US` 與 `hl=zh_TW` 皆回 404 /「找不到」。
   → APK 只能自第三方鏡像取得，**簽章驗證成為研究可信度的前提**。

2. **可得版本共 6 個，橫跨 2019-02 → 2024-09**（詳見 `samples/MANIFEST.md`）。
   APKMirror 有 1.6.8.0 / 1.6.4.0 / 1.6.0.1 / 1.6.0.0；
   APKPure 另有 1.4.0.0 (2020-01) 與 1.3.0.0 (2019-02)。
   → 縱向分析可行。

3. **1.6.8.0 中繼資料**：versionCode 160800、minSdk 18、**targetSdk 30**、
   arm64-v8a + armeabi-v7a、16 個權限、72 種語系。
   → 2024 年釋出卻只到 targetSdk 30，值得追（豁免 Android 11+ 隱私強化；也可能是下架主因）。

4. **1.6.8.0 更新說明含「Updated Privacy Policy」** → 追這條，政策改了什麼。

5. **產品線狀態**：DJI 於 2023-12（亞洲）與 2024-01（美國）陸續停止教育產品線銷售，
   官方 App 亦不再維護。→ **後端是否仍運作需實測（前置關卡 P2）**。

6. **關鍵前人研究**：Synacktiv 2020 對 DJI GO 4 的分析（自我更新繞過 Play、Weibo SDK
   可安裝任意 App、MobTech SDK 蒐集個資、反分析技術），GRIMM 獨立複現。
   → 直接成為本專案的方法論母本與研究問題來源：**Tello App 是否有同樣模式？**

**判讀**

題目成立，且找到了清楚的骨架（對照 Synacktiv 的四項發現 × 6 個版本的時間軸）。
最大不確定性是後端存活狀態（P2）。即使後端已關站，題目仍成立，但敘事需改為
「停售裝置的資料流遺留風險」。

**下一步**
- [ ] 找到實體 Tello（前置關卡 P1）
- [x] 取得並驗證 APK（P3）→ 見下一筆
- [ ] 存檔 Ryze 隱私權政策當前版本

---

## 2026-08-16 — 樣本取得、簽章驗證、首輪靜態盤點

**目的**：完成前置關卡 P3（取得並驗證六個版本），並在正式反編譯前取得可比對的縱向輪廓。

### 1. 樣本取得

**環境**：Windows 11、`curl.exe` 8.x（系統內建）、PowerShell 5.1

`Invoke-WebRequest` 對 APKPure 與 APKMirror 皆回 **403**（含完整瀏覽器 UA 與
session cookie 仍失敗）→ 判定為 TLS 指紋層級的 bot 偵測，非 UA 檢查。
改用 `curl.exe` 後兩站皆通。

- APKMirror（1.6.8.0 / 1.6.4.0 / 1.6.0.1 / 1.6.0.0）：三段跳轉，
  key 每次重新產生，不可硬編碼。腳本化為 `tools/fetch_apkmirror.ps1`。
- APKPure（1.4.0.0 / 1.3.0.0）：`d.apkpure.com/b/APK/com.ryzerobotics.tello?versionCode=<code>`
  （versionCode 對應 `130000` / `140000`），最終導向 `data.winudf.com`。

六支全部下載成功，ZIP magic 檢查通過。SHA-256 見 `samples/MANIFEST.md`。
1.6.8.0 的 31,618,407 bytes 與 APKMirror 頁面標示完全吻合。

### 2. 簽章驗證（無 Android build-tools 的替代方案）

本機無 Android SDK build-tools，`apksigner` 不可用。
改以 .NET 直接解析 `META-INF/TELLO.RSA` 的 PKCS#7
（`System.Security.Cryptography.Pkcs.SignedCms`）取出憑證。

**結果：六個版本憑證完全一致。**

```
certSHA256 : 53c78b9d025b16620569dd06d17fd49246749f9fe8eb47f6472bbc819ba1f878
Subject    : CN=tello (自簽)
Serial     : 1A9B4633
有效期     : 2018-01-09 → 2043-01-03
```

**判讀**：兩支來自 APKPure 的舊版與 APKMirror 已驗證版本同一把金鑰
→ **APKPure 來源驗證通過，可採用**。
另注意憑證 DN 只有 `CN=tello`，無組織欄位——供應鏈信任的實質弱點，已記入 MANIFEST。

⚠️ 僅驗證 v1 簽章。v2/v3 Signing Block 仍需 `apksigner` 補做。

### 3. 首輪靜態盤點（`tools/apk_quicklook.ps1`）

不需 jadx／apktool，以 ZipArchive + dex 字串掃描取得輪廓。原始輸出：`static/quicklook.json`。

**主要結果**（詳見 F01、F02）：

- **百度定位 SDK**（`com.baidu.location`）與 **騰訊 Bugly**（`com.tencent.bugly`）
  存在於 1.3.0.0 – 1.6.4.0，**1.6.8.0 命中數歸零**。
  `com.ryzerobotics` 在 1.6.8.0 仍有 947 次命中 → dex 未加殼，此「0」是真實移除。
- 但 1.6.8.0 **仍保留** `liblocSDK8a.so` 與 `libRoadLineRebuildAPI.so`（百度 native 元件）
  → 疑點，須以 Ghidra + Frida 追。
- `libpatchtool.so` **存在於全部六版** → 熱修補／動態載入能力，
  與 Synacktiv 對 DJI GO 4 的「繞過商店自我更新」發現同一類問題。**列為 F03 待查。**
- 六版共同存在的端點：`mydjiflight.dji.com`、`report.ryzerobotics.com`、
  `chatsupport.ryzerobotics.com`、`enchatsupport.ryzerobotics.com`、`client.vgabc.com`

### 4. 被動 DNS + RDAP 歸屬

**所有端點 2026-08-16 皆可正常解析** → **前置關卡 P2 初步正面**（服務是否仍回應待實測）。

| 網域 | IP | RDAP | 國別 |
|---|---|---|---|
| mydjiflight.dji.com | CloudFront 54.192.248.x | Amazon.com | – |
| report.ryzerobotics.com | CloudFront 3.169.121.x | Amazon.com | – |
| chatsupport.ryzerobotics.com | 47.110.222.8 | ALISOFT（阿里雲） | **CN** |
| enchatsupport.ryzerobotics.com | 47.254.51.89 | Alibaba Cloud - US | – |
| client.vgabc.com | 120.78.95.33 | ALISOFT（阿里雲） | **CN** |

**判讀**：`client.vgabc.com` 是最大未知數——存在於全部六版（含最新版）、
命名不具語義、與 Ryze/DJI 無明顯關聯、位於中國境內阿里雲。**最高優先追查。**

⚠️ CloudFront 前置**不能**推論資料落地位置。這個邏輯陷阱已寫進 F02。

**下一步**
- [ ] 追查 `client.vgabc.com`（WHOIS / crt.sh / 被動 DNS 歷史）
- [ ] 安裝 Android SDK build-tools → 補 v2/v3 簽章驗證 + AndroidManifest 權限比對
- [ ] jadx 反編譯 1.6.4.0 與 1.6.8.0，找端點呼叫點
- [ ] Ghidra 檢視 1.6.8.0 的 `liblocSDK8a.so` 是否仍可達
- [ ] 建立 F03：`libpatchtool.so` 熱修補機制分析
- [ ] 找到實體 Tello（P1，仍未解決）

---

## <日期> — <標題>

**目的**：

**環境**：

**指令 / 操作**：

```
```

**原始輸出**：

```
```

**判讀**：

**下一步**：
