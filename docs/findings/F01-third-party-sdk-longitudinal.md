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

`com.ryzerobotics` 在 1.6.8.0 維持 947，證明 dex 未被加殼或加密——
因此「命中數為 0」是真實的移除，而非掃描失效。

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

## ⚠️ 尚未解答的關鍵疑點

**1.6.8.0 移除了百度的 Java 類別與網域，卻仍保留 `liblocSDK8a.so` 與 `libRoadLineRebuildAPI.so`。**

三種可能，需逐一排除：
- (a) 建置腳本疏漏，native 檔為無用殘留 → 最可能，但屬供應鏈衛生問題
- (b) 仍透過其他路徑（JNI 直呼、反射、動態載入）使用
- (c) 由 `libpatchtool.so` 的熱修補機制在執行期恢復

→ **必須以 Ghidra 檢視 1.6.8.0 的 `liblocSDK8a.so` 是否仍有可達的匯出函式，
   並以 Frida hook `System.loadLibrary` 確認執行期是否被載入。**

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
