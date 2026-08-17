# F08 — 動態首次啟動觀測：零網路請求，且加殼未阻擋分析

| 欄位 | 內容 |
|---|---|
| 編號 | F08 |
| 層級 | L3 供應鏈與資料主權 / 方法論 |
| 分類 | 行為觀測（含否定結果） |
| 嚴重度 | Info — 未發現可疑傳輸 |
| 受影響版本 | 1.6.8.0 |
| 狀態 | **T2 執行期已驗證** |
| 對應測試 | TC-L3-01，並覆核 F01 / F03 / F04 / F05 / F07 |

## 測試環境

```
裝置      Pixel 6 Pro (raven)，Android 13 / SDK 33 / arm64-v8a
          bootloader 已解鎖，Magisk 30.7（Ramdisk 模式），SELinux Enforcing
語系      persist.sys.locale = zh-Hant-TW
App       com.ryzerobotics.tello 1.6.8.0（官方來源，SHA-256 b55f2e62…）
擷取      mitmproxy 11.0.2，CA 以 tmpfs bind-mount 掛入系統信任區
          （/system/etc/security/cacerts，SELinux context system_security_cacerts_file）
通道      adb reverse tcp:8080 → 電腦，手機 http_proxy = 127.0.0.1:8080
儀器      frida-server 17.17.0（root 執行），native-only hook
時間      2026-08-17 15:29–16:00
```

CA 有效性已由對照流量驗證：同一 proxy 成功解密 `optimizationguide-pa.googleapis.com`、
`update.googleapis.com` 等系統流量（HTTP/2 200），
僅 `youtubei.googleapis.com` 因 App 自帶 pinning 失敗——**證明攔截鏈本身可用**。

## 主要結果：完整流程零網路請求

依序執行：安裝 → 首次啟動 → 同意用戶協議 → 拒絕位置／相片／通知權限
→ 關閉連線引導 → 停留於主畫面（`TelloCameraActivity`）。

**全程未觀測到任何來自 App 的網路連線。**

90 秒定時取樣（每 15 秒）：

| 取樣點 | uid 10247 TCP | mitmproxy 新增 |
|---|---|---|
| 15s–90s（6 次） | **0** | **0 行** |

- 未連線至 `report.ryzerobotics.com`、`mydjiflight.dji.com`、
  `client.vgabc.com`、`chatsupport.ryzerobotics.com`、`aasky.net` 等
  F02 所列的任何端點
- 無遙測上報、無版本檢查、無崩潰回報
- UDP 有 2 個 socket，為無人機控制埠（8889/8890）的監聽，非對外連線

### 判讀

在**未連接無人機**的狀態下，1.6.8.0 不主動與任何後端通訊。
這是有意義的否定結果，也修正了一個常見預期
（「一啟動就會回傳裝置資訊」在此版本不成立）。

## 本地判定的地區代碼

`/data/data/com.ryzerobotics.tello/shared_prefs/share_date.xml`：

```xml
<string name="AreaCodeTello">TW</string>
<int name="DisclaimerShowState" value="1" />
<int name="spRockerMode" value="1" />
```

**`AreaCodeTello = TW`** —— App 判定使用者地區為台灣。
由於全程零網路請求，此判定**必然來自本地**（語系或 SIM），非後端查詢。

→ 這給 F05 一個新的追查方向：**該地區代碼是否影響後續行為**
（政策顯示、端點選擇、功能開關）？可用 `am` 改設定值後對照。

## GameSir 清單的週期更新痕跡（對 F02 的新線索）

`shared_prefs/gamesir_config.xml` 內建完整手把型號清單（21 筆，含 vid/pid），
同時記錄：

```xml
<long name="gamesir_lastTime" value="1786952374883" />   ← 本次啟動時間戳
<int name="GAMESIR_CHECK_LIMIT" value="0" />
<int name="gamesir_forbidden" value="2" />
```

`lastTime` + `CHECK_LIMIT` 是**節流式週期更新**的典型結構。
清單本身內建於本地，但存在更新機制——目標端點極可能為
F02 查明的 `https://client.vgabc.com/clientapi/`（GameSir／小雞科技後端）。

本次未觸發，研判被 `lastTime` 節流擋下。

**可測的假設**：將 `gamesir_lastTime` 改為足夠早的值後重啟 App，
觀察是否連線 `client.vgabc.com`。若成立，可一舉確認：
- 該端點是否仍在服務（F02 的存活問題）
- 送出哪些欄位（TC-L3-04）
- **憑證早已於 2020 過期，TLS 如何處理**（F04 的核心問題）

## 覆核既有 findings

### F01 — 百度 SDK 未於執行期載入（升級為 T2）

native hook（`dlopen` / `android_dlopen_ext`）攔截全部函式庫載入：

| 觀測標的 | 執行期是否載入 |
|---|---|
| `liblocSDK8a.so` | ❌ |
| `libRoadLineRebuildAPI.so` | ❌ |
| `libpatchtool.so` | ❌ |
| `libBugly.so` | ❌（1.6.8.0 已不打包） |
| App 自有 `.so` 中唯一被載入者 | `libexec.so`（加殼 loader） |

APK 打包 11 個 `.so`，**首次啟動至主畫面期間僅載入 1 個**。

> ⚠️ **觀測邊界**：`libdreamDroneParser.so`（無人機協定實作）**同樣未載入**，
> 因為尚未連接無人機。這證明**這些函式庫是按需載入的**。
> 因此本結果僅能支持「首次啟動至主畫面期間未載入」，
> **不能推論「永不載入」**。連上無人機後需重測。

### F03 — 加殼機制的執行期證據，以及反分析強度

**機制證實**：

```
/data/user/0/com.ryzerobotics.tello/files/libexec.so     從 assets 解出後 dlopen
Anonymous-DexFile@2269758449.jar                          執行期解密的記憶體 dex
s.h.e.l.l.A.instantiateApplication                        殼的 AppComponentFactory
```

`Anonymous-DexFile` 是 `InMemoryDexClassLoader` 的產物，
**直接證實 F03 所述「方法主體被抽取、執行期還原」的機制**。

**反分析強度：比預期弱。**

App 在下列條件下**穩定運行至主畫面**，logcat 中無任何
root／debugger／tamper／integrity 偵測訊息：

- bootloader 已解鎖（`verifiedbootstate = orange`）
- Magisk root 生效，**未啟用任何隱藏**（無 DenyList、無 Shamiko、無 Zygisk）
- `frida-server` 以 root 常駐
- 由 frida spawn 啟動，並掛載 native hook

→ **本 App 的加殼未實作有效的 root／模擬器／除錯器阻擋。**

### 兩次崩潰皆為儀器造成，非反分析

過程中 App 崩潰兩次，**經追查皆為 Frida 的 Java 層 hook 所致**：

| Hook | 崩潰 | 機制 |
|---|---|---|
| `java.lang.System.loadLibrary` | `UnsatisfiedLinkError: library "libframework-connectivity-jni.so" not found` | overload 分派錯亂：framework 內部呼叫 native 版被攔截後轉往 Java 版 |
| `java.lang.ClassLoader.loadClass` | `VerifyError: Verifier rejected class MyApplication` | 干擾殼的 dex 還原，ART 驗證器拒絕還原後的類別 |

第一項崩在 `ActivityThread.handleBindApplication`（Android 自身初始化網路層），
與 App 無關。改用 **native-only hook** 後 App 完全穩定。

> **不可將此二者記為「反分析偵測」。** 兩者都是
> 「加殼與 instrumentation 不相容」的表現，是否為刻意設計無法由此區分。
> 欲區分需觀察是否有主動偵測邏輯（如檢查 `/proc/self/maps` 中的 frida 字串），
> 屬後續工作。

### F05 — 台灣裝置顯示簡體中文協議（補上缺口）

`persist.sys.locale = zh-Hant-TW` 的裝置，首次啟動顯示：

```
標題    《TELLO APP用戶協議》            繁體
內文    《用户协议》…深圳市睿炽科技有限公司   簡體
連結    《隱私權政策》《TELLO免責聲明和安全操作指引》  繁體
```

**介面經繁體本地化，但實質條款內文為簡體原文。**

→ F05 先前標記的觀測邊界「未確認台灣使用者實際會看到哪一份政策」
**已解除**：看到的是中文版，且內文為簡體。英文版在此情境不會出現。

證據：`docs/screenshots/07-tello-first-launch-agreement.png`

### F07 — 藍牙權限因 targetSdk 30 而免詢問取得

安裝後權限狀態：

| 權限 | 授予 | 說明 |
|---|---|---|
| `ACCESS_FINE_LOCATION` | ❌ | 使用者拒絕 |
| `ACCESS_COARSE_LOCATION` | ❌ | 使用者拒絕 |
| `READ_MEDIA_IMAGES/VIDEO/AUDIO` | ❌ | 使用者拒絕 |
| `READ_EXTERNAL_STORAGE` | ❌ | 使用者拒絕 |
| `POST_NOTIFICATIONS` | ❌ | 使用者拒絕 |
| **`BLUETOOTH_CONNECT`** | ✅ | **未詢問** |
| **`BLUETOOTH_SCAN`** | ✅ | **未詢問** |
| **`BLUETOOTH_ADVERTISE`** | ✅ | **未詢問** |

三個藍牙權限旗標為 `REVOKE_WHEN_REQUESTED`，**安裝時自動授予，全程未跳出詢問**。

**原因**：Android 12（API 31）將藍牙改為執行期權限，
但**僅對 `targetSdk ≥ 31` 的 App 生效**。本 App 停在 `targetSdk 30`，
沿用舊模型——安裝即取得，使用者無從拒絕。

這是 MANIFEST 中「targetSdk 過舊會豁免 Android 11+ 隱私強化」
一說的**首個執行期實例**。

值得注意：`BLUETOOTH_SCAN` 可用於位置推定。
使用者拒絕了位置權限，但此路徑未被關閉。

## 觀測邊界

1. **未連接無人機。** 所有結論僅適用於「App 單獨執行、未連機」的狀態。
   連上無人機後行為可能完全不同（尤其是飛行資料上傳與 `libdreamDroneParser.so` 載入）。
2. **未登入帳號。** 註冊／登入流程（TC-L3-09）未執行，該路徑的流量未觀測。
3. **觀測窗約 30 分鐘**，其中定時取樣 90 秒。無法排除更長週期的行為。
4. 權限全部拒絕的情境下觀測。授予後行為需另行對照（已規劃）。
5. F04 的 pinning 行為**仍未取得** —— App 未發出任何 TLS 連線，無從觀察。

## 下一步

- [ ] 修改 `gamesir_lastTime` 觸發 GameSir 清單更新 → 一舉解 F02 存活性 + F04 pinning + TC-L3-04
- [ ] 以 `pm grant` 逐項授予權限，跑第二輪對照，找出哪些權限實際影響傳輸
- [ ] 連接無人機後重跑 native hook，觀察 `libdreamDroneParser.so` 與飛行資料路徑
- [ ] 執行 TC-L3-09（註冊登入），使用研究專用信箱
- [ ] 檢查是否有主動反分析邏輯（`/proc/self/maps` 掃描等），以區分「不相容」與「刻意偵測」
