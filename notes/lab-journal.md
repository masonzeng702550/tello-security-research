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

## 2026-08-16 — `client.vgabc.com` 追查（含一則判斷更正）

**目的**：查明前一筆日誌中列為「最高優先未知數」的端點是誰的。

**結果：是 GameSir 手把 SDK 的後端。原本的可疑判斷過度了。**

### 追查過程

**1. RDAP** — `vgabc.com` 註冊於 2010-03-26（早於 Tello 上市 8 年）、
2024-11-01 仍有異動、NS 為騰訊 DNSPod。
→ 當時據此推論「第三方、仍在維護、全中國基礎設施」。方向對，但沒查到底。

**2. crt.sh 憑證透明度** — 319 張憑證、14 個子網域：
```
client / img / clientgsw / helpgsw / imggsw / img.gsw / ucenter.egg
xjdl.vgabc.com  xjdl2.vgabc.com  xj001dl.vgabc.com   ← 關鍵
```

**3. DEX 字串比對（決定性）** — 在 1.6.8.0 的 dex 搜 `gamesir`：
```
Lcom/xj/gamesir/sdk/ButtonEvent;
Lcom/xj/gamesir/sdk/bluetooth/*;
"driveName":"xiaoji Gamesir-G2"
```
**`xj` = 小雞（xiaoji）**，GameSir 手把的品牌方，與子網域 `xjdl`（xiaoji download）吻合。

**4. 網域主體** — `vgabc.com` 由廣州電遊網絡科技有限公司營運。

硬編碼字串為 `https://client.vgabc.com/clientapi/`。
Tello 支援實體手把操控 → 功能性整合，非資料蒐集端點。
也解釋了它為何在 1.6.8.0 的 SDK 清理中被保留：手把功能還在。

### 反省

前一筆日誌把它寫成「一個來歷不明、全中國基礎設施的第三方端點在隱私政策清理中
倖存，需要解釋」——措辭已經預設了結論。實際上只要多一步（查 dex 裡的 SDK 套件路徑）
就能得到平淡的答案。

**教訓**：T0 靜態證據加上 DNS 歸屬，很容易拼出一個看似合理但錯誤的敘事。
「可疑」的感覺不是證據。日後遇到不明端點，先找程式碼裡的呼叫方，再做歸屬推論。

### 但確實挖出一個真問題

`client.vgabc.com` 的憑證共 11 張，**最新一張 2019-10-17 簽發、2020-10-16 到期，
此後未再簽發**。對照 `vgabc.com` 整體 2025 年 78 張、2026 年 53 張——主網域極活躍，
唯獨這個子網域自 2020 年停滯。

而 App 硬編碼的是 `https://`。

→ 若此路徑仍會被呼叫，TLS 交握應該失敗。除非 **App 忽略憑證錯誤**。
   後者若成立就是可被中間人利用的路徑，比原本以為的「可疑端點」更值得查。
   已寫入 F02，待動態驗證。

### 附帶修正

`com.xj.gamesir` 是 `apk_quicklook.ps1` 的 marker 清單先前遺漏的第三方 SDK。
已補入並重跑：全六版穩定存在（159 次命中），確認為長期功能整合。

**下一步**
- [ ] Frida hook 確認 `client.vgabc.com` 執行期是否真的被呼叫
- [ ] 若有呼叫，掛自簽憑證測試 App 是否照樣接受
- [ ] 其餘端點（`mydjiflight.dji.com`、`report.ryzerobotics.com`）比照辦理，
      先找呼叫方再談歸屬

---

## 2026-08-16 — 工具鏈建置、權限比對，與加殼的發現

**前置關卡更新**：**P1 解除** — 實體 Tello 已找到，充電中。L1 測試待電池就緒。

### 1. 工具鏈

系統原有 Java 8（32-bit Client VM），對 apktool 3.x（需 Java 11+）與
cmdline-tools（需 17+）都不足。winget 的 MSI 不支援 `--scope user`，
改用免安裝 zip 全部裝在 `%USERPROFILE%\devtools\`：

```
jdk-21.0.12+8            Microsoft OpenJDK 21 LTS (x64)
android-sdk/build-tools/37.0.0
android-sdk/platform-tools   adb 1.0.41
apktool/apktool.jar      3.0.3
bin/apktool.bat          wrapper，寫死 JDK 21 路徑（不吃系統 Java 8）
```

使用者層級環境變數已設 `JAVA_HOME` / `ANDROID_HOME` / PATH。

### 2. 補完 v2/v3 簽章驗證（MANIFEST 的 TODO）

`apksigner verify --print-certs` 對六版全跑：
**全部 v1 + v2 通過、單一簽署者、無 v3**。樣本完整性完全確認。

附帶觀察：連 2024 年的 1.6.8.0 都沒有 v3 簽章（v3 自 Android 9 起可用，支援金鑰輪替）。
與 targetSdk 30 一致，反映建置設定長期未更新。

### 3. TC-L2-01 權限縱向比對

| 版本 | targetSdk | 權限數 |
|---|---|---|
| 1.3.0.0 | 26 | 21 |
| 1.4.0.0 | 28 | 21 |
| 1.6.0.0 | 29 | 21 |
| 1.6.0.1 | 29 | **16** |
| 1.6.4.0 | 30 | 16 |
| 1.6.8.0 | 30 | 16 |

**1.6.0.0 → 1.6.0.1 這個小版號更新砍掉 5 個權限**：
`READ_LOGS`、`SET_DEBUG_APP`、`WRITE_SETTINGS`、
`MOUNT_UNMOUNT_FILESYSTEMS`、`GET_TASKS`。

對一支飛無人機的 App 而言，這五個都相當越界，`READ_LOGS` 與 `SET_DEBUG_APP` 尤然。
待查是否為通過 Play 審查而做。

**關鍵**：`ACCESS_FINE_LOCATION` 與 `ACCESS_COARSE_LOCATION` **全六版都在**，
包含 1.6.8.0。Tello 無 GNSS。若定位功能真的整個移除，此權限沒有理由保留。

其他全版本存在、待查用途：`SYSTEM_ALERT_WINDOW`、`USE_CREDENTIALS`、
`com.android.launcher.permission.READ_SETTINGS`。

### 4. 追 `liblocSDK8a` — 結果推翻了先前的判斷

**smali 全文檢索**（apktool 解出 1.6.8.0）：
`locSDK|RoadLine|patchtool|baidu|BDLocation|LocationClient`
→ **可見 smali 中零命中**，僅 AndroidManifest 與簽章檔的檔案列表有。
`loadLibrary` 全列舉也未見 locSDK8a / RoadLineRebuildAPI / patchtool。

→ 假設 (b)「以 JNI 或反射從可見程式碼呼叫」**排除**。

**但 AndroidManifest 有兩處命中，內容出乎意料**：
```xml
<service android:name="com.baidu.location.f" android:process=":remote"/>
<meta-data android:name="com.baidu.lbsapi.API_KEY" android:value="NQuYO2K…"/>
```
宣告了一個在 smali 中不存在的百度服務類別，且百度 API key 仍在。

**同一行還有更重要的東西**：
```xml
android:name="s.h.e.l.l.S"  android:appComponentFactory="s.h.e.l.l.A"
```

→ 查 assets：`ijiami.ajm`（668 KB）+ `ijm_lib/*/libexec.so`
→ **愛加密（Ijiami）商用加固，存在於全部六個版本。**

**這推翻了我在 F01 寫的「dex 未加殼」。** 該結論的基礎是
「com.ryzerobotics 有 947 命中所以沒加殼」——愛加密屬選擇性保護，
部分類別可見、部分在加密 payload 裡，兩者並存。

**影響**：所有基於 dex 字串掃描的**否定**結論，效力都降級為
「在可見的 dex 中未出現」。動態驗證從加分項變成必要條件。已寫入 F03。

### 5. 憑證素材全面過期（F04）

檢視 `assets/*.cer|crt|pem` 的實際內容：

| 憑證 | 到期 | 逾期 |
|---|---|---|
| `*.aasky.net` (AlphaSSL) | 2018-06-07 | 8 年 |
| `*.dji.com` (AlphaSSL) | 2018-09-04 | 8 年 |
| `*.aasky.net` (GoDaddy) | 2020-05-24 | 6 年 |
| `*.dji.com` (GoDaddy) | 2020-08-03 | 6 年 |
| `*.ryzerobotics.com` | 2020-12-17 | 5 年 |

1.6.8.0 新增一批根 CA（Amazon×4、DigiCert、GlobalSign、Entrust、USERTrust）——
研判 pinning 由 leaf 改為根 CA，但舊 leaf 未清除。

**並發現 `aasky.net` 這個網域**：有三個憑證檔案專為它準備、全六版存在，
**但完全不在 dex 硬編碼網域清單裡**。`www.aasky.net` 目前解析至 CloudFront，服務存活。

→ 實證了 F02 的觀測邊界警告：靜態字串抽取**無法**產出完整端點清單。
   加上 F03 的加殼，更說明這件事。

### 判讀

今天最重要的不是任何單一發現，而是**方法論上的修正**：
我先前依賴 dex 字串掃描下了幾個「已移除」的結論，
在加殼存在的前提下這些都站不住。改成「可見 dex 中未出現」是誠實的表述。

同時，`aasky.net` 的出現方式（只在 pinning 憑證裡、不在字串裡）
提醒端點盤點要多管道交叉，不能只靠一種抽取方式。

**下一步**
- [ ] 追查 `aasky.net`（RDAP / crt.sh / 被動 DNS）
- [ ] 反編譯 pinning 實作（TrustManager / CertificatePinner / checkServerTrusted）
- [ ] 準備 root 實機與 Frida，跑決定性的動態測試：
      `System.loadLibrary` / `ClassLoader.loadClass` hook
- [ ] 評估愛加密的反除錯強度（App 是否在 Frida 環境下拒絕啟動）
- [ ] 電池充飽後排 L1（TC-L1-01/02/04）

---

## 2026-08-16 — Tello USB 埠有線介面測試（否定結果）

**目的**：確認 Tello 的 Micro-USB 埠是否提供任何資料介面，
以判定是否存在 Wi-Fi 之外的旁路。此問題影響 L1 的測試設計與 TC-L1-07 的可行性。

**環境**：Windows 11、Tello（充電中）、USB 直連筆電

**方法**：插入前後各做一次 `Get-PnpDevice -PresentOnly` 全裝置列舉，
比對 InstanceId 差集；同時檢查 COM 埠、`adb devices` 與 System 事件記錄。

**原始輸出**

插入前：267 個裝置、無 COM 埠、adb 無裝置。
插入後：268 個裝置。新增一項：

```
Status  Class  FriendlyName                             InstanceId
Error   USB    Unknown USB Device (Set Address Failed)  USB\VID_0000&PID_0004\5&30C3FD28&0&4
```

- COM 埠：無
- `adb devices`：無
- System 事件記錄近 3 分鐘內無 USB／Kernel-PnP 事件

**判讀**

`Set Address Failed` 表示主機在匯流排上偵測到裝置、發出 SET_ADDRESS 要求，
但對方未回應。`VID_0000&PID_0004` 是 Windows 讀不到裝置描述元時填入的預留值，
非真實 VID/PID。

→ **Tello 的對外 USB 埠只供充電，未實作 USB device 協定，無資料介面。**

值得注意：若使用純充電線（D+/D- 未接），主機通常**完全偵測不到**裝置。
本次 Windows 有偵測到並嘗試列舉，代表資料線是通的，
未回應的是**裝置端**——此點反而強化了「埠本身不通資料」的結論。

**觀測邊界**：尚未以另一條確認可傳資料的線材做對照測試。
嚴格說線材因素未 100% 排除，但依上述理由可能性低。

**對研究範圍的影響**

1. **L1 全部走 Wi-Fi**——本即應如此。威脅模型的核心正是
   「無需實體接觸即可接管」，有線測試反而繞過了要研究的攻擊面。
2. **TC-L1-07（韌體升級）只能透過 App 的 Wi-Fi 升級流程被動觀察**，無旁路可用。
3. 硬體 UART 焊點為唯一的有線可能，但需拆機焊接。
   `02-threat-model.md` 已將硬體逆向排除在範圍外，且僅有一台機器，不執行。

**下一步**
- [ ] （可選）以確認可傳資料的線材做對照測試，完全排除線材因素
- [ ] 電池充飽後執行 TC-L1-01 / 02 / 04

### 附記：抓包工具鏈（同日補齊）

原本無抓包能力。補裝：

```
Wireshark 4.6.8    winget WiresharkFoundation.Wireshark
Npcap     1.88     https://npcap.com/dist/npcap-1.88.exe
                   SHA-256 a2f4ec1e5ea353ff67efd24b2ebf081ba44532410fae8d5e146af0310aa4f56b
                   Authenticode: Valid / Nmap Software LLC / DigiCert G4 CS RSA4096
```

兩點記錄：

1. **Wireshark 的 MSI 版不含 Npcap**，需另外安裝，否則 dumpcap -D 報
   Unable to load Npcap (wpcap.dll)。
2. **Npcap 免費版不支援 /S 靜默安裝**（該旗標僅開放 OEM 授權版），
   以 /S 執行會直接回 exit code 2 且不安裝。必須互動式安裝。

安裝後 dumpcap -D 列出 13 個介面，Wi-Fi 為 #5
（\Device\NPF_{6B0BA880-9D13-4882-B879-2E56902E6F10}）。
連上 Tello AP 後即以此介面抓 8889／8890／11111。

---

## 2026-08-16 — L1 實機測試：TC-L1-01 / 02 / 04 完成（專案首個 T2 證據）

**環境**：自有 Tello（SDK 1.3 世代韌體）、Windows 11 單一無線介面、
`tools/run_l1_capture.ps1` → dumpcap 4.6.8 + `tello_probe.py`

### 執行架構的限制與解法

本機只有一張無線網卡，連上 Tello 的 AP 就會失去對外網路，
**Claude Code 本身也會斷線**。因此必須把整個流程寫成無人值守的一鍵腳本：
切網路 → 抓包 → 探測 → **自動切回原網路**（`finally` 區塊保證執行）。

實際運作良好，兩次執行都正確切回。

### 兩次執行

**第一次（17:34）失敗** — `tello_probe.py` 在第一行 `print` 就拋
`UnicodeEncodeError: 'charmap' codec`。stdout 被重導向到 pipeline 時
Windows 預設 cp1252，中文輸出直接崩潰，**一個 UDP 封包都沒送出**。
pcap 只有 31 個背景封包。

同時發現 `$PSScriptRoot` 在 param 區塊預設值中為空
（PowerShell 5.1 以 `-File` 呼叫時的已知行為）。

兩者皆已修正（reconfigure stdout + `PYTHONIOENCODING`；三段回退解析腳本目錄）。

**第二次（17:36）成功** — 取得 54 KB 封包、完整查詢序列、178 個遙測封包。

### 結果摘要（詳見 F06）

| 測試 | 結果 |
|---|---|
| TC-L1-01 | `Authentication: Open` / `Encryption: None`，且無人機**主動 DHCP 配發** `192.168.10.2` |
| TC-L1-02 | 送出 7 bytes 明文 `command` → 回 `ok`，**連線到第一個指令之間零認證封包** |
| TC-L1-04 | 未送任何指令即收到 **178 個遙測封包**（≈10 Hz、16 欄位、明文 ASCII） |

11/13 查詢取得有效資料。`sdk?` 與 `sn?` 回 `unknown command`
→ 此機為 SDK 1.3 世代韌體（該兩指令屬 SDK 2.0，主要見於 Tello EDU）。

### 一次資料汙染，以及為什麼 pcap 是權威記錄

腳本輸出的指令／回應對照**整串平移了一格**：
`sdk?` 顯示回 `ok`、`battery?` 顯示回 `unknown command: sn?`……

原因：pcap `#29` 顯示無人機在 `command` 的 `ok`（#30）**之前**
主動送了一個 DJI 二進位協定封包（`cc 68 00 51 88 1a 00 0b 00 5a 00 a4 95`），
第一次 `recvfrom` 把它當成回應，之後全部錯位。

**初次判讀時我照著腳本輸出寫，得到的是錯的對照表。**
改以 pcap 重新還原才得到正確結果。

→ 已修正 `tello_probe.py`：送出前清空緩衝區，且只接受非 `0xcc` 開頭的回應。
→ **教訓**：UDP 上不能假設一送一收。腳本輸出是輔助，**pcap 才是權威**。
   這正是 `10-tooling-spec.md` 要求證據指標的理由。

### 附帶發現：8899 上的二進位串流

無人機除了文字 SDK 協定，還主動往 **8899** 推送 26 個 `0xcc` 開頭的
DJI 二進位協定封包，第 8 位元組為遞增序號。
官方 App 使用的應是這條協定，尚未分析，列為後續方向。

### ⚠️ 證據檔含個人資訊

pcap 內含測試機自身的背景流量：本機 MAC、對外 DNS 查詢
（洩漏安裝的 VPN 軟體）、mDNS 服務探索（`_adb._tcp.local` 等）。
**已由 `.gitignore` 排除，公開前必須過濾為僅含 192.168.10.0/24 並遮蔽 MAC。**

### 另記

Tello 的 **SSID 後綴即 BSSID 後三個位元組**——SSID 直接洩漏機身 MAC。

**下一步**
- [ ] TC-L1-05 視訊：送 `streamon` 抓 11111（本次該埠 0 封包）
- [ ] TC-L1-06 指令重放
- [ ] TC-L1-03 第二控制端接管（需兩人、室內、低空）
- [ ] 產出去識別化 pcap 供報告引用

---

## 2026-08-16 — 無裝置靜態分析全批次（F01 解決、F03 大幅深化、新增 F07）

**目的**：在取得 root 實機／模擬器之前，把所有不需裝置的靜態分析做完，
盡可能縮小假設空間。

**環境**：apktool 3.0.3 解出 1.3.0.0 / 1.6.4.0 / 1.6.8.0 三版
（smali 檔案數 5895 / 6015 / 5722）

### 1. F01 解決 — 百度 SDK 為真實移除

**類別清單差異**（1.6.4.0 → 1.6.8.0）：移除 296、新增 3。
其中 290/296 屬百度（127）與騰訊（164）。

新增的 3 個名稱帶隨機三字母後綴（`BindColorili` 等）→ 愛加密的誘餌類別，
非實際變更。

**膠合程式碼也被移除**：
```
com/ryzerobotics/tello/common/utils/o$b
    .implements Lcom/baidu/location/c;
    .method public a(Lcom/baidu/location/BDLocation;)V
```

**`LocationUtil`（類別 `o`）被改寫**：1.6.4.0 是雙後端（百度 + Android 原生），
1.6.8.0 拆掉百度只留原生，行數 671 → 349。

**字串池**：`locSDK8a`、`com.baidu.location`、`BDLocation`、`LocationClient`、
`com.baidu.lbsapi.API_KEY`、`bugly` 在 1.6.4.0 皆有、1.6.8.0 皆無。

→ 假設 (a)「真實移除，殘留為建置衛生問題」**成立**。

**同時修正一個錯誤前提**：我先前問「定位移除了為何保留位置權限」，
但**定位功能沒有移除**，移除的只是百度這個後端。權限合理，不是殘留。

### 2. F03 大幅深化 — 方法主體抽取（今日最重要）

反編譯 `RYZEHttpsUtils` 時發現方法主體是空的：

```smali
.method public b()Lokhttp3/OkHttpClient;
    .locals 1
    const/4 v0, 0x0
    return-object v0
    nop
.end method
```

`nop` 填充是為了保留原方法長度。這是愛加密的 **DEX 方法抽取**。

**量化**：`com/ryzerobotics/**` 5,388 個方法中 **4,808 個（89.2%）被抽取**；
okhttp3 也有 87.6%。**全面抽取，非選擇性。**

`ijiami.ajm`：magic `indl01`，熵 **7.991**（近理論上限），667,978 bytes。
載入點 `s/h/e/l/l/S:1818-1824`（`getAssets()` → `AssetManager.open()`）。

**這切割了靜態分析的可信度**：
- ✅ 類別清單、欄位宣告、方法簽章、**dex 字串池**、manifest、assets → 可信
- ❌ 方法主體、呼叫點、控制流 → 完全不可信

**字串池完好是關鍵補償**：已驗證 `aasky-net.cer` 等憑證檔名仍在池中，
儘管不被任何可見方法引用。因抽取後的 bytecode 仍以原索引引用字串表，
故「字串不在池中 ⇒ 無方法引用它」成立——F01 對 `locSDK8a` 的結論即建立於此。

**必須撤回的一項推論**：先前「smali 零命中 → 排除 JNI／反射呼叫」無效，
呼叫點就在被抽走的主體裡。已改以字串池重新建立結論。

### 3. F04 — pinning 實作已定位但行為受阻

找到 `RYZEHttpsUtils.java`（混淆為 `com/ryzerobotics/tello/common/c/d`）
與 `RYZEStatisticsHttpsUtils.java`（`c/e`）。

方法簽章明確：
```
a([Ljava/io/InputStream;)Ljavax/net/ssl/X509TrustManager;
a([C)Ljava/security/KeyStore;
b()Lokhttp3/OkHttpClient;
```
→ App **確實自行建構 TrustManager，輸入為憑證串流**。

但方法主體全空（`a(...)` 300 行都是 nop）。**驗證行為靜態取不到，必須動態。**

附帶：憑證檔名在字串池中 → **確實有方法引用它們，不是死檔案**。
第三方 `HttpsUtils` 零呼叫，為未使用的函式庫程式碼。

### 4. 新增 F07 — L2 攻擊面（否定結果）+ 未引用資產

三版 manifest 全量比對：**exported="true" 為 0、receiver 為 0、
自訂 scheme 為 0**，唯一 provider 是 FileProvider（exported=false）。
未設 `networkSecurityConfig`（targetSdk 30 預設禁明文）。

→ **L2 沒有可利用的問題。manifest 衛生相當好。**

**但發現三個不被 dex 引用的資產**：
| 檔案 | 大小 | 熵 |
|---|---|---|
| `assets/asr/common.jet` | **9.78 MB** | 5.664（結構化，未加密） |
| `assets/af.bin` | 53 KB | 7.989（加密） |
| `assets/signed.bin` | 37 KB | 7.995（加密） |

`common.jet` magic 為 `v5pp` + 一組 MD5 樣式字串。asr = 語音辨識。
**佔 APK 體積近三分之一，但 `common.jet`／`asr/` 皆不在字串池**。
已檢索訊飛、百度語音、雲知聲、思必馳等 SDK 類別，**全部零命中**。
（`msc` 的 65 次命中經上下文檢視為二進位偶然序列，非訊飛 MSC。）

### 判讀

今天最有價值的不是任何單一發現，而是**確立了「在加殼環境下，
靜態分析什麼能信、什麼不能信」的界線**，並據此重建了 F01 的結論。

另一個值得寫進報告的對比：**對外攻擊面設計謹慎（L2 全乾淨），
但建置清理長期失修**——不存在的 service 宣告、失效的 API key、
無人載入的 `.so`、過期 5–8 年的憑證、9.7 MB 的無用資產。
問題不在安全意識，在**維護流程**，與產品線停售的背景一致。

**下一步（皆需裝置）**
- [ ] Frida hook `System.loadLibrary` / `ClassLoader.loadClass` → 覆核 F01
- [ ] mitmproxy 掛自簽憑證 → 決定 F04 的 pinning 行為
- [ ] 語系切換測試 → 決定 F05 對台灣使用者的適用性
- [ ] 評估愛加密的反除錯強度（App 是否拒絕在 root／Frida 環境啟動）

---

## 2026-08-17 — 官方來源交叉驗證，以及兩個新的分析標的

### 1. 樣本來源鏈驗證通過

自 `ryzerobotics.com` 官網取得 `TELLO_GOOGLEPLAY_release_2024-08-29_1.6.8.0_signed.apk`，
與本專案 8/16 自 APKMirror 取得的 1.6.8.0 比對：

```
官網下載    31,618,407 bytes   b55f2e62cd4dff960e855a549c978f611f82683e86134a4bc9f2092b3703a8af
APKMirror   31,618,407 bytes   b55f2e62cd4dff960e855a549c978f611f82683e86134a4bc9f2092b3703a8af
```

**位元組完全相同。** `versionCode 160800`、`targetSdk 30`、v1+v2 簽章通過、單一簽署者。

意義：F01、F03、F04、F05、F07 全部錨定於官方建置產物，不再依賴鏡像的可信度。
這解除了 MANIFEST 開頭列為研究前提的那項風險。

### 2. 修正先前的敘述：「下架」的範圍

先前寫「App 已下架，只能從第三方鏡像取得」。**這個敘述過寬。**

實際情形：**Play 商店的上架頁已 404，但廠商官網仍直接散布 APK**
（CDN 為 `dl-cdn.ryzerobotics.com`）。

→ 正確說法是「自 Google Play 下架，廠商未停止散布」。已修正 MANIFEST。

### 3. 官方檔名透露的線索：版本變體

檔名為 `TELLO_**GOOGLEPLAY**_release_...`。既然建置流程以變體命名，
**很可能存在其他變體**（如中國版）。

若中國版存在且與 Google Play 版內容不同，**對 F05 是關鍵素材**——
目前 F05 是以「同一支 APK 內建的中英文政策不同」立論；
若連二進位檔本身都分版，論述強度會完全不同。待查。

### 4. 官網下載頁發現兩個未分析的標的

- **TELLO HERO APP** — 官網並列的第二支 App，本專案從未接觸
- **`com.wistron.telloeduIN`**（Tello EDU）— **開發者為緯創資通（Wistron）**，
  與 `com.ryzerobotics.tello` 完全不同的套件與發行者。
  該 Play 頁面同樣回 404（2026-08-17 查證）
- iOS 有**獨立的中國區 App Store 上架**（`id1453963643`），
  與美國區（`id1330559633`）**App ID 不同** → iOS 確實分版發行。
  這與第 3 點的變體推測方向一致，但屬 iOS，不直接適用於 Android

### 5. 工具坑（第二次踩到）

以 PowerShell 雙引號 here-string 做文字取代時，**反引號是轉義字元**，
`` `r `` 被解讀為 CR，導致 `ryzerobotics.com` 被寫成 `yzerobotics.com` 並在行中插入裸 CR。

→ 此類取代一律改用**單引號 here-string** `@'...'@`。
已全專案掃描並確認其餘檔案無同類損壞。

**下一步**
- [ ] 查官網是否提供其他版本變體（中國版？）與舊版 APK
- [ ] 評估是否將 TELLO HERO 與 Tello EDU（Wistron）納入研究範圍

---

## 2026-08-17 — 繞過 pinning 取得 DJI 後端 payload

**目的**：F04 遺留的問題——`mydjiflight.dji.com` 有 pinning，payload 取不到。

**環境**：Pixel 6 Pro / Android 13 / Magisk root / frida-server / mitmdump 8080 + `adb reverse`

**指令 / 操作**：

```
frida -U -f com.ryzerobotics.tello -l dynamic/frida/unpin-targeted.js
```

**判讀**：

前兩次嘗試 App 皆在 `LoadedApk.makeApplicationInner` 崩潰。
原因是 `Java.perform` 與愛加密的 dex 還原撞在一起。
**改為延遲 2500 ms 掛載後成功**——殼於 1–2 秒完成還原，
App 於 4–5 秒發出首波請求，2.5 秒是這個窗口。

取得三個端點的完整內容：`getallfile`、`configpath`，
以及由 `configpath` 回應動態指派的 `terra-2-g-a.djicdn.com`。
最後這個**不存在於任何靜態來源**，只有動態分析能發現。

韌體設定檔的 `Content-Type` 是 `application/pgp-signature`，
且 manifest 中 `antirollback="0"`、`enforce="0"`。

→ 寫入 **F10**，並更新 F02。

**下一步**：
- [ ] 定位 `signature` 欄位的產生邏輯
- [ ] 連機後重跑

---

## 2026-08-17 — 權限 A/B 對照測試

**目的**：檢驗「待機無外送流量是因為拒絕了位置與相簿權限」這個假設。
若成立，先前所有無流量的觀察都只是權限設定的產物，會失去外部效度。

**環境**：同上。兩組各待機 180 秒，全程不觸碰畫面。

**指令 / 操作**：

```
.\tools\run_permission_ab.ps1 -Arm A -IdleSeconds 180
.\tools\run_permission_ab.ps1 -Arm B -IdleSeconds 180
python tools\diff_flows.py dynamic\mitm\AB-perm-A.flow dynamic\mitm\AB-perm-B.flow
```

**原始輸出**：

```
=== 請求數 ===
A拒絕: 1    B授予: 1

POST client.vgabc.com/clientapi/    A=1  B=1   =
[相同] POST client.vgabc.com/clientapi/ #1  (110 bytes)
回應大小  A=[2053]  B=[2053]
```

**判讀**：

**假設否證。** 兩組完全相同，連 payload 都逐位元組一致。
測試後以 `dumpsys` 確認 B 組六項權限確實 `granted=true`，排除 `pm grant` 未生效。

設計上最關鍵的一點是**兩組都必須先把 `gamesir_lastTime` 歸零**。
若不做，兩組都會因節流而無流量，那個零差異會被誤讀成「權限無影響」——
結論碰巧正確，但論證是無效的。

意外收穫兩項：

1. **本次兩組都沒觸發 `mydjiflight`**，與昨天的差異在於全程未觸碰畫面
   → DJI 韌體檢查**需要使用者互動，不是待機心跳**。修正 F10 可能引起的誤讀。
2. `shared_prefs/share_date.xml` 中發現 **`AreaCodeTello = TW`**
   → App 已正確判定地區為台灣，卻仍送 `language: zh_cn`。
     這排除了「偵測失敗」的解釋，F05 的性質從技術疏漏變成分類決定。

**下一步**：
- [ ] 連機後重跑同一組 A/B——飛行資料的上傳才是真正的風險點
- [ ] Frida hook `LocationManager` / `MediaStore`，區分「未讀取」與「讀取但未外送」
- [ ] 追出 `AreaCodeTello` 的寫入點
---

## 2026-08-18 — 實機飛行：控制協定、飛行日誌、時間差測試

**目的**：TC-L1-08 錄下實際操作的控制封包；TC-L3-11 測時間差上傳路徑。

**環境**：Pixel 6 Pro / Magisk root / mitmproxy + Frida / 手機端 `/system/bin/tcpdump`

**指令 / 操作**：

```
adb shell su -c "tcpdump -i wlan0 -s 0 -w /data/local/tmp/tello.pcap host 192.168.10.1"
tshark -r flight.pcap -Y "udp.port==8889" -w ctrl_only.pcap
python tools\decode_tello_proto.py dynamic\pcap\TC-L1-08_ctrl_only.pcap
.\tools\capture_session.ps1 -Tag TC-L3-11-deferred-upload
```

**判讀**：見 **F12**、**F13**。核心是搖桿指令 `0x0050` 共 11,693 筆序號全為 0，
且 Tello Wi-Fi 為 `open`。時間差上傳在未登入、5 分鐘的條件下未觀測到。

### 三個方法論教訓

**一、VPN 沒真的關掉，差點毀掉整輪資料。**
`SurfsharkWireGuard` 介面仍 Up、出口 IP 在 Phoenix，
而 Ryze 的 `GetIPRegion` 判定我們在英國，App 因此拿到英文客服端點。
**教訓：每輪地區相關測試前，必須先驗證出口 IP，不能只信 VPN app 的 UI。**
回溯發現 F10 的 CloudFront POP 是 `SFO53`（舊金山），
台灣使用者正常應打到東京或香港——那輪的 VPN 很可能也是開的，已回頭註記。

**二、需要大幅搬動裝置的操作，不該與 USB 擷取同時進行。**
IMU 校準時扯到線，`adb reverse` 一斷，手機在無人機 Wi-Fi 上等於完全沒網路，
該段流量既沒抓到、App 也連不出去。
**順序應反過來：先校準好，再插線開始抓。**

**三、PowerShell 反引號第二次咬人。**
用雙引號 `.Replace()` 寫入含反引號的 Markdown，
`` `f `` 變成 form-feed、`` `0 `` 變成 null，寫進 F12 的內文。
先前已為此立過規則卻沒遵守。
**規則重申：所有含反引號的字串一律用單引號 here-string `@'...'@`。**
已加入全專案控制字元掃描作為驗收步驟。

**下一步**：
- [ ] TC-L1-03 空曠場地實測接管（目前最高優先）
- [ ] TC-L3-09 登入後重跑 F13——那是 F13 最大的缺口
- [ ] 台灣 IP 下重做客服頁面測試（阿里雲 ARMS 那批尚未寫成 findings）
- [ ] 飛機 `ERROR CODE 29` 未解決，完整六面 IMU 校準待做
---

## 2026-08-25 — TC-L1-03 階段一：未認證連線實測成功

**目的**：把 F12 的「依協定屬性推論可注入」轉為直接證據。

**環境**：飛機在地面、未裝槳、`ERROR CODE 29` 未排除。
手機連 Tello Wi-Fi 並以 USB 接電腦（電腦留在家用 Wi-Fi 以維持我方連線）。
**官方 App 全程未執行**，並自最近任務移除。

**指令 / 操作**：

```
python tools/derive_tello_crc.py dynamic/pcap/TC-L1-08_ctrl_only.pcap
python tools/tello_inject.py --selftest dynamic/pcap/TC-L1-08_ctrl_only.pcap
# 手機端：tcpdump 為觀察者，nc 僅作發送器
nc -u 192.168.10.1 8889 < conn_req.bin
```

**判讀**：見 **F15**。送出 15 個封包，飛機 87 ms 回 `conn_ack:`，
接著推送飛行日誌與 5.4 MB 影像。第二輪加送 40 次 `VIDEO_START`
後取得 39 個關鍵畫格，解出 960x720 可視畫面。

### 四個方法論教訓

**一、`nc` 對 UDP 的接收不可靠，但這不影響結論。**
改以 `tcpdump` 當觀察者、`nc` 只當發送器，
「飛機是否回應」就不再受工具限制左右。這個切分是本次成功的關鍵。

**二、`adb shell` 會等到所有子行程結束。**
`nc` 沒有逾時，即使包在 `timeout` 內，孤兒行程仍佔著 stdout，
連續兩次把工具卡到逾時。
**正解是手機端 `nohup ... &` 讓 adb 立刻返回，改由電腦端計時。**
即使卡住，tcpdump 的資料其實都還在，事後撈得回來。

**三、Git Bash 的路徑轉換兩面都會咬。**
不設 `MSYS_NO_PATHCONV=1` 時目的地 `/data/local/tmp` 被轉成
`C:/Program Files/Git/data/...`；設了之後來源 `/tmp/x.sh` 又變成 adb 找不到的路徑。
**正解是來源用 Windows 路徑、目的地用 Unix 路徑，並設 `MSYS_NO_PATHCONV=1`。**

**四、驗證工具時，先確認測資本身是對的。**
編碼器比對真實封包時有兩個不吻合，第一反應是編碼器有問題，
實際上是我手工填的 seq 與 payload 長度抄錯。
**改成從真實封包拆出欄位再餵回編碼器**，六種命令碼全部一致。
人工轉抄的測資本身就是錯誤來源。

**下一步**：
- [ ] 階段二：空曠場地實測搖桿注入（需先排除 `ERROR CODE 29`）
- [ ] 測試 App 連線中時第二個連線是否仍被接受
- [ ] 測試設定 Wi-Fi 密碼後本攻擊是否失效

---

## 2026-08-25／26 — SDK 通道打穿、二進位通道守住

**目的**：完成 TC-L1-03 階段二（飛行中注入），並釐清兩條控制路徑的差異。

**環境**：Pixel 6 Pro / Magisk root / 手機端 tcpdump + screenrecord。
飛機 IMU 已校準、`ERROR CODE 29` 已排除。中途因機身溫度 88–91°C 自動關機一次。

### 本日結果一覽

| 測試 | 結果 |
|---|---|
| TC-L1-09 SDK `command` 注入 | ✅ **成功**，18 ms 回 `ok`，切斷擁有者影像 |
| 恢復性 | ❌ 不可恢復，**只能關飛機電源** |
| WPA2 密碼緩解 | ❌ **無效**，攻擊照舊 |
| TC-L1-11 SDK 查詢列舉 | 九項可用，`sn?` 不支援（無持久識別碼） |
| TC-L1-12 `rc` 指令識別 | ✅ 存在且被接受（對照組設計） |
| TC-L1-13 軸序校正 | ✅ 八段全中，roll/pitch/throttle/yaw 確認 |
| **TC-L1-03 階段二 二進位注入** | ❌ **失敗**，滿舵 21.5 秒零反應 |

### 五個方法論教訓

**一、封包沒有防重放欄位 ≠ 可以注入。**
F12 從「序號恆為 0」推出「任意來源可注入」，看起來很有說服力。
飛行實測直接否證。飛機在封包之上另有一層以來源位址／埠為基礎的綁定，
**該機制不在封包內容中**——靜態分析與被動側錄皆看不到。
F12 嚴重度由 High 下修為 Low。

**二、與機制認知衝突的單次陰性結果，重測前不得採信。**
WPA2 首次測試顯示攻擊失效，一度指向「密碼可防」。
因 WPA2 屬連結層、理論上不影響 UDP 應用層而重測，
第二次即完整重現攻擊。若止於 n=1，會產出方向完全相反且會誤導使用者的建議。

**三、使用者的質疑是對的：不知道怎麼控制就別急著注入。**
飛手指出「你根本不知道要怎麼控制這台飛機」，該質疑成立。
軸序當時仍是借用公開文件的猜測。
改以受控操作序列取得對照後，八個區段與指定順序完全吻合，
軸序自此成為實測值。**先取得對照，再談注入。**

**四、否定結果要能排除替代解釋才有力。**
第一輪 15% 舵量無反應，無法排除「幅度不足」。
改以滿舵、單軸、長時間、且確認飛手未操作後重測，
並以 pcap 佐證 App 的 yaw 全程為中位，
才得以排除該解釋。**否定結果的強度取決於排除了多少替代解釋。**

**五、`adb shell` 會等所有子行程，`nc` 沒逾時會卡死整個工具呼叫。**
今日兩次因此逾時。正解是手機端 `nohup ... &` 讓 adb 立刻返回，
電腦端自行計時。即使卡住，tcpdump 的資料仍在，事後撈得回。

### 記錄限制

`screenrecord` 上限 180 秒。階段二的 ax3、ax4 在錄影結束後送出，
僅有 pcap 與飛手目視紀錄。後續長時間測試需分段錄影。

**下一步**：
- [ ] **閒置無人機的完整接管**：`command` → `takeoff` → `rc` → `land`，
      全程無認證不用 App。這是 F16 是否從「阻斷＋外洩」升級為
      「完整未授權控制」的關鍵，**需空曠場地**
- [ ] 地面可測的安全項目：`emergency`／`land`／`wifi` 指令是否被識別
- [ ] 無其他客戶端時，二進位 `conn_req` 建立工作階段後能否控制

---

## 2026-08-26 上午 — P1 脫殼：確定失敗，但量化了殼的行為

**目的**：執行隔夜計畫的 P1，自記憶體取得還原後的 dex，
以解開 F03 所述的方法抽取，進而回答 F02／F04／F05／F10 的多項未決問題。

**環境**：手機 USB 連接，無人機**未連線**（全程不需要）。

### 結果：P1 失敗，且是決定性的失敗

傾印所得與 APK 內的 `classes.dex` **位元組層級完全相同**
（7,067,956 bytes、5,722 類別、49,705 方法，三者皆一致）。

→ 愛加密**不以「還原整份 dex」的方式運作**，
   而應是在 `ArtMethod` 層級改寫程式碼指標。
   **單純的記憶體 dex 傾印無法解開此殼。**

F03 所界定的靜態分析邊界**依然有效**。

### 過程中的三個技術坑

**一、Frida spawn 注入會使 App 立即死亡**，即使腳本內容僅有一個 `setTimeout`。
改為 **attach 至已啟動的行程**後 App 穩定存活。

**二、Android 的 `sh` 對大於 32 位元的十六進位算術會截斷。**
`$(( 0x7c47cde000 ))` 得 1,204,674,560，正確值為 532,318,158,848。
`dd` 因此讀取錯誤位置並產出空檔。
位移須於 PC 端以全精度計算，再以字面值配合 `iflag=skip_bytes` 傳入。

**三、DEX 跨越權限邊界。**
`[anon:dalvik-DEX data]` 由 `r--` 與 `-wx` 交錯構成，
只取可讀區段會截斷檔案。以 root 讀 `/proc/pid/mem` 可無視權限取得連續區塊。

### 意外收穫：殼的保護是選擇性的

| 範圍 | 樁比例 |
|---|---|
| `com/ryzerobotics` 合計 | **96.7%** |
| 多數第三方函式庫 | 90–99% |
| **`android/support/*`** | **5–7%** |
| 全 dex 整體 | 39.2% |

`android/support/*` 佔全 dex 近三成方法，**足以將 96.7% 稀釋至 39.2%**。

### 一個差點成立的錯誤更正

以「全 dex」為母體量得 39.2% 後，一度判定 F03 的 89% 有誤。
**該判定本身才是錯的**——母體選擇不當。

> **教訓**：對「某比例過高／過低」提出質疑前，
> 必須先確認雙方的**母體定義是否一致**。

### 另一項確認：百度原生庫仍出貨但未載入

`liblocSDK8a.so` 在 1.6.8.0 仍隨 APK 出貨（Bugly 的已移除）。
以 `/proc/pid/maps` 檢視實際載入的程式庫，
在**位置權限拒絕與授予兩種條件下皆未載入**，載入總數同為 267。
→ F01 的結論成立，敘述精確化為「Java 層已移除且執行期未載入，
   原生程式庫未一併清除」。

### 新工具：`dynamic/frida/framework-probe.js`

既然脫殼不可行，改以**只攔 Android／Java 框架 API** 的策略繞過——
殼不會、也無法保護框架。已驗證六個 hook 皆可成功掛載且 App 穩定。

**但本次未攔截到任何事件**：無人機未連線時 App 幾乎不活動，
與 F08、F11 的觀察一致。該工具須在**連機**狀態下才能發揮作用。

**下一步**：
- [ ] 連機後以 `framework-probe.js` 攔截，回答 F10 的 `signature` 產生方式
- [ ] `AreaCodeTello` 於啟動時寫入，需能在啟動期掛載（spawn 會崩潰，待解）
- [ ] 隔夜計畫的 P3（原生程式庫）、P4（Python／Scratch）、P5（DAT 解碼）尚未執行

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
