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

### 3. `aasky.net` — 端點盤點的漏網之魚

- 有**三個**憑證檔案專為此網域準備（兩張 leaf + 一張命名誤導的根）
- 出現在**全部六個版本**
- **但 dex 硬編碼網域清單中完全沒有它**
- `www.aasky.net` 目前解析至 CloudFront（`d2scvg9scalkna.cloudfront.net`），**服務存活**
- `aasky.net` 本身無 A 記錄

**這證實了 F02 的觀測邊界警告是對的**：靜態 dex 字串抽取**無法**產出完整端點清單。
URL 可能於執行期組出，或位於加密的 `ijiami.ajm`（見 F03）。

會為一個網域準備三張 pinning 憑證，代表它**曾經是（或仍是）重要的通訊對象**。
用途待查。

## 觀測邊界

- 僅確認**憑證檔案存在且已過期**。**未確認** App 實際如何使用它們——
  可能載入、可能忽略、可能只用根 CA。
- 未反編譯 pinning 實作邏輯（相關程式碼可能位於 `ijiami.ajm`）。
- 「逾期年數」以 2026-08 為基準計算。

## 下一步

- [ ] **追查 `aasky.net`** — RDAP、crt.sh、被動 DNS；確認與 Ryze/DJI 的關係
- [ ] 反編譯 pinning 實作：搜尋 `TrustManager` / `SSLContext` /
      `CertificatePinner` / `checkServerTrusted` 的自訂實作
- [ ] **動態測試（決定性）**：掛 mitmproxy 自簽憑證
  - 連線失敗 → pinning 有效，屬情況 (a)
  - 連線成功 → 情況 (b) 或 (c)，**升級為可利用的中間人風險**
- [ ] 逐一測試各端點，pinning 行為可能因端點而異
