# 文獻回顧與前人研究

> 目的：釐清**哪些已經被做過**，避免重做；並定位本專案的增量貢獻。
> 狀態標記：`[已讀]` / `[待讀]` / `[待驗證]`

---

## A. 最重要的方法論母本：DJI GO 4 Android App 分析（2020）

這是與本專案**最直接相關**的前人研究。Tello App 由 Shenzhen Ryze Tech 發行、DJI 提供技術支援，
兩者是否共用同一套 SDK／後端／更新機制，是本專案最有價值的研究問題。

### Synacktiv, "DJI Android GO 4 application security analysis" (2020-07) `[待讀]`
https://www.synacktiv.com/en/publications/dji-android-go-4-application-security-analysis

四項核心發現：

1. **自我更新繞過 Google Play** — App 內建更新機制可在不經 Play 商店審查、不需使用者同意的情況下安裝新程式碼。
2. **Weibo SDK 可下載並安裝任意 App**，且該 SDK 在過程中蒐集使用者個資回傳微博。
3. **MobTech（Mob SDK）** — 4.3.36 版之前內含中國分析商 MobTech 的 SDK，蒐集並回傳個資。
4. **反分析技術** — 反除錯、混淆、動態解密與加殼，手法近似惡意程式。

DJI 回應：2020-07-31 更新 GO 4，移除 Weibo SDK，並把自動更新導回 Google Play。

### GRIMM, "DJI Privacy Analysis Validation" (2020-07) `[待讀]`
https://blog.grimm-co.com/2020/07/dji-privacy-analysis-validation.html

第三方獨立複現 Synacktiv 的結果（靜態＋動態）。**複現方法論值得直接借用。**

### 相關報導與廠商回應 `[待讀]`
- DJI 官方聲明：https://www.dji.com/newsroom/news/dji-statement-on-further-misleading-claims-about-app-security
- SecurityWeek：https://www.securityweek.com/chinese-drone-giant-dji-responds-disclosure-android-app-security-issues/
- Threatpost：https://threatpost.com/dji-drone-app-riddled-with-privacy-issues-researchers-allege/157730/
- Synacktiv, DJI Pilot 分析（另一支 App）：https://www.synacktiv.com/en/publications/dji-pilot-android-application-security-analysis-1

> **本專案的關鍵問題**：Tello App（Ryze 發行，非 DJI 品牌）是否也存在上述四項模式？
> 若**有** → 顯示問題延伸到子品牌，且 2020 事件後未被修正 → 高價值發現。
> 若**沒有** → 也是有意義的否證結果，且可對比說明兩條產品線的治理差異。
> 這是目前看起來**最扎實的研究骨架**。

---

## B. Tello 控制通道安全（L1 近場攻擊）

此領域**已有相當多前人成果**，本專案不宜把重心放這裡，但需要複現以建立基準。

### 學術
- **"Analysis of Control Channel Cybersecurity of the Consumer-Grade UAV by the Example of DJI Tello"** `[待讀]`
  https://www.researchgate.net/publication/351750974_
  控制通道安全的正式分析，本專案 L1 的主要引用來源。
- **SoK: Security and Privacy in the Age of Drones** (arXiv:1903.05155) `[待讀]` — 領域綜述，用來定位研究缺口。
- **Security Requirements of Commercial Drones for Public Authorities by Vulnerability Analysis of Applications** (arXiv:1909.02786) `[待讀]`
  ← 標題就是「透過 App 漏洞分析」，方法論高度相關。

### 業界／實務
- **Alias Robotics, "Ryze Tello Drone Pentesting: Security Case Study"** `[待讀]`
  https://aliasrobotics.com/case-study-pentesting-tello.php
- **Eyal Asulin, "Exploit and Takeover a DJI Tello Drone"** `[待讀]`
  https://medium.com/@eyalasulin.9/exploit-and-takeover-a-dji-tello-drone-9f69c18f6a3a

### 已被確立的事實（不需重新發現，但需複現驗證）`[待驗證]`
- Tello 自建開放式 Wi-Fi AP，**無密碼**，且不強制使用者設定密碼、不做裝置綁定。
- UDP `8889` 命令、`8890` 狀態、`11111` 視訊，**明文、無認證**。
- 送出 `command` 即被無人機標記為控制端。
- **關鍵**：已有第二台裝置連線時無人機仍運作 → 攻擊者可宣告自己為控制端接管，
  而原操作者的官方 App 因「已有人連線」而失去控制。
- 取得 Wi-Fi 密碼後（若使用者有設）可用 de-auth 攻擊踢掉原操作者再接管。

---

## C. 隱私評測（L3 資料主權）

### Mozilla Foundation, *Privacy Not Included* — Ryze Tello `[待讀]`
https://www.mozillafoundation.org/en/privacynotincluded/ryze-tello/

重點（需回到 Ryze 隱私權政策原文查證）：
- 蒐集姓名、電子郵件、通訊地址、行動電話號碼、**位置資料**。
- **明示可能將個資分享給 DJI**。
- 對是否販售使用者資料**未揭露**。
- 保留條款寬鬆（備份、封存、防詐、分析、法遵…）。

### 一手來源 `[待讀]`
- Ryze 隱私權政策：https://www.ryzerobotics.com/policy （2026-08-16 直接抓取失敗，需用瀏覽器取得並存檔）
- **務必存檔當下版本 + 存取日期**，政策會改。

> **注意**：隱私權政策寫了什麼 ≠ App 實際做了什麼。
> 本專案的價值就在於用流量證據去**比對政策宣稱與實際行為的落差**。

---

## D. 研究缺口與本專案定位（初稿，待文獻讀完後修訂）

| 缺口 | 說明 | 本專案是否處理 |
|---|---|---|
| Tello App 本身的靜態／隱私分析 | 前人聚焦在**控制通道**與 **DJI 主品牌 App**，Ryze Tello App 本體的 SDK 清冊與資料流分析少見 | ✅ 主軸 |
| 多版本縱向分析 | 未見有人比對 Tello App 2019→2024 的 SDK／權限／端點演變 | ✅ 主軸 |
| 離線落地—上線補傳 的時間差路徑 | 連無人機時手機無網路，遙測如何回傳？前人未見探討 | ✅ 主軸 |
| 停售後的後端存續狀態 | 產品線已停售，後端還在嗎？舊 App 是否仍嘗試連線？ | ✅ 附帶 |
| 控制通道漏洞 | 已被充分研究 | ⚠️ 僅複現，作為基準 |

---

## 引用紀律

- 每個結論都要能指回：**原始檔案路徑 + 行號**（靜態）或 **pcap 檔 + 封包編號**（動態）。
- 引用前人研究時明確區分：「前人已證實」 vs 「本研究複現確認」 vs 「本研究新發現」。
- 未經自己驗證的二手說法，一律標 `[待驗證]`，不得直接當成結論。
