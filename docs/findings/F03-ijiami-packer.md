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

## ⚠️ 對既有結論的影響（重要更正）

**F01 原本主張**：「`com.ryzerobotics` 在 1.6.8.0 仍有 947 次命中，證明 dex 未加殼，
因此百度／Bugly 命中數為 0 是真實的移除。」

**這個推論的前提是錯的。App 確實有加殼。**

正確的理解：愛加密屬**選擇性保護**——部分類別留在可見的 `classes.dex`
（因此 `com.ryzerobotics` 可見、apktool 能解出大量 smali），
另有內容位於加密的 `ijiami.ajm`，於執行期解密載入。

因此「靜態掃不到某個類別」**不能**推論「該類別不存在」。
`ijiami.ajm` 有 668 KB，內容未知。

**所有基於 dex 字串掃描的否定結論，效力都降級為
「在可見的 dex 中未出現」，而非「已移除」。**

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
