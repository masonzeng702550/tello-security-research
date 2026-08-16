# F04 — 內建的 pinning 憑證素材大量過期，並暴露一個未揭露的端點網域

| 欄位 | 內容 |
|---|---|
| 編號 | F04 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 設計缺陷 |
| 嚴重度 | **待定** — 取決於 pinning 是否實際強制執行 |
| 受影響版本 | 全部（1.3.0.0 – 1.6.8.0） |
| 狀態 | 靜態已確認 / 行為待驗證 |
| 新穎性 | 本研究新發現 |

## 摘要

App 的 `assets/` 內建憑證作為 TLS pinning 素材。
**在 2024 年釋出的 1.6.8.0 中，所有 leaf（伺服器）憑證均已過期，
最久的逾期 8 年。**

同時，其中一組憑證指向 **`*.aasky.net`** ——
這個網域**完全不在 dex 硬編碼網域清單中**，是 F02 端點盤點的漏網之魚。

## 證據：1.6.8.0 內建憑證狀態

`lib:1.6.8.0:assets/*.cer|*.crt|*.pem`

### Leaf 憑證（全部過期）

| 檔案 | Subject | 簽發者 | 到期 | 逾期 |
|---|---|---|---|---|
| `aasky-net2.crt` | `CN=*.aasky.net` | AlphaSSL CA - SHA256 - G2 | 2018-06-07 | **8 年** |
| `dji-com2.crt` | `CN=*.dji.com` | AlphaSSL CA - SHA256 - G2 | 2018-09-04 | **8 年** |
| `aasky-net.cer` | `CN=*.aasky.net` | Go Daddy Secure CA - G2 | 2020-05-24 | **6 年** |
| `dji-com.cer` | `CN=*.dji.com` | Go Daddy Secure CA - G2 | 2020-08-03 | **6 年** |
| `ryzerobotics.com.crt` | `CN=*.ryzerobotics.com` | Go Daddy Secure CA - G2 | 2020-12-17 | **5 年** |

### 根 CA（有效）

`aasky-net-new2.cer` 實為 Go Daddy Root CA G2（2038 到期）——
**檔名誤導**，命名為 aasky 但內容是根憑證。

1.6.8.0 相較舊版**新增**一批根 CA：
```
amazon_root_ca1..4.pem            ← 對應 CloudFront 遷移
DigiCert_Global_Root_CA.pem / _G2.pem
GlobalsignRootR3-2029.pem / R6-2034.pem
entrust_g2_ca.pem
USERTrust_RSA_Certification_Authority.pem
godaddy_root_certificate_authority_g2.pem
godaddy_secure_certificate_authority_g2.pem
```

**研判**：pinning 策略由「pin 伺服器 leaf 憑證」改為「pin 根／中繼 CA」，
但**舊的 leaf 憑證未一併移除**。

## 判讀

### 1. 過期 leaf 憑證的三種可能

若 App 仍以這些 leaf 憑證做嚴格 pinning，對應連線**必然失敗**（憑證早已輪替）。
App 仍可正常使用，所以至少其一成立：

- **(a) 已改用根 CA pinning**，leaf 檔案是未清除的殘留 → 最可能，屬衛生問題
- **(b) pinning 邏輯在驗證失敗時 fallback 到系統信任鏈** → 等同無 pinning
- **(c) 憑證驗證整體被停用** → **可被中間人利用，嚴重**

**(b) 與 (c) 都是實質資安問題**，必須以動態測試分辨。

### 2. 與 F02 的模式呼應

F02 已發現 `client.vgabc.com` 的憑證自 2020-10-16 到期後未再簽發，
而 App 硬編碼 `https://` URL。

加上本findings，**憑證素材過期是全 App 範圍的模式，不是單點疏漏**。
這指向建置流程缺乏憑證有效期檢查。

### 3. `aasky.net` — 已查明：**DJI 的後端服務網域**

- 有**三個**憑證檔案專為此網域準備（兩張 leaf + 一張命名誤導的根）
- 出現在**全部六個版本**
- **但 dex 硬編碼網域清單中完全沒有它**

#### 憑證透明度（crt.sh，64 張憑證，9 個子網域）

```
aasky.net / www.aasky.net / *.aasky.net
flighthub-pe.aasky.net          www.flighthub-pe.aasky.net
ag-rtk.aasky.net                www.ag-rtk.aasky.net
ag-rtk-alg.aasky.net            www.ag-rtk-alg.aasky.net
```

**子網域名稱直接說明歸屬**：

| 子網域 | 對應的 DJI 產品 |
|---|---|
| `flighthub-pe` | **DJI FlightHub** — DJI 的機隊管理與飛行資料平台 |
| `ag-rtk` / `ag-rtk-alg` | **AG = Agras（DJI 農業無人機）＋ RTK 定位服務**；`alg` 疑為 algorithm |

另有公開來源將 `acbe.aasky.net` 與 `adhoc-staging.aasky.net`
列入 DJI GO 4 的韌體更新網域清單。

→ **`aasky.net` 是 DJI 的後端服務網域，不是 Ryze 的。**

#### 網域活躍度與目前解析（2026-08-16）

憑證簽發自 **2015-06-23 至 2026-08-05**，2026 年已簽發 9 張 → **持續營運中**。

| 主機 | 解析 | 歸屬 |
|---|---|---|
| `www.aasky.net` | `d2scvg9scalkna.cloudfront.net` → 65.9.180.x | Amazon CloudFront |
| `ag-rtk.aasky.net` | 114.55.144.58 | **ALISOFT（阿里雲），CN** |
| `ag-rtk-alg.aasky.net` | 114.55.144.58 | **ALISOFT（阿里雲），CN** |
| `flighthub-pe.aasky.net` | 無解析 | 已退役 |
| `acbe` / `adhoc-staging` | 無解析 | 已退役 |
| `aasky.net`（裸網域） | 無 A 記錄 | — |

> 網域註冊資訊未取得——RDAP 查詢連續失敗（研判為查詢頻率限制）。待補。

#### 判讀

**Tello App 內建了 DJI 後端基礎設施網域的 pinning 憑證。**
這與 `mydjiflight.dji.com`（六版皆存在）相互印證：
Tello App 預期會與 DJI 的後端通訊，而非只與 Ryze 自家服務通訊。

但 `aasky.net` **完全不出現在 dex 硬編碼字串中**。三種可能：
- (a) URL 於執行期組出（例如由設定檔或伺服器回應決定）
- (b) 相關程式碼位於加密的 `ijiami.ajm`（見 F03）
- (c) 該路徑已廢棄，憑證是未清除的殘留

考量兩張 `*.aasky.net` leaf 憑證分別於 2018 與 2020 過期、
且 `flighthub-pe` 等子網域已無解析，**(c) 的可能性最高**。
但 (b) 無法以靜態方法排除。

**這證實了 F02 的觀測邊界警告**：靜態 dex 字串抽取**無法**產出完整端點清單。
本專案的端點盤點必須至少涵蓋三個來源——
dex 字串、pinning 憑證素材、以及（最終）動態流量。

## pinning 實作已定位，但行為無法靜態取得

反編譯 1.6.8.0 後找到 App 自有的 TLS 處理類別：

| 混淆後類別 | 原始檔名 |
|---|---|
| `com/ryzerobotics/tello/common/c/d` | **`RYZEHttpsUtils.java`** |
| `com/ryzerobotics/tello/common/c/e` | **`RYZEStatisticsHttpsUtils.java`** |

`RYZEHttpsUtils` 的結構（欄位與方法簽章不受方法抽取影響）：

```smali
.field private static b:Lokhttp3/OkHttpClient;
.method public static a()Lcom/ryzerobotics/tello/common/c/d;      單例
.method private a([C)Ljava/security/KeyStore;                     由密碼建 KeyStore
.method private varargs a([Ljava/io/InputStream;)Ljavax/net/ssl/X509TrustManager;
                                                                   由憑證串流建 TrustManager
.method public b()Lokhttp3/OkHttpClient;                          建構 HTTP client
```

**方法簽章明確顯示 App 自行建構 X509TrustManager，且輸入為憑證檔的 InputStream**
——與 `assets/` 中那批 `.cer`/`.crt`/`.pem` 相符。

### 但方法主體是空的

```smali
.method public b()Lokhttp3/OkHttpClient;
    .locals 1
    const/4 v0, 0x0
    return-object v0        ← 只有 return null
    nop
.end method
```

`a([Ljava/io/InputStream;)` 佔 300 行，內容為 `return null` + 約 290 個 `nop`。

**App 的 89% 方法主體已被愛加密抽取（見 F03）。**
因此**無法靜態判斷**：
- 憑證從何處載入、載入哪幾張
- `checkServerTrusted` 的實作邏輯
- 驗證失敗時是否 fallback 到系統信任鏈
- 過期的 leaf 憑證是否真的被使用

### 附帶確認

- 憑證檔名（`aasky-net.cer` 等）**存在於 dex 字串池**，
  代表**確實有某個方法引用它們**（依 F03 的推論）——只是那個方法主體看不到。
  → **這些憑證不是純粹的死檔案，有程式碼引用。**
- 第三方的 `com/zhy/http/okhttp/https/HttpsUtils` **無任何呼叫**，為未使用的函式庫程式碼。
- 平台層 `networkSecurityConfig` **未設定**（見 F07）→ pinning 若存在，純由程式碼實作。

## 觀測邊界

- 僅確認**憑證檔案存在、已過期、且被某個方法引用**。
  **未確認**實際的驗證行為——受 F03 的方法抽取所阻。
- 「逾期年數」以 2026-08 為基準計算。
- 未分析 `RYZEStatisticsHttpsUtils`（用於統計上報的獨立 client）與主 client 的差異。

## 下一步

- [x] ~~追查 `aasky.net`~~ → 已查明為 DJI 後端服務網域（見上）
- [ ] 補 `aasky.net` 的網域註冊資訊（RDAP 被限流，改日重試或改用 whois）
- [ ] 反編譯 pinning 實作：搜尋 `TrustManager` / `SSLContext` /
      `CertificatePinner` / `checkServerTrusted` 的自訂實作
- [ ] **動態測試（決定性）**：掛 mitmproxy 自簽憑證
  - 連線失敗 → pinning 有效，屬情況 (a)
  - 連線成功 → 情況 (b) 或 (c)，**升級為可利用的中間人風險**
- [ ] 逐一測試各端點，pinning 行為可能因端點而異
