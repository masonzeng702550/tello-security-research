# F01 — 中國第三方 SDK（百度定位、騰訊 Bugly）存在於 2019–2022 版本，2024 版移除

| 欄位 | 內容 |
|---|---|
| 編號 | F01 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 隱私 |
| 嚴重度 | **待定** — 需動態驗證後評估 |
| 受影響版本 | 1.3.0.0 – 1.6.4.0（1.6.8.0 已移除 Java 層） |
| 狀態 | **靜態已確認 / 動態待驗證** |
| 新穎性 | 本研究新發現（未見前人對 Tello App 做過此縱向分析） |

## 摘要

Tello App 自 1.3.0.0（2019-02）至 1.6.4.0（2022-09）內含 **百度定位 SDK**
（`com.baidu.location`）與 **騰訊 Bugly**（`com.tencent.bugly`）。
兩者在 1.6.8.0（2024）的 Java 層被完整移除，dex 字串命中數歸零，
與該版更新說明中的「Updated Privacy Policy」時間點吻合。

**一台不具 GNSS 的室內玩具無人機 App，內建中國定位服務 SDK**，是本發現的核心疑點。
定位資料的用途需追查（可能用於「找回無人機最後位置」功能，但需驗證）。

## 證據

### dex 類別路徑字串出現次數

| marker | 1.3.0.0 | 1.4.0.0 | 1.6.0.0 | 1.6.0.1 | 1.6.4.0 | 1.6.8.0 |
|---|---|---|---|---|---|---|
| `Lcom/baidu/location` | 121 | 103 | 104 | 104 | 104 | **0** |
| `Lcom/tencent/bugly` | 128 | 132 | 131 | 132 | 167 | **0** |
| `Lcom/ryzerobotics` | 890 | 1150 | 947 | 947 | 949 | 947 |

> ⚠️ **更正（見 F03）**：原本此處主張「`com.ryzerobotics` 維持 947 命中，
> 證明 dex 未加殼，故命中數 0 是真實移除」。**這個推論的前提是錯的。**
>
> App 全部六版皆以**愛加密（Ijiami）加殼**（`assets/ijiami.ajm` + `ijm_lib/*/libexec.so`）。
> 屬選擇性保護：部分類別留在可見 dex（故 `com.ryzerobotics` 可見），
> 另有內容位於加密 payload，執行期解密載入。
>
> 因此正確的表述是：百度／Bugly 類別**在可見的 dex 中不存在**，
> 而非「已從 App 移除」。差別很大，見下方「待解疑點」。

### 對應的 native library

| lib | 1.3.0.0 | 1.4.0.0 | 1.6.0.0 | 1.6.0.1 | 1.6.4.0 | 1.6.8.0 | 歸屬 |
|---|---|---|---|---|---|---|---|
| `libBugly.so` | X | X | X | X | X | . | 騰訊 Bugly |
| `libBugly-ext.so` | . | . | . | . | X | . | 騰訊 Bugly |
| `liblocSDK7.so` | X | . | . | . | . | . | 百度定位 SDK v7 |
| `liblocSDK8a.so` | . | X | X | X | X | **X** | 百度定位 SDK v8 |
| `libRoadLineRebuildAPI.so` | X | X | X | X | X | **X** | 百度地圖 SDK |
| `libpatchtool.so` | X | X | X | X | X | **X** | 熱修補（見 F03） |

### 對應的硬編碼網域

移除於 1.6.8.0：`loc.map.baidu.com`、`api.map.baidu.com`、`itsdata.map.baidu.com`、
`daup.map.baidu.com`、`android.bugly.qq.com`、`astat.bugly.qcloud.com`、
`astat.bugly.cros.wr.pvp.net`、`h.trace.qq.com`、`rqd.uu.qq.com`

**重現方式**：`tools/apk_quicklook.ps1`，原始資料於 `static/quicklook.json`

## ⚠️ 尚未解答的關鍵疑點（已大幅擴充）

**1.6.8.0 的百度定位相關元件，七項中有六項仍然保留，只有 Java 類別在可見 dex 中消失。**

| 項目 | 1.6.8.0 | 證據 |
|---|---|---|
| `com.baidu.location` 類別 | ❌ 可見 dex 中無 | `dex:1.6.8.0` 命中 0 |
| `com.baidu.location.f` **服務宣告** | ✅ **仍在** | `src:1.6.8.0:AndroidManifest.xml:23` |
| **百度 LBS API Key** | ✅ **仍在** | `src:1.6.8.0:AndroidManifest.xml:24` |
| `liblocSDK8a.so` | ✅ **仍在** | `lib:1.6.8.0:liblocSDK8a.so` |
| `libRoadLineRebuildAPI.so` | ✅ **仍在** | `lib:1.6.8.0:libRoadLineRebuildAPI.so` |
| `ACCESS_FINE_LOCATION` | ✅ **仍在** | manifest 權限 |
| `ACCESS_COARSE_LOCATION` | ✅ **仍在** | manifest 權限 |

manifest 中仍宣告：
```xml
<service android:enabled="true" android:name="com.baidu.location.f" android:process=":remote"/>
<meta-data android:name="com.baidu.lbsapi.API_KEY" android:value="NQuYO2K…nWCVp"/>
```

**若真是完整移除，manifest 宣告與 API key 沒有理由留下**——
宣告一個不存在的類別，該 service 啟動時會直接 ClassNotFoundException。

### 已排除的假設

smali 全文檢索 `locSDK|RoadLine|patchtool|baidu|BDLocation|LocationClient`：
**可見的 smali 中零命中**（僅 AndroidManifest 與簽章檔的檔案列表有）。
`loadLibrary` 全列舉也**未見** `locSDK8a`、`RoadLineRebuildAPI` 或 `patchtool`。

→ 原假設 (b)「可見程式碼中以 JNI 或反射呼叫」**已排除**。

### 剩餘兩種假設

- **(a) 不完整的移除** — 程式碼移除了，manifest／native／權限沒清乾淨。
  屬供應鏈衛生問題，嚴重度低。但殘留範圍達六項，異常之大。
- **(b) 移入加密 payload** — 百度 SDK 位於 `ijiami.ajm`（668 KB，見 **F03**），
  執行期解密載入。若成立，「移除中國定位 SDK」的表象與實際不符，**嚴重度高**。

**加殼的存在使靜態分析無法分辨這兩者。必須動態驗證。**

### 決定性測試

Frida hook `System.loadLibrary` / `dlopen` / `ClassLoader.loadClass`，
啟動 App 後觀察：
- 是否載入 `liblocSDK8a.so` → 直接分辨 (a) 與 (b)
- 是否出現 `com.baidu.*` 類別
- `:remote` 程序是否真的啟動（`adb shell ps | grep remote`）

> 附帶：`libpatchtool.so` 同樣**未見任何 `loadLibrary` 呼叫**，狀況與 `liblocSDK8a.so` 相同。
> 熱修補機制的實際存在與否，一併由上述動態測試回答。

## 觀測邊界

- 純靜態 dex 字串比對。**未證明**這些 SDK 在執行期實際被初始化或上傳任何資料。
- 掃描對加殼／執行期動態載入無效。本 App 含 `libpatchtool.so`，
  故「掃不到」不等於「不存在」。
- 未檢查 `assets/` 內是否藏有次要 dex 或加密設定檔。**待補。**

## 下一步

- [ ] jadx 反編譯 1.6.4.0，找出百度定位 SDK 的**呼叫點**與請求的定位精度／頻率
- [ ] 檢查所要求的位置權限（`ACCESS_FINE_LOCATION`？）在各版本的演變
- [ ] Frida hook 驗證 1.6.8.0 是否仍載入 `liblocSDK8a.so`
- [ ] 對照 Ryze 隱私權政策，確認位置蒐集是否有揭露
- [ ] **動態驗證**：實際飛行並抓包，確認有無流量流向百度／騰訊端點
