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

## ✅ 已解決：百度 SDK 為真實移除，非隱藏於加殼 payload

> 前一版將此列為未決疑點。經 1.6.4.0 與 1.6.8.0 的完整反編譯比對後，
> **結論為假設 (a)：真實移除，殘留為建置衛生問題。**

### 證據一：類別清單差異（apktool 全量比對）

1.6.4.0（6,015 類別）→ 1.6.8.0（5,722 類別）：**移除 296、新增 3**。

| 移除的套件 | 類別數 |
|---|---|
| `com/tencent/bugly` | 163 |
| `com/baidu/location` | 100 |
| `com/baidu/lbsapi` | 19 |
| `com/baidu/a` | 8 |
| `com/ryzerobotics/tello` | **3** |
| `com/tencent/rqd` | 1 |
| 其他 | 2 |

**296 個移除中有 290 個屬百度／騰訊**，是完整而外科式的移除。

新增的 3 個（`BindColorili`、`BaseFragmentActivityuam`、`BackgroundPosternhy`）
名稱帶隨機三字母後綴，為**愛加密注入的誘餌類別**，非實際程式碼變更。

### 證據二：膠合程式碼也被移除

被移除的 3 個 Ryze 自家類別中，兩個正是百度整合的接點：

`src:1.6.4.0:smali/com/ryzerobotics/tello/common/utils/o$b.smali`
```smali
.class Lcom/ryzerobotics/tello/common/utils/o$b;
.implements Lcom/baidu/location/c;                       ← 百度定位監聽器
.method public a(Lcom/baidu/location/BDLocation;)V       ← 定位回呼
```

`o$a` 為介面 `a([D)V`（座標陣列回呼）。**兩者在 1.6.8.0 皆不存在。**

### 證據三：`LocationUtil` 被改寫為只用 Android 原生 API

外層類別 `o`（`.source "LocationUtil.java"`）的**欄位宣告**比對
（欄位宣告不受方法抽取影響，見 F03）：

| 欄位 | 1.6.4.0 | 1.6.8.0 |
|---|---|---|
| `Lcom/baidu/location/LocationClient` | ✅ `c` | ❌ |
| `Lcom/baidu/location/c`（監聽器） | ✅ `d` | ❌ |
| `Landroid/location/LocationManager` | ✅ `e` | ✅ `a` |
| `Landroid/location/Location` | ✅ `f` | ✅ `b` |
| `Landroid/location/LocationListener` | ✅ `h` | ✅ `d` |
| 檔案行數 | 671 | **349** |

**1.6.4.0 為雙定位後端（百度 + Android 原生）；1.6.8.0 拆掉百度，只留 Android 原生。**

### 證據四：字串池中相關字串全數消失

| 字串 | 1.6.4.0 | 1.6.8.0 |
|---|---|---|
| `locSDK8a` | ✅ | ❌ |
| `com.baidu.location` | ✅ | ❌ |
| `BDLocation` | ✅ | ❌ |
| `LocationClient` | ✅ | ❌ |
| `com.baidu.lbsapi.API_KEY` | ✅ | ❌ |
| `baidu` | ✅ | ❌ |
| `bugly` / `BuglyNative` | ✅ | ❌ |
| `dreamDroneParser` / `Gamesir` 等仍在用的 | ✅ | ✅ |

`System.loadLibrary("locSDK8a")` 需要 `locSDK8a` 這個字串常數。
dex 字串池完好（見 F03 的驗證），**該字串不存在 ⇒ 無任何方法載入該函式庫**。

## 修正先前的一項推論

先前主張「smali 全文檢索零命中 → 排除 JNI／反射呼叫」。
**該推論無效**——呼叫點位於被抽走的方法主體中（89% 方法被抽取，見 F03）。

結論已改以**字串池**為依據重新建立，如上。字串池不受方法抽取影響。

## 殘留清單（已確認為死重）

| 殘留物 | 狀態 |
|---|---|
| `liblocSDK8a.so` | 仍打包，但 `locSDK8a` 字串已不存在 → 無人載入 |
| `libRoadLineRebuildAPI.so` | 仍打包；該字串在**兩個版本**皆不存在（研判由百度 native 內部 dlopen） |
| `com.baidu.location.f` 服務宣告 | 仍在 manifest，但類別不存在 → 若被啟動會 ClassNotFoundException |
| 百度 LBS API Key meta-data | 仍在 manifest，但已無程式碼讀取 |
| `ACCESS_FINE/COARSE_LOCATION` | **不是殘留** — App 仍以 Android 原生 API 取位置 |

> 位置權限先前被列為疑點，前提是「定位功能已移除」。
> **該前提錯誤**：移除的只是百度這個後端，定位功能保留。權限合理。

## 關於 `libpatchtool.so`

`patchtool` 字串在**兩個版本的字串池皆不存在** → Java 層從未按名稱載入。
其是否由 native 程式碼 `dlopen`，靜態無法判斷。
熱修補機制的實際運作與否仍待動態驗證，但「Java 層主動觸發」已可排除。

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

## 追加：原生程式庫未一併清除，但執行期確認未載入（2026-08-26）

本findings原有的證據**全部位於 Java 層**（類別清單、膠水程式碼、
`LocationUtil` 改寫、字串池）。檢視 APK 內的**原生程式庫**後發現一項落差。

### 出貨內容：百度的 .so 仍在 1.6.8.0

直接自 APK 讀取（非解包目錄，避免誤差）：

| 版本 | 百度／Bugly 的 arm64 原生庫 |
|---|---|
| 1.3.0.0 | （無 arm64 目錄） |
| 1.4.0.0 | `libBugly.so`, `liblocSDK8a.so` |
| 1.6.0.0 | `libBugly.so`, `liblocSDK8a.so` |
| 1.6.0.1 | `libBugly.so`, `liblocSDK8a.so` |
| 1.6.4.0 | `libBugly-ext.so`, `libBugly.so`, `liblocSDK8a.so` |
| **1.6.8.0** | **`liblocSDK8a.so`** ← Bugly 已移除，百度未移除 |

`liblocSDK8a.so` 為 43,112 bytes，
1.6.8.0 的雜湊與 1.6.0.0／1.6.0.1 **完全相同**（`sha256=3d6be61c9906049b…`）。

→ **Java 層清除了，原生程式庫仍隨 APK 出貨。**

### 執行期驗證：未載入

「隨附 .so」不等於「會使用它」。且因加殼抽走 89% 的方法主體（見 F03），
**此問題無法以靜態分析回答**。改以執行期直接檢視行程的記憶體對映。

```
啟動 App → 讀 /proc/<pid>/maps → 列出實際載入的 .so
```

| 條件 | `liblocSDK8a.so` | `libBugly.so` | 載入總數 |
|---|---|---|---|
| 位置權限**拒絕** | ❌ 未載入 | ❌ 未載入 | 267 |
| **位置權限授予**、等待 20 秒 | ❌ **仍未載入** | ❌ 未載入 | 267 |

**行程中不存在任何定位相關的原生程式庫。**
App 私有目錄下唯一被載入的是 `files/libexec.so`——加殼器自身的元件（見 F03）。

> **控制了最明顯的混淆變因**：定位 SDK 可能因缺少權限而不初始化。
> 授予 `ACCESS_FINE_LOCATION` 與 `ACCESS_COARSE_LOCATION` 後重啟並等待，
> 結果不變，載入總數亦完全相同（267）。

### 判讀

**本findings的核心結論維持成立**：百度定位 SDK 在 1.6.8.0 已不再運作。

但敘述需精確化：

- ❌ 不宜說「百度 SDK 已自 1.6.8.0 移除」
- ✅ 應說「**Java 層已移除且執行期未載入；原生程式庫未一併清除，仍隨 APK 出貨**」

這同時回答了 **F05** 提出的未決問題（1.6.8.0 刪除附件一的兩種解讀）：
本次證據支持 **(a) 一致性修正**——SDK 確實不再運作，
而非 (b)「揭露減少但蒐集持續」。

### 觀測邊界

- 觀測時機為 **App 啟動後 20 秒內、未連接無人機**。
  不排除存在其他觸發條件使其載入，惟位置權限已授予，
  該情境下最自然的觸發時機已涵蓋。
- 僅測試 1.6.8.0 與單一裝置（Pixel 6 Pro / Android 13）。
- `libGamesir.so` 與 `libdreamDroneParser.so` 於本次亦未載入，
  惟當時**未連接手把與無人機**，屬預期，不可據此推論其為死程式碼。
