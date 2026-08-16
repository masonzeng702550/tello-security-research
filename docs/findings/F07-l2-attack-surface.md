# F07 — L2 攻擊面評估（否定結果）與未被引用的資產

| 欄位 | 內容 |
|---|---|
| 編號 | F07 |
| 層級 | L2 同裝置惡意 App |
| 分類 | 攻擊面評估 |
| 嚴重度 | **Info** — 未發現可利用問題 |
| 受影響版本 | 1.3.0.0 / 1.6.4.0 / 1.6.8.0（三版比對） |
| 狀態 | 靜態已確認（不受方法抽取影響） |
| 新穎性 | 本研究新發現（否定結果） |

## 摘要

L2 層（同裝置的其他 App 能否攻擊本 App）的靜態盤點結果是**乾淨的**。
這是有意義的否定結果，應如實記錄。

同時發現三個**完全不被 dex 引用**的二進位資產，其中一個達 9.7 MB。

## TC-L2-02｜exported 元件

以 AndroidManifest 全量檢視三個版本：

| 版本 | `exported="true"` | service | receiver | provider |
|---|---|---|---|---|
| 1.3.0.0 | **0** | 4 | 0 | 1 |
| 1.6.4.0 | **0** | 4 | 0 | 1 |
| 1.6.8.0 | **0** | 4 | 0 | 1 |

- **無任何明示 `exported="true"` 的元件**
- 唯一隱含對外開放的是 `SplashActivity`（有 `intent-filter`，即啟動器 Activity）——
  這是每個 App 都必須有的，非缺陷
- 唯一的 `provider` 是 `android.support.v4.content.FileProvider`，
  明示 `exported="false"` 且 `grantUriPermissions="true"`（標準用法）
- **零個 broadcast receiver**

**判定：無未受保護的對外元件。三個版本一致。**

## TC-L2-03｜network security config

```
android:networkSecurityConfig    未設定
android:usesCleartextTraffic     未設定
```

targetSdk 30 的預設行為即**禁止明文流量**，且**無自訂 trust anchors、無網域例外**。

**判定：平台層設定乾淨。**

> 但這也意味著：若 App 有憑證 pinning，是**在程式碼中實作**
> （已定位到 `RYZEHttpsUtils`，見 F04），而非透過平台設定。
> 平台設定乾淨 ≠ TLS 驗證行為正確。

## TC-L2-07｜自訂 URL scheme

三個版本的 manifest 中**皆無任何 `android:scheme` 宣告**。

**判定：無 deep link 劫持面。**

## 附帶發現：三個未被 dex 引用的資產

| 檔案 | 大小 | 熵 (bits/byte) | 研判 | dex 字串池是否引用 |
|---|---|---|---|---|
| `assets/asr/common.jet` | **9,781,778** | 5.664 | 結構化資料，未加密 | ❌ **無** |
| `assets/af.bin` | 53,872 | 7.989 | 已加密／壓縮 | ❌ **無** |
| `assets/signed.bin` | 37,808 | 7.995 | 已加密／壓縮 | ❌ **無** |

### `assets/asr/common.jet` — 9.7 MB 的語音辨識模型？

```
magic  76 35 70 70              "v5pp"
接續   0bd0e78185b192ce6a2b18ada401866c    （32 字元十六進位，疑為 MD5）
熵     5.664 → 非加密，為結構化資料
```

`asr` = automatic speech recognition。**一支飛無人機的 App 打包 9.7 MB 的語音資源**，
且該資產佔 APK 總體積（30 MB）的近三分之一。

**但**：`common.jet`、`asr/`、`/asr` **皆不存在於 dex 字串池**
（唯一命中的 `.jet` 來自 `org.eclipse.jetty.alpn.ALPN` 字串，屬誤判）。

依 F03 的推論（字串池完好，字串不在池中 ⇒ 無方法引用），
**Java 層不會以此路徑開啟該檔案**。

已檢索但**未發現**任何主流語音 SDK 的類別：
`com.iflytek`、`com.baidu.speech`、`unisound`、`com.aispeech`、`com.mobvoi` 皆零命中。
（`msc` 的 65 次命中經上下文檢視後判定為二進位資料中的偶然位元組序列，非訊飛 MSC SDK。）

**三種可能**：
- (a) 建置殘留 — 曾經有語音功能，移除時漏掉 9.7 MB 資產
- (b) 由 native 程式碼載入 — 不經 Java 路徑
- (c) 位於被抽走的方法主體且路徑為執行期組成 — 但字串仍須在池中，故**此項不成立**

→ **(a) 最可能。** 若成立，代表建置流程長期未清理，
與 F04 的過期憑證、F01 的 native 殘留是同一類問題。

### `af.bin` / `signed.bin`

熵接近 8.0，為加密或壓縮資料。同樣不被 dex 引用。
`signed.bin` 的命名暗示與簽章相關，用途未知。
研判由 native 程式碼或加殼器使用。

## 整體判讀

L2 這一層**沒有找到可利用的問題**，manifest 衛生相當好——
無 exported 元件、無 receiver、無自訂 scheme、無明文流量例外。

**但同一份 manifest 與 assets 中，卻同時存在：**
- 指向不存在類別的 service 宣告（F01）
- 已失效的百度 API key（F01）
- 兩個無人載入的 `.so`（F01）
- 五張過期 5–8 年的 pinning 憑證（F04）
- 三個不被引用的資產，含一個 9.7 MB 的（本篇）

→ **對外攻擊面的設計是謹慎的，但建置流程的清理長期失修。**
這個對比本身值得寫進報告——它顯示問題不在安全意識，而在**維護流程**，
與「產品線已停售、App 不再維護」的背景一致。

## 觀測邊界

- 未做 **TC-L2-04 本地資料落地檢查**、**TC-L2-05 外部儲存**、
  **TC-L2-06 WebView 設定** —— 前兩者需實機；
  WebView 設定屬方法主體內的行為，**受 F03 的方法抽取所阻**
- exported 判定依 manifest 靜態宣告；未驗證執行期是否動態註冊 receiver
  （`registerReceiver` 屬方法主體，看不到）
- 未嘗試解析 `common.jet` 的內部格式

## 下一步

- [ ] 嘗試辨識 `common.jet` 的格式（`v5pp` magic 的來源）
- [ ] 以 Ghidra 檢視 native 庫是否引用 `af.bin` / `signed.bin` / `common.jet`
- [ ] 動態：hook `registerReceiver` 確認有無執行期註冊的對外接收器
- [ ] 動態：TC-L2-04 / 05 / 06
