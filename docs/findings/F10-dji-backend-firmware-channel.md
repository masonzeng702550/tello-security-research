# F10 — DJI 後端與韌體更新通道：pinning 已繞過，完整協定取得

| 欄位 | 內容 |
|---|---|
| 編號 | F10 |
| 層級 | L3 供應鏈與資料主權 / L1 韌體通道 |
| 分類 | 行為觀測 |
| 嚴重度 | Info — 未發現可利用弱點，但揭露完整攻擊面 |
| 受影響版本 | 1.6.8.0 |
| 狀態 | **T3 — payload 已解密取得** |
| 對應測試 | TC-L3-02、TC-L3-04，並為 TC-L1-07 提供關鍵前提 |
| 證據 | `flow:TC-L3-04_20260817-2320.flow` |

## 摘要

以 Frida 繞過憑證 pinning 後，取得 App 與 DJI 後端的完整通訊內容。
本findings記錄該通道的協定、送出的欄位、以及**韌體更新通道的實際結構**。

三項對其他 findings 有直接影響的觀察：

1. **台灣裝置在網路層送出 `language: zh_cn`** —— 於協定層面印證 F05
2. **發現 `terra-2-g-a.djicdn.com`，該端點不在任何靜態清單中** —— 再次印證 F02 的觀測邊界
3. **韌體設定檔為 PGP 簽章** —— 改變 TC-L1-07 的問題設定

## 繞過方法：延遲掛載

先前兩次嘗試皆因 Frida 的 Java hook 與加殼器衝突而失敗
（App 在 `LoadedApk.makeApplicationInner` 崩潰，見 F08）。

**成功的做法是延遲掛載**：

```
t=0       frida spawn
t≈1–2s    愛加密完成 dex 還原與 Application 建立
t=2.5s    ← 此時才 Java.perform 掛載 TLS hook
t≈4–5s    App 發出首波網路請求，已被攔截
```

腳本：`dynamic/frida/unpin-targeted.js`（`DELAY_MS = 2500`）

掛載的攔截點（刻意只取三處，壓低對加殼 App 的擾動）：

| 攔截點 | 作用 |
|---|---|
| `javax.net.ssl.SSLContext.init` | 以寬鬆 TrustManager 取代 App 提供的 |
| `com.android.org.conscrypt.TrustManagerImpl.verifyChain` | Android 7+ 的實際鏈驗證落點 |
| `okhttp3.CertificatePinner.check` / `com.squareup.okhttp` | OkHttp 的明示 pin |

> **方法論**：對加殼 App 使用通用的 `frida-multiple-unpinning` 是不可行的——
> 那類腳本 hook 數十個類別，必然撞上殼的初始化。
> **針對性 + 延遲掛載**是可行解。

## 端點一：`mydjiflight.dji.com/getfile/getallfile`

```http
POST https://mydjiflight.dji.com/getfile/getallfile
User-Agent: Mozilla/5.0 (Linux; Android 13; Pixel 6 Pro Build/TQ3A.230901.001; wv)
            AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0
            Chrome/109.0.5414.123 Mobile Safari/537.36 TELLO-Android
Content-Type: application/x-www-form-urlencoded
Content-Length: 81

signature:  c9f73806a7ed5da64fa7f13acee4fa6c
product_id: wm004
language:   zh_cn
token:      (空)

<< 200 OK 2.4k  application/json
   Via: 1.1 …cloudfront.net (CloudFront)
   X-Kong-Upstream-Latency: 4          ← Kong API gateway
   X-Amz-Cf-Pop: SFO53-P8
```

回應為韌體版本清單，含各版本的 `release_note`（簡體中文）與釋出日期。

## 端點二：`mydjiflight.dji.com/getfile/configpath`

```http
POST https://mydjiflight.dji.com/getfile/configpath

product_version: 01.01.0083
signature:       b18dd9bafa4c51f5bc9dd1140c323549
product_id:      wm004
token:           (空)

<< 200 OK 196b  application/json
```

回應含韌體設定檔的下載 URL（見端點三）。

## 端點三：`terra-2-g-a.djicdn.com` — 韌體檔案下載

**此端點不存在於 dex 字串池、不存在於 pinning 憑證、不存在於 manifest。**
僅由 `configpath` 的回應動態提供，**只有動態分析能發現**。

```http
GET https://terra-2-g-a.djicdn.com/1546577435024199aad91154298e6ca7/
    a5c5qa1uvz0il0zs7yoble3k/wm004edu_0000_v02.05.0119_20220507.pro.cfg.sig
    ?auth_key=1786987227-1786980027204-0-201ad37f051dded8bd5e726456c34305
User-Agent: okhttp/3.3.1

<< 200 OK 518b
   Server: Tengine                            ← 阿里巴巴的 nginx 分支
   Content-Type: application/pgp-signature    ← PGP 簽章檔
   x-oss-request-id: 6A83264B19FB12F2BAEBC413
   x-oss-cdn-auth: success                    ← auth_key 已通過驗證
   x-oss-object-type: Normal
```

另有一筆 `MYpgbA2TgscJ1gMUB5iAwQE6.sig`（同一 CDN）。

### 基礎設施分工

| 用途 | 服務 | 供應商 |
|---|---|---|
| API（`mydjiflight.dji.com`） | CloudFront + Kong gateway | **Amazon AWS** |
| 韌體／設定檔（`terra-*.djicdn.com`） | Tengine + OSS | **阿里雲（Alibaba Cloud）** |

DJI 的 CDN 實際由阿里雲 OSS 承載，API 層則在 AWS。

## 韌體更新清單（對 TC-L1-07 的關鍵前提）

同一工作階段擷取到的韌體 manifest：

```xml
<dji>
  <device id="wm004edu">
    <firmware formal="02.05.0119">
      <release version="02.05.0119"
               antirollback="0" antirollback_ext="cn:0"
               enforce="0" enforce_ext="cn:0"
               enforce_time="2018-01-01T09:39:35+00:00"
               from="2018/01/01" expire="2024/01/01">
        <module id="0802" version="02.05.01.19" group="ac"
                size="7209032"
                md5="6742926f69f877e0337607e1c0aa3612">
          wm004edu_0802_v02.05.01.19_20220507.pro.fw.sig
        </module>
      </release>
    </firmware>
  </device>
</dji>
```

### 可讀出的資訊

| 欄位 | 值 | 意義 |
|---|---|---|
| `device id` | `wm004edu` | Tello EDU 的產品代號（本機為 `wm004`） |
| 檔名副檔 | `.pro.fw.sig` | **韌體帶簽章** |
| `Content-Type` | `application/pgp-signature` | 簽章格式為 PGP |
| `md5` | 提供 | 完整性校驗值隨清單下發 |
| **`antirollback`** | **`0`** | **防降級未啟用** |
| **`enforce`** | **`0`** | **未強制升級** |
| `expire` | `2024/01/01` | **該 release 標記已過期** |

### 這如何改變 TC-L1-07 的問題設定

原測試案例問「韌體升級封包是否有簽章驗證」。
現在已知**韌體確實帶 PGP 簽章**，因此正確的問題變成：

1. **簽章驗證在何處執行**——App 端、無人機韌體端、或兩者？
2. **`antirollback="0"` 的實際效果**——能否推入舊版韌體？
3. 若 App 端不驗、僅無人機驗，則 App 側的 MITM 無法直接注入韌體
4. `auth_key` 是 CDN 層的存取控制，**非完整性保護**

> ⚠️ 本findings**未測試**任何韌體注入。上述為攻擊面分析，非已驗證的漏洞。
> 韌體測試具有損毀裝置的風險，且僅有一台機器，
> 依 `03-ethics-legal.md` 應排在最後並需備援機器。

## 送出欄位的盤點（TC-L3-04）

App 向 DJI 後端送出的欄位：

| 欄位 | 內容 | 性質 |
|---|---|---|
| `product_id` | `wm004` | 產品型號 |
| `product_version` | `01.01.0083` | 韌體版本 |
| `language` | **`zh_cn`** | 語言（見下） |
| `signature` | MD5 樣式字串 | 請求簽章 |
| `token` | 空 | 未登入 |
| User-Agent | Android 版本、機型、**精確建置編號**、Chrome 版本 | 裝置指紋 |

**未見**：Android ID、MAC 位址、IMEI、廣告 ID、GPS 座標、帳號識別。

→ 就個資蒐集而言，此通道相當節制。裝置指紋主要來自 User-Agent，
   且為 WebView 標準格式，非刻意蒐集。

## `language: zh_cn` — 於協定層印證 F05

測試裝置的 `persist.sys.locale = zh-Hant-TW`（繁體中文，台灣），
但 App 在網路請求中送出的是 **`language: zh_cn`**（簡體中文）。

這與 F05 的三項觀察一致，並提供了**網路層的獨立佐證**：

| 層級 | 觀察 |
|---|---|
| 官網（F05） | 台灣區頁尾標「繁體中文」，實際供應簡體內文 |
| App 介面（F08） | 協議標題繁體，條款內文簡體 |
| **網路協定（本findings）** | **送出 `language: zh_cn`** |

→ 三個獨立層級一致顯示：**台灣使用者在系統中被歸類為簡體中文使用者。**

伺服器回應的 `release_note` 也僅有 `zh_cn` 一種語言。

## 觀測邊界

- 僅觀測 **未連接無人機、未登入帳號** 的狀態。
  `token` 為空，登入後的請求可能攜帶更多欄位（TC-L3-09 未執行）
- 未測試 `report.ryzerobotics.com`、`chatsupport.*`、`aasky.net` ——
  本次工作階段這些端點**未被觸發**
- **未驗證 `signature` 欄位的產生方式**，故無法判斷請求偽造的難度
- **未下載完整韌體檔**（僅取得 `.cfg.sig`），未驗證簽章鏈
- pinning 繞過依賴 Frida，**非 App 本身的弱點**——
  真實攻擊者需先取得裝置的程式碼執行權限

## 下一步

- [ ] 執行 TC-L3-09（註冊登入），觀察 `token` 非空時的請求差異
- [ ] 分析 `signature` 欄位的產生邏輯（可能在被抽取的方法主體中，需 hook 求解）
- [ ] 連接無人機後重測，觀察飛行資料是否經此通道上傳
- [ ] 觸發其餘端點（`report.ryzerobotics.com` 等）並比對 pinning 行為
- [ ] TC-L1-07：在確認有備援機器後，分析 `.pro.fw.sig` 的簽章結構
