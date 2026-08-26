# F17 — 原生程式庫分析：無隱藏端點，百度模組為孤兒程式碼

| 欄位 | 內容 |
|---|---|
| 編號 | F17 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 靜態分析 |
| 嚴重度 | Info — 未發現隱藏的資料蒐集 |
| 受影響版本 | 1.6.8.0（並與 1.6.0.1／1.6.4.0 比對） |
| 狀態 | **T0／T0′ 靜態 + T2 執行期** |
| 對應計畫 | `docs/05-overnight-plan.md` P3 |

## 為何需要這項分析

F03 證實 Java 層有 96.7% 的方法主體被抽取，且**記憶體傾印無法還原**。
若廠商將端點或蒐集邏輯放在**原生層**，Java 層的所有分析都會漏掉。

本findings檢視 1.6.8.0 全部九個 arm64 原生程式庫，回答兩個問題：

1. 原生層是否藏有 Java 層看不到的端點、金鑰或蒐集邏輯？
2. `liblocSDK8a.so`（百度）既然仍出貨，它到底是什麼？

## 一、無隱藏端點

對九個 `.so` 逐一抽取可列印字串並比對 URL／網域／IP 樣式：

| 程式庫 | 大小 | 網路相關字串 |
|---|---|---|
| `libGamesir.so` | 72,400 | **無** |
| `libdreamDroneParser.so` | 9,992 | **無** |
| `libgpuimage-library.so` | 5,448 | **無** |
| `libijkffmpeg.so` | 2,419,360 | 僅 `ffmpeg.org`、`w3.org`（建置資訊） |
| `libijkplayer.so` | 294,864 | 僅 `ffmpeg.org` |
| `libijksdl.so` | 481,112 | **無** |
| `libjpegbither.so` | 230,784 | **無** |
| `liblocSDK8a.so` | 43,112 | **無** |
| `libphotoedithelp.so` | 54,904 | **無** |

→ **原生層未發現任何自訂端點。** 唯一的網域來自 ffmpeg 自身的建置字串。

## 二、`liblocSDK8a.so`：百度 SDK 的加密輔助層，且已成孤兒

### 它是什麼

以 ELF 動態符號表解析，18 個 JNI 函式全部指向百度的類別：

```
Java_com_baidu_location_Jni_encrypt
Java_com_baidu_location_Jni_murmur
Java_com_baidu_serverLoc_Jni_encrypt
…
```

其他匯出顯示其功能：

```
_ZN12GcjEncryptor13Transform_yj5Edd    ← GCJ-02 座標轉換
_ZN3MD58MD5FinalEPhP7MD5_CTX           ← MD5
_Z13decode_base64PhPKcjRj              ← Base64
_Z12gzdecompressPhmS_Pm                ← gzip 解壓
enciphering / encodeChar / encode2 / encode4
```

**`GcjEncryptor` 值得記錄**：GCJ-02 是中國法規要求的座標偏移系統。
該符號的存在說明此模組原本用於處理中國境內的定位座標。

> 惟 43,112 bytes 遠小於完整的百度定位 SDK，
> 研判本檔僅為該 SDK 的**加密／編碼輔助層**，主體邏輯在 Java 側。

### 它已無法被呼叫

JNI 函式必須有對應的 Java 類別才能被觸發。檢視各版本 dex 的類別清單：

| 類別 | 1.6.0.1 | 1.6.4.0 | 1.6.8.0 |
|---|---|---|---|
| `com/baidu/location/Jni` | ✓ | ✓ | **✗** |
| `com/baidu/serverLoc/Jni` | ✗ | ✗ | ✗ |
| `com/baidu/location/fused/sdk/Jni` | ✗ | ✗ | ✗ |
| **`com/baidu` 開頭的類別總數（1.6.8.0）** | — | — | **0 個** |

→ **1.6.8.0 中不存在任何 `com/baidu` 類別。**
   `liblocSDK8a.so` 的 18 個 JNI 進入點**在 Java 側無人可呼叫**。

### 三條獨立證據匯聚

| 證據 | 來源 | 結論 |
|---|---|---|
| Java 類別清單、膠水程式碼、`LocationUtil` 改寫 | F01 原有 | 已移除 |
| 執行期 `/proc/pid/maps` 未載入（權限開關皆同） | F01 追加 | 未載入 |
| **JNI 進入點所需的 Java 類別不存在** | **本findings** | **結構上不可呼叫** |

第三條**不依賴執行期觀測**，也**不受加殼影響**（類別清單不會被抽取），
是三者中最強的一條。

## 三、另兩個庫的實際用途

### `libdreamDroneParser.so`（9,992 bytes）

名稱易誤導為「無人機協定解析器」，但匯出顯示其功能**僅限視訊格式處理**：

```
Java_com_sdk_DreamDroneParser_decodeVideoWH
Java_com_sdk_DreamDroneParser_getWidth / getHeight
Java_com_sdk_DreamDroneParser_yuv420pToyuv420sp
Java_com_sdk_DreamDroneParser_yuv420spToyuv420p
h264_decode_seq_parameter_set        ← 解析 H.264 SPS 取得畫面尺寸
```

→ **解析 H.264 的序列參數集以取得解析度，並做 YUV 格式轉換。**
   **不含協定解析、不含加密、不含網路。**
   對應的 Java 類別 `com/sdk/DreamDroneParser` 於三個版本皆存在，故為活程式碼。

### `libGamesir.so`（72,400 bytes）

21 個 JNI 函式全部屬 `com.xj.gamesir.sdk.bluetooth.ble.Gamesir`：

```
decryJoyData / decryJoytouchData      ← 解碼藍牙手把的搖桿資料
setABXYDetectArea / setFirstPoint     ← 觸控區域對應
isMoveOutIgnoredArea / setIgnoreDistance
```

→ **純為藍牙手把的輸入解碼與觸控映射，全部在本機完成。**
   與 F09 記載的 `client.vgabc.com` 上報**分屬不同層**——
   上報邏輯在 Java 側，本原生庫不涉及網路。

## 判讀

**原生層未發現任何 Java 層看不到的資料蒐集或端點。**

這對本研究的意義是：F03 所界定的「靜態分析邊界」雖然嚴重，
但**該邊界的另一側（原生層）已排除**。
未決問題仍集中於被抽取的 Java 方法主體，而非原生程式碼。

## 觀測邊界

- 僅分析 **arm64-v8a**。其他 ABI 的 `.so` 未逐一比對，
  惟同名檔案通常為同一原始碼的不同編譯目標。
- **未反組譯**任何原生程式碼，僅解析 ELF 符號表與可列印字串。
  以執行期組出的字串（如經 XOR 混淆的端點）不會被此方法發現。
- `libijkffmpeg.so` 等大型多媒體庫未逐一檢視全部符號。
- `assets/ijm_lib/*/libexec.so`（加殼器自身，474 KB）**未納入本次分析**，
  該檔為愛加密的執行期元件，其行為屬 F03 範疇。
