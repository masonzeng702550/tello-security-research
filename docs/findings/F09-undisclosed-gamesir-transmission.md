# F09 — 未揭露的第三方傳輸：GameSir SDK 將裝置資訊送往中國伺服器，且無憑證 pinning

| 欄位 | 內容 |
|---|---|
| 編號 | F09 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 隱私 / 揭露 |
| 嚴重度 | **High** |
| 受影響版本 | 全部（1.3.0.0 – 1.6.8.0，`com.xj.gamesir` 六版皆存在） |
| 狀態 | **T3 — payload 已解密取得** |
| 新穎性 | 本研究新發現 |
| 證據 | `flow:TC-L3-01_20260817-1549.flow`（`~d vgabc`） |

## 摘要

Tello App 在啟動時，會將**裝置品牌、型號、套件名稱與 SDK 版本**
以明文表單送往 `https://client.vgabc.com/clientapi/`
——該端點位於**中國境內阿里雲**（120.78.95.33，RDAP: ALISOFT，CN），
由 **GameSir／小雞科技** 的 SDK（`com.xj.gamesir`）發起。

**此第三方在廠商的任何一版隱私政策中皆未被揭露。**

同時，該連線**未實施憑證 pinning**——本研究的 MITM 憑證被直接接受。
對照之下，同一次啟動中對 `mydjiflight.dji.com` 的連線**pinning 生效並拒絕了 MITM**。

## 證據：實際擷取的請求

```http
POST https://client.vgabc.com/clientapi/
User-Agent: xjappstore
Charset: UTF-8
Content-Type: application/x-www-form-urlencoded
encoding: UTF-8
Host: client.vgabc.com
Connection: Keep-Alive
Accept-Encoding: gzip
Content-Length: 110

model:      appstore
action:     connectmodel
brand:      google
device:     Pixel 6 Pro
package:    com.ryzerobotics.tello
sdkversion: 5

<< 200 OK 379b
Server: nginx
Date: Mon, 17 Aug 2026 14:53:53 GMT
```

回應內容為 GameSir 手把型號清單（JSON，含 `driveName` / `keyName` / `vid` / `pid`）。

`User-Agent: xjappstore` 中的 `xj` 即**小雞（xiaoji）**，與
`com.xj.gamesir.sdk` 套件路徑及 `xjdl.vgabc.com` 子網域一致（見 F02）。

## 送出的欄位

| 欄位 | 值 | 性質 |
|---|---|---|
| `brand` | `google` | 裝置品牌 |
| `device` | `Pixel 6 Pro` | 裝置型號 |
| `package` | `com.ryzerobotics.tello` | 呼叫端套件 |
| `model` | `appstore` | SDK 內部參數 |
| `action` | `connectmodel` | 請求類型 |
| `sdkversion` | `5` | SDK 版本 |

**未見** Android ID、MAC 位址、IMEI、廣告 ID、位置座標、帳號資訊。

→ 就蒐集範圍而言相對節制，**問題不在蒐集了多少，而在完全未揭露**。

## 揭露落差：全數版本、全數語言皆無揭露

檢索四個版本的中文政策與英文政策：

| 版本 | `gamesir` | `小鸡` | `小雞` | `vgabc` | `xj` |
|---|---|---|---|---|---|
| 1.3.0.0 | 0 | 0 | 0 | 0 | 0 |
| 1.6.0.1 | 0 | 0 | 0 | 0 | 0 |
| 1.6.4.0 | 0 | 0 | 0 | 0 | 0 |
| 1.6.8.0 | 0 | 0 | 0 | 0 | 0 |
| 英文版（六版皆同） | 0 | 0 | 0 | 0 | 0 |

而 1.6.4.0 的**附件一「第三方 SDK 說明」**——廠商做過最詳盡的一次揭露——
完整內容僅有兩項：

```
第三方SDK名称 | 使用目的     | 信息类型                              | 隐私政策链接
Bugly        | 崩溃信息收集  | 设备信息：Android id信息               | bugly.qq.com
BaiduLBS     | 定位服务      | 设备信息：Android id信息、设备MAC 地址  | lbsyun.baidu.com
```

**GameSir SDK 不在其中。** 且該 SDK 存在於全部六個版本
（dex 字串 `Lcom/xj/gamesir` 穩定命中 159 次，見 F01），
即使在 1.6.8.0 移除百度與騰訊之後仍然保留。

## 差異化的憑證 pinning（F04 的答案）

同一次啟動、相隔 91 毫秒的兩個連線：

```
[22:53:50.124] server connect mydjiflight.dji.com:443 (13.249.74.123:443)
[22:53:50.215] server connect client.vgabc.com:443   (120.78.95.33:443)

[22:53:50.373] mydjiflight.dji.com
               Client TLS handshake failed.
               The client does not trust the proxy's certificate
               (ssl/tls alert certificate unknown)
               → 拒絕 MITM，pinning 生效 ✅

127.0.0.1:56936: POST https://client.vgabc.com/clientapi/
               → 接受 MITM 憑證，請求完整送出並解密 ❌
```

**判定**：

- App **確實實作了憑證 pinning**，且對 `mydjiflight.dji.com` **有效**
  → 印證 F04 所定位的 `RYZEHttpsUtils`（`X509TrustManager` 由憑證串流建構）確有作用
- 但該保護**未套用於 `client.vgabc.com`**
  → 第三方 SDK 走自己的網路堆疊，不受 App 的 pinning 設定約束

### 這對 F04 的意義

F04 記錄了「內建 pinning 憑證全數過期 5–8 年」，並列出三種可能。
本次觀測**排除了最嚴重的一種**：憑證驗證並未整體停用——
對自家端點是有效的。

但同時揭示了一個 F04 未預期的面向：**pinning 的覆蓋範圍不完整**。
第三方 SDK 的連線繞過了該保護。

## 攻擊面意義

`client.vgabc.com` 的連線無 pinning，代表：

- 位於同一網路的攻擊者可在該連線上進行中間人
- 可觀察到裝置品牌與型號（低敏感度）
- **可竄改回應內容**——回應是手把型號清單 JSON，
  由 SDK 解析。若解析邏輯不健壯，構成一條可控輸入路徑

> 本研究**未測試**回應竄改的後果。上述為攻擊面描述，非已驗證的漏洞。

## 觸發條件

該請求**非每次啟動必發**，受節流控制。
`shared_prefs/gamesir_config.xml`：

```xml
<long name="gamesir_lastTime" value="…" />      ← 上次檢查時間戳
<int name="GAMESIR_CHECK_LIMIT" value="0" />
```

本次係將 `gamesir_lastTime` 改為 `0` 後重啟 App 才觸發。
首次啟動（F08）未觀測到，即因該節流機制。

> **方法論註記**：若僅做一次首次啟動觀測，會得出「App 不連任何後端」的結論
> ——那正是 F08 的結果，且該結果本身正確。
> 但**節流機制會使短時間的觀測系統性地低估實際傳輸**。
> 檢查 `shared_prefs` 中的時間戳／計數器並主動重置，
> 應列為此類研究的標準步驟。

### 使用者無法以權限設定阻止此上報（2026-08-17 A/B 實測）

已完成受控 A/B 測試（見 **F11**）：在
`ACCESS_FINE_LOCATION`、`ACCESS_COARSE_LOCATION`、`READ_MEDIA_IMAGES`、
`READ_MEDIA_VIDEO`、`READ_EXTERNAL_STORAGE`、`WRITE_EXTERNAL_STORAGE`
**六項全部拒絕**的情況下，此請求**照樣送出**，
且 payload 與六項全部授予時**逐位元組相同**。

原因是所送欄位（廠牌、機型、套件名、SDK 版本）
皆可由 `android.os.Build` 取得，**不需要任何危險權限**。

→ **這強化本findings的嚴重度判定**：
   一個未經揭露的境外上報，**不受任何使用者可見的權限控制項所節制**。
   使用者既不知道它存在，也無法透過系統設定阻止它。

## 觀測邊界

- 僅觀測到 **一次** 該請求。是否有其他觸發條件（連接手把、特定操作）未測
- **未連接無人機**，飛行相關的傳輸路徑尚未觀測
- 僅在 `brand=google` / `Pixel 6 Pro` 的裝置上測試；
  不同裝置是否送出更多欄位未知
- `mydjiflight.dji.com` 的 pinning 使其 payload **無法取得**，
  該端點送出什麼仍未知（需 Frida 繞過 pinning，屬後續工作）
- 未驗證 `client.vgabc.com` 的回應是否可被竄改利用

## 下一步

- [ ] 以 Frida 繞過 pinning，取得 `mydjiflight.dji.com` 的 payload（該端點六版皆存在）
- [ ] 觀察連接 GameSir 手把時是否有額外傳輸
- [ ] 檢查其他 `shared_prefs` 節流欄位，是否還有未被觸發的端點
- [ ] 連接無人機後重測，觀察飛行資料路徑
- [ ] 確認 `client.vgabc.com` 回應的解析邏輯是否為可控輸入路徑
