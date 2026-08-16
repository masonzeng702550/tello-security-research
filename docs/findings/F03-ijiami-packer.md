# F03 — 全部六個版本以愛加密（Ijiami）商用加固產品加殼

| 欄位 | 內容 |
|---|---|
| 編號 | F03 |
| 層級 | L3 供應鏈（分析阻礙） |
| 分類 | 設計缺陷 / 反分析 |
| 嚴重度 | Info（本身非漏洞）— 但**削弱所有靜態分析結論的效力** |
| 受影響版本 | 全部（1.3.0.0 – 1.6.8.0） |
| 狀態 | 已確認 |
| 新穎性 | 本研究新發現（Tello App 部分）；同型問題前人已在 DJI GO 4 提出 |

## 摘要

Tello App 自 2019 至 2024 全部六個版本，皆以**愛加密（Ijiami）**——
中國的商用 Android 應用加固產品——進行加殼保護。

這對應 Synacktiv 2020 對 DJI GO 4 的**第四項發現**（反除錯、混淆、動態解密與加殼，
手法近似惡意程式）。**問題延續到子品牌，且至 2024 年仍未改變。**

## 證據

### 加殼元件（`lib:` 與 assets）

```
assets/ijiami.ajm                    加密 payload（1.6.8.0 為 667,978 bytes）
assets/ijm_lib/arm64-v8a/libexec.so  native loader
assets/ijm_lib/armeabi/libexec.so
assets/ijm_lib/x86/libexec.so
assets/ijm_lib/x86_64/libexec.so
```

### AndroidManifest 的殼進入點

`src:1.6.8.0:AndroidManifest.xml:22`
```xml
<application
    android:appComponentFactory="s.h.e.l.l.A"
    android:name="s.h.e.l.l.S"
    ... />
```

`s.h.e.l.l` 套件是殼的進入點，取代原本的 Application 類別。

### 殼的載入邏輯

`src:1.6.8.0:smali/s/h/e/l/l/N.smali:179-230`
```smali
const-string v0, "exec"
invoke-static {v0}, Ljava/lang/System;->loadLibrary(...)
const-string v0, "execmain"
...
const-string v0, "exec_x86"      # 依 ABI 分歧
const-string v0, "execmain_x86"
```

對應 `assets/ijm_lib/*/libexec.so`。

### 各版本 `ijiami.ajm` 大小

| 版本 | ajm 大小 | ijiami 相關項目數 |
|---|---|---|
| 1.3.0.0 | 829,645 | 4 |
| 1.4.0.0 | 862,647 | 5 |
| 1.6.0.0 | 723,739 | 5 |
| 1.6.0.1 | 724,573 | 5 |
| 1.6.4.0 | 742,266 | 5 |
| 1.6.8.0 | 667,978 | 5 |

## 保護機制：DEX 方法主體抽取（已實測量化）

apktool 能解出大量 smali，但**方法主體是空的**。實例
（`src:1.6.8.0:smali/com/ryzerobotics/tello/common/c/d.smali`）：

```smali
.method public b()Lokhttp3/OkHttpClient;
    .locals 1
    const/4 v0, 0x0
    return-object v0
    nop
.end method
```

宣告回傳 `OkHttpClient`，實際只有 `return null` 加 `nop` 填充。
另一個方法 `a([Ljava/io/InputStream;)Ljavax/net/ssl/X509TrustManager;`
佔 300 行，內容同樣是 `return null` + 約 290 個 `nop`。

**nop 填充是為了保留原方法的長度與偏移量**，真正的 bytecode 被移入
`ijiami.ajm`，執行期才還原。這是愛加密的「DEX 抽取」保護。

### 抽取比例（實測）

| 範圍 | 方法總數 | 疑似被抽取 | 比例 |
|---|---|---|---|
| `com/ryzerobotics/**`（應用程式碼） | 5,388 | 4,808 | **89.2%** |
| `okhttp3/**`（第三方函式庫） | 1,685 | 1,476 | **87.6%** |

判定準則：方法主體不含任何 `invoke-` 指令、且含 `nop` 填充。

**這是全面抽取，不是選擇性保護。**

### `ijiami.ajm` 的檔案特徵

```
大小   667,978 bytes
magic  69 6e 64 6c 30 31    "indl01"
熵     7.991 bits/byte      → 已加密（接近理論最大值 8.0）
```

載入點：`src:1.6.8.0:smali/s/h/e/l/l/S:1818-1824`
呼叫 `Context.getAssets()` 後 `AssetManager.open(String)`。

## ⚠️ 對靜態分析可信度的影響（關鍵）

**必須區分「什麼還看得到」與「什麼看不到」：**

| 資料 | 是否可信 | 理由 |
|---|---|---|
| **類別清單** | ✅ 可信 | 類別定義保留在 dex |
| **欄位宣告** | ✅ 可信 | 同上 |
| **方法簽章** | ✅ 可信 | 同上 |
| **dex 字串池** | ✅ 可信 | **已驗證**：憑證檔名等字串仍在池中 |
| **AndroidManifest** | ✅ 可信 | 獨立檔案，未加密 |
| **assets / lib** | ✅ 可信 | 獨立檔案 |
| **方法主體（行為）** | ❌ **不可信** | 89% 被抽走 |
| **呼叫點 / 控制流** | ❌ **不可信** | 同上 |
| **方法內的字串引用關係** | ❌ **不可信** | 字串在池中，但誰用它看不到 |

### 字串池完好是關鍵的補償

已驗證 `aasky-net.cer`、`ryzerobotics.com.crt`、`dji-com2.crt`、
`amazon_root_ca1.pem`、`RYZE_Privacy_Policy.html` **皆存在於 dex 字串池**，
儘管它們不被任何可見的方法主體引用。

**推論依據**：抽取後的 bytecode 仍以原始索引引用 dex 字串表，
因此**方法（無論可見與否）所引用的字串必然保留在池中**。
反之，**某字串不在池中 ⇒ 沒有任何方法引用它**。

這使得「以字串池的存否做否定判斷」仍然成立——
F01 對 `locSDK8a` 的結論即建立在此基礎上。

> 此推論假設愛加密不改寫 dex 字串表。若改寫，索引機制會失效，
> 故此假設合理，但未經獨立驗證。

### 對各 findings 的實際影響

| finding | 是否受影響 | 說明 |
|---|---|---|
| F01 SDK 縱向 | ✅ **不受影響** | 依據類別清單 + 欄位宣告 + 字串池，皆完好 |
| F02 端點清單 | ⚠️ 部分 | 網域清單有效；「哪段程式碼呼叫」無法取得 |
| F04 pinning | ❌ **受阻** | 已定位到實作類別，但方法主體被抽走 |
| F05 政策落差 | ✅ 不受影響 | 依據 assets 內的 HTML 檔案 |
| F06 控制通道 | ✅ 不受影響 | 依據 pcap |

**F01 原本的一項排除必須撤回**：先前主張
「smali 全文檢索 `locSDK|patchtool|baidu` 零命中 → 排除 JNI／反射呼叫」。
呼叫點位於被抽走的方法主體中，**此排除無效**。
該結論已改以字串池為依據重新建立（見 F01）。

## 為什麼這件事對 F01 特別關鍵

1.6.8.0 中，百度定位相關的**周邊全部還在**，只有 Java 類別不見了：

| 項目 | 1.6.8.0 是否存在 | 證據 |
|---|---|---|
| `com.baidu.location` 類別 | ❌ 可見 dex 中無 | `dex:1.6.8.0` 命中 0 |
| `com.baidu.location.f` 服務宣告 | ✅ **仍在** | `src:1.6.8.0:AndroidManifest.xml:23` |
| 百度 LBS API Key | ✅ **仍在** | `src:1.6.8.0:AndroidManifest.xml:24` |
| `liblocSDK8a.so` | ✅ **仍在** | `lib:1.6.8.0:liblocSDK8a.so` |
| `libRoadLineRebuildAPI.so` | ✅ **仍在** | `lib:1.6.8.0:libRoadLineRebuildAPI.so` |
| `ACCESS_FINE_LOCATION` | ✅ **仍在** | manifest 權限 |
| `ACCESS_COARSE_LOCATION` | ✅ **仍在** | manifest 權限 |

manifest 宣告的 service：
```xml
<service android:enabled="true" android:name="com.baidu.location.f" android:process=":remote"/>
<meta-data android:name="com.baidu.lbsapi.API_KEY" android:value="NQuYO2K…nWCVp"/>
```
（API key 完整值見 manifest；為客戶端金鑰，任何人取得 APK 皆可讀出，此處部分遮蔽。）

**七項周邊有六項保留，只有 Java 類別在可見 dex 中消失。**
若真是完整移除，manifest 宣告與 API key 沒有理由留下——
宣告一個不存在的類別，該 service 啟動時會直接 ClassNotFoundException。

兩種解釋，需動態驗證分辨：
- **(a) 不完整的移除**：程式碼移除了，但 manifest／native／權限沒清乾淨。
  屬供應鏈衛生問題，嚴重度低，但殘留範圍之大值得記錄。
- **(b) 移入加密 payload**：百度 SDK 被搬進 `ijiami.ajm`，執行期解密載入。
  若成立，等於「移除中國定位 SDK」的表象與實際不符，嚴重度高。

## 對後續分析方法的影響

1. **不能只靠靜態分析下否定結論。** 動態驗證從「加分項」變成「必要條件」。
2. **Frida hook 需處理殼的反除錯。** 愛加密通常帶 ptrace 偵測、
   除錯器偵測與完整性校驗，可能需要反反除錯。
3. **脫殼是可選路徑**：以記憶體 dump 取出執行期解密的 dex。
   但需評估必要性——若動態流量觀測已足以回答研究問題，不必然要脫殼。

## 下一步

- [ ] Frida hook `System.loadLibrary` / `dlopen`，記錄執行期實際載入的 native 庫
      → 直接判定 `liblocSDK8a.so` 是否被載入（分辨 (a) 與 (b)）
- [ ] hook `ClassLoader.loadClass`，觀察是否出現 `com.baidu.*` 類別
- [ ] 觀察 `:remote` 程序是否真的被啟動（`adb shell ps`）
- [ ] 測試 App 在 root／Frida 環境下是否拒絕啟動（殼的反除錯強度）
- [ ] 評估是否需要脫殼
