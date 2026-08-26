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

## 追加：方法抽取的精確量化與選擇性保護（2026-08-26）

本findings原記載「89% 的方法主體被抽取」。
以自建的 DEX 解析器逐一解碼指令後，該數字**獲得確認並可進一步細分**。

### 量測方法

判定「樁」的準則：方法的**第一個指令即為 `return`**，
或**常數載入後緊接 `return`**（即 `const/4 v0, 0x0; return-object v0` 這類樣態）。
不依賴 apktool 的輸出，直接解析 `code_item` 的 `insns`。

### 結果：保護是選擇性的

| 套件 | 方法數 | 樁 | 比例 |
|---|---|---|---|
| `com/ryzerobotics/tello` | 3,603 | 3,556 | **98.7%** |
| `com/ryzerobotics/report` | 662 | 630 | **95.2%** |
| `com/ryzerobotics/common` | 695 | 609 | **87.6%** |
| **`com/ryzerobotics` 合計** | **4,960** | **4,795** | **96.7%** |
| `com/squareup/okhttp` | 1,472 | 1,411 | 95.9% |
| `org/apache/commons` | 1,827 | 1,750 | 95.8% |
| `com/bumptech/glide` | 1,520 | 1,445 | 95.1% |
| `com/xj/gamesir` | 698 | 634 | 90.8% |
| **`android/support/v4`** | **7,187** | **483** | **6.7%** |
| **`android/support/v7`** | **5,212** | **274** | **5.3%** |
| **`android/support/design`** | **1,367** | **77** | **5.6%** |

```
com/ryzerobotics 合計    96.7% 為樁
其餘第三方函式庫         27.3% 為樁（但此數字被 android/support 拉低）
全 dex 整體              39.2% 為樁
```

### 判讀

**加殼器保護了 App 自有程式碼與絕大多數第三方函式庫，
唯獨放過 `android/support/*`**——研判為相容性或效能考量的白名單。

`android/support/*` 佔全 dex 46,331 個方法中的約 13,700 個（近 30%），
**足以將整體比例由 96.7% 稀釋至 39.2%**。

> ### ⚠️ 一個差點成立的錯誤更正
>
> 本次分析初期，以「全 dex」為母體量得樁比例僅 39.2%，
> 一度判定本findings的 89% 有誤。
> **該判定本身才是錯的**——母體選擇不當，
> 把未受保護的 `android/support/*` 混入分母。
>
> **教訓**：對「某比例過高／過低」提出質疑前，
> 必須先確認雙方的**母體定義是否一致**。
> 本findings的 89% 指的是受保護的程式碼，而非整份 dex。

### 六個版本皆已加殼

| 版本 | 加殼 | 全 dex 樁比例 |
|---|---|---|
| 1.3.0.0 | ijiami | 38.4% |
| 1.4.0.0 | ijiami | 40.1% |
| 1.6.0.0 | ijiami | 39.9% |
| 1.6.0.1 | ijiami | 39.9% |
| 1.6.4.0 | ijiami | 40.3% |
| 1.6.8.0 | ijiami | 39.2% |

**全部六個版本自 2019 至 2024 皆使用愛加密**，比例穩定，
顯示保護策略未曾改變。

## 追加：記憶體 DEX 傾印**無法**解開此殼（2026-08-26）

### 嘗試

目標為自記憶體取得還原後的 dex，以解開本findings所述的方法抽取。

1. Frida `spawn` 注入 → **App 立即死亡**，即使腳本內容僅有一個 `setTimeout`。
   與本findings原記載的殼衝突一致。
2. 改為 **attach 至已啟動的行程** → App 穩定存活，可執行腳本。
3. 自 `/proc/<pid>/maps` 定位 `[anon:dalvik-DEX data]` 區段，
   以 root 經 `/proc/<pid>/mem` 讀出（對 App 零擾動）。

> **踩到的坑**：Android 的 `sh` 對 `$(( 0x7c47cde000 ))` 會**截斷為 32 位元**
> （得 1,204,674,560，正確值為 532,318,158,848），
> 導致 `dd` 讀取錯誤位置而產出空檔。
> 位移須於 PC 端以全精度計算後，以字面值配合 `iflag=skip_bytes` 傳入。

### 結果：傾印所得與 APK 內的 dex **完全相同**

| 項目 | APK 內 `classes.dex` | 記憶體傾印 |
|---|---|---|
| 大小 | 7,067,956 | 7,067,956 |
| 類別 | 5,722 | 5,722 |
| 方法 | 49,705 | 49,705 |
| 有 `code_item` | 46,331 | 46,331 |

**兩者位元組層級一致。**

### 判讀：此殼不以「還原整份 dex」的方式運作

ART 將 APK 的 `classes.dex` 映射至 `[anon:dalvik-DEX data]`，
該區段內即為原始的（已抽取的）dex。

→ **愛加密於執行期還原方法主體的方式，並非產生一份乾淨的 dex，
   而應是在 `ArtMethod` 層級改寫程式碼指標。**

因此**單純的記憶體 dex 傾印無法解開此殼**。
若要取得真實的方法主體，須轉向：

- 攔截 `ArtMethod` 的 `entry_point` 或 `code_item` 指標改寫
- 或於方法實際執行時逐一擷取

兩者皆需與殼的反偵錯機制正面對抗，工作量遠大於 dex 傾印。

> **對後續研究的意義**：本findings所界定的靜態分析邊界**依然有效**。
> F02／F04／F05／F10 中所有標註「因方法主體被抽取而無法判斷」的項目，
> 不會因為記憶體傾印而獲得解答。
