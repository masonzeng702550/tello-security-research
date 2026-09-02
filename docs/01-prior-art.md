# 前人研究盤點與缺口定位

> 目的：釐清**哪些已經被做過**，避免重做；並定位本專案的增量貢獻。
> 狀態標記：`[已讀]` / `[待讀]` / `[待驗證]` / `[已複現]`
> 最後更新：2026-08-16

---

## 結論先講

查證後，Tello 相關的資安研究可分三塊：

| 領域 | 前人成果 | 本專案定位 |
|---|---|---|
| 控制通道（UDP 8889/8890/11111） | **相當充分** | 僅複現作為基準 |
| 韌體 / 硬體逆向 | **有一定累積** | 不投入（除韌體升級通道） |
| **Tello App 本身的逆向與資料流** | **查無前人研究** | ✅ **主軸** |

**App 層的研究全部集中在 DJI 主品牌的 App（GO 4 / Pilot），
Tello 這支 App 本體的 SDK 盤點、端點分析與縱向比對，未見有人做過。**
這是本專案最明確的缺口。

---

## A. 方法論母本：DJI GO 4 Android App 分析（2020）

與本專案**最直接相關**的前人研究。Tello App 由 Shenzhen Ryze Tech 發行、
DJI 提供技術支援，兩者是否共用同一套 SDK／後端／保護機制，是本專案的核心提問。

### Synacktiv, "DJI Android GO 4 application security analysis" (2020-07) `[待讀]`
https://www.synacktiv.com/en/publications/dji-android-go-4-application-security-analysis

四項核心發現，以及本專案在 Tello App 上的對照結果：

| # | Synacktiv 對 DJI GO 4 的發現 | Tello App 對照 | 狀態 |
|---|---|---|---|
| 1 | 自我更新繞過 Google Play | `libpatchtool.so` 全六版存在，但可見 smali 中查無 `loadLibrary` 呼叫 | 🔄 待動態驗證 |
| 2 | Weibo SDK 可下載安裝任意 App 並回傳個資 | 六版皆**未發現** Weibo SDK | ✅ 否證（限可見 dex） |
| 3 | MobTech (Mob SDK) 蒐集個資 | 未發現 MobTech；但有**百度定位**與**騰訊 Bugly** | 🔄 見 F01 |
| 4 | **反除錯、混淆、動態解密與加殼** | **確認：全六版以愛加密（Ijiami）加固** | ✅ **已複現，見 F03** |

**第 4 項已在 Tello App 上獲得確認**——問題延伸到子品牌，且至 2024 年未改變。

DJI 回應：2020-07-31 更新 GO 4，移除 Weibo SDK，並把自動更新導回 Google Play。

### GRIMM, "DJI Privacy Analysis Validation" (2020-07) `[待讀]`
https://blog.grimm-co.com/2020/07/dji-privacy-analysis-validation.html

第三方獨立複現 Synacktiv 的結果（靜態＋動態）。**複現方法論值得直接借用。**

### Synacktiv, "DJI Pilot Android Application Security Analysis" `[待讀]`
https://www.synacktiv.com/en/publications/dji-pilot-android-application-security-analysis-1

### 廠商回應與報導 `[待讀]`
- DJI 官方聲明：https://www.dji.com/newsroom/news/dji-statement-on-further-misleading-claims-about-app-security
- SecurityWeek：https://www.securityweek.com/chinese-drone-giant-dji-responds-disclosure-android-app-security-issues/
- Threatpost：https://threatpost.com/dji-drone-app-riddled-with-privacy-issues-researchers-allege/157730/

---

## B. Tello 控制通道安全（L1 近場攻擊）

**此領域已被充分研究，本專案不投入原創，僅複現建立基準。**

### 業界／實務
- **Alias Robotics, "Ryze Tello Drone Pentesting: Security Case Study"** `[待讀]`
  https://aliasrobotics.com/case-study-pentesting-tello.php
  最高 **CVSS 9.4**。指出預設無密碼 Wi-Fi 與 de-auth 劫持。
- **Eyal Asulin, "Exploit and Takeover a DJI Tello Drone"** `[待讀]`
  https://medium.com/@eyalasulin.9/exploit-and-takeover-a-dji-tello-drone-9f69c18f6a3a

### 學術
- **"Analysis of Control Channel Cybersecurity of the Consumer-Grade UAV
  by the Example of DJI Tello"** (2021) `[待讀]`
  https://www.researchgate.net/publication/351750974_Analysis_of_Control_Channel_Cybersecurity_of_the_Consumer-Grade_UAV_by_the_Example_of_DJI_Tello
  控制通道安全的正式分析，本專案 L1 的主要引用來源。
- **Cluster Computing (Springer), 2025-01** `[待讀]`
  https://link.springer.com/article/10.1007/s10586-024-04911-8
  AI 強化的無人機入侵偵測，**以 DJI Ryze Tello 作為實驗平台**。
  注意：Tello 在此是受測對象而非研究主題。

### 已被確立的事實（不需重新發現，但需複現驗證）`[待驗證]`
- Tello 自建開放式 Wi-Fi AP，**無密碼**，不強制設定密碼、不做裝置綁定
- UDP `8889` 命令、`8890` 狀態、`11111` 視訊，**明文、無認證**
- 送出 `command` 即被標記為控制端
- 已有裝置連線時無人機仍運作 → 第二裝置可宣告接管，原操作者失去控制
- 取得 Wi-Fi 密碼後（若使用者有設）可用 de-auth 踢掉原操作者再接管

---

## C. 韌體與硬體逆向

**不在本專案範圍，但 TC-L1-07（韌體升級通道）需要這塊的背景。**

- **Sander Walters, "DJI/Ryze Tello Drone Gets Reverse-Engineered"** `[待讀]`
  https://medium.com/@swalters/dji-ryze-tello-drone-gets-reverse-engineered-46a65d83e6b5
  硬體拆解與韌體分析（Intel Movidius Myriad VPU）。
- **RyzeTelloFirmware（GitHub）** `[待讀]`
  https://github.com/NirViaje/RyzeTelloFirmware
  韌體映像檔收集，供逆向與拆解使用。
- **tellopilots 論壇：`.pro.fw.sig` 韌體檔格式討論** `[待讀]` ⭐
  https://tellopilots.com/threads/how-to-read-tello-firmware-v01-04-78-01-tools-for-pro-fw-sig-files.3153/

> ⭐ **對 TC-L1-07 的影響**：韌體檔副檔名為 `.sig`，強烈暗示**韌體是有簽章的**。
> 因此該測試案例的問題應從「有沒有簽章」改為
> **「簽章驗證是否確實在裝置端執行、能否繞過」**。
> 這也強化了先做被動觀察（步驟 1–2）、暫緩主動修改的判斷。

---

## D. 隱私評測（L3 資料主權）

### Mozilla Foundation, *Privacy Not Included* — Ryze Tello `[待讀]`
https://www.mozillafoundation.org/en/privacynotincluded/ryze-tello/

重點（需回到 Ryze 隱私權政策原文查證）：
- 蒐集姓名、電子郵件、通訊地址、行動電話號碼、**位置資料**
- **明示可能將個資分享給 DJI**
- 對是否販售使用者資料**未揭露**
- 保留條款寬鬆（備份、封存、防詐、分析、法遵…）

> **這是政策層面的評測，非技術分析。** 它記錄「廠商說會蒐集什麼」，
> 沒有驗證「App 實際做了什麼」。本專案補的正是後者。

### 一手來源 `[待讀]`
- Ryze 隱私權政策：https://www.ryzerobotics.com/policy
  （2026-08-16 直接抓取連線中斷，需用瀏覽器取得並存檔）
- **App 內建副本**：`assets/RYZE_Privacy_Policy.html`（205 KB）與
  `assets/ZH_RYZE_Privacy_Policy.htm`（133 KB）
  → **各版本 APK 內都有一份，等於自帶政策的時間軸快照。**
  比對六版之間的差異，可直接看出 1.6.8.0「Updated Privacy Policy」改了什麼。
  這比抓線上版本更可靠（線上版會被覆蓋）。

---

## E. 領域綜述（定位用）

- **Cyber4Drone: A Systematic Review of Cyber Security and Forensics in
  Next-Generation Drones** (MDPI Drones, 2023) `[待讀]`
  https://www.mdpi.com/2504-446X/7/7/430
- **SoK: Security and Privacy in the Age of Drones** (arXiv:1903.05155) `[待讀]`
- **Security Requirements of Commercial Drones for Public Authorities by
  Vulnerability Analysis of Applications** (arXiv:1909.02786) `[待讀]`
  ← 標題即「透過 App 漏洞分析」，方法論高度相關

---

## F. 研究缺口與本專案定位

> 開始時這張表是推測；經過首輪靜態分析後，多數缺口已有實證支持。

| 缺口 | 前人狀況 | 本專案已有的證據 | 定位 |
|---|---|---|---|
| **Tello App 的 SDK 盤點** | 查無 | 百度定位 + 騰訊 Bugly + GameSir，2019–2024 演變（F01） | ✅ 主軸 |
| **多版本縱向分析** | 查無 | 六版 × SDK／權限／端點／憑證矩陣 | ✅ 主軸 |
| **Tello App 的加殼保護** | 查無（DJI GO 4 有） | 愛加密全六版（F03） | ✅ 已確認 |
| **端點歸屬與資料主權** | 僅有政策層面評測 | 端點清單 + RDAP 歸屬（F02） | ✅ 主軸 |
| **憑證 pinning 素材狀態** | 查無 | leaf 憑證全過期、逾期達 8 年（F04） | ✅ 新發現 |
| **離線落地—上線補傳** | 查無 | 尚未驗證（需實機） | ✅ 主軸 |
| **停售後的後端存續** | 查無 | DNS 全數存活（F02） | ✅ 附帶 |
| **韌體升級通道完整性** | 有格式討論，無安全分析 | 未開始 | ⚠️ 條件性（需備援機） |
| 控制通道漏洞 | **充分** | — | ⚠️ 僅複現 |
| 硬體／韌體逆向 | 有累積 | — | ❌ 不投入 |

---

## 引用紀律

- 每個結論都要能指回：**原始檔案路徑 + 行號**（靜態）或 **pcap 檔 + 封包編號**（動態）。
- 引用前人研究時明確區分：
  「前人已證實」 vs 「本研究複現確認」 vs 「本研究新發現」。
- 未經自己驗證的二手說法，一律標 `[待驗證]`，不得直接當成結論。
- **標為 `[待讀]` 的來源，其內容目前只是搜尋摘要，不得直接引用細節。**
  正式引用前必須讀過原文。


---

# 新穎性評估（2026-08-26）

> **目的**：在對外發表或引用本研究前，明確區分「前人已發表」與「本研究的增量」。
> 未經此區分即宣稱發現，是最容易失去可信度的方式。

## 結論：L1 大多已知，L3 才是本研究的貢獻

本文件開頭於 2026-08-16 即預判「控制通道的前人成果相當充分」。
2026-08-26 的查證**證實了該預判**，而且範圍比預期更大。

### 已發表、本研究不具新穎性的部分

| 項目 | 前人來源 | 本研究對應 |
|---|---|---|
| **Tello Wi-Fi 預設無密碼** | Alias Robotics 案例研究，**RVDP#1208**，RVSS 10.0／CVSS 9.4 | F12、F16 的攻擊前提 |
| **SDK 協定無認證，可劫持** | 同儕審查論文《Analysis of Control Channel Cybersecurity of the Consumer-Grade UAV by the Example of DJI Tello》；另有公開的技術文章 | F16、F18 |
| **以 SDK 指令踢掉已連線的手機** | 公開技術文章明載「skip DJI's authentication checks, letting attackers **disconnect connected phones** and mark themselves as the controller」 | **F16 的核心機制** |
| Deauth 攻擊使操作者失去控制 | 上述論文 | 本研究未測（見 F16 下一步） |
| UDP 8889／8890／11111 的用途 | 官方 SDK 文件 + 多篇研究 | F16、F18 的基礎 |

> ⚠️ **F16 的核心機制並非本研究首次發現。**
> 「送出 SDK 指令可切斷擁有者連線」已有公開紀錄。
> 本研究的價值在於**量化與邊界釐清**，而非發現該現象本身。

### 本研究在 L1 的增量（精化，非發現）

前人多以「Tello 沒有認證」一語帶過。本研究以實測指出**這句話不完整**：

| 增量 | 內容 |
|---|---|
| **兩條路徑的安全模型不同** | App 的二進位協定**具**工作階段綁定（F12，滿舵注入 21.5 秒零反應）；SDK 純文字協定**完全沒有**（F16）。前人研究未作此區分。 |
| **WPA2 密碼無法緩解** | 實測設定密碼後攻擊照舊（F16）。前人指出 Wi-Fi 無密碼是問題，但未測「設了密碼是否就安全」。 |
| **不可恢復性** | 影像中斷後 47 秒零恢復，App 內重連無效，**僅能關閉飛機電源**（F16）。此點未見於前人紀錄。 |
| 精確時序 | `command` → `ok` 18 ms；影像於 4 ms 內中斷；封包數 1,766 → 0。 |

### 本研究可主張新穎性的部分（L3 / App 層）

本文件開頭即定位「Tello App 本體的逆向與資料流，查無前人研究」。
Alias Robotics 的案例研究**明確未涵蓋** App 分析、飛行日誌、第三方 SDK 與遙測。
以下各項目前未見對應的公開研究：

| 發現 | 內容 |
|---|---|
| **F09** | GameSir SDK 於啟動時上報至境內阿里雲，**所有版本、所有語言的隱私政策皆未揭露**，且**任何權限設定都無法阻止** |
| **F14** | 客服 WebView 載入阿里雲 ARMS 與 Google Analytics，含**持久性使用者識別碼** |
| **F05** | 隱私政策的揭露落差是**對稱的**——中文版揭露百度／騰訊、英文版揭露 Google，兩份都不完整 |
| **F01 + F17** | 六版縱向比對；百度原生庫**仍出貨但 JNI 進入點已成孤兒**（三條獨立證據） |
| **F10** | DJI 韌體更新通道的完整協定；API 走 AWS 而韌體檔走阿里雲 OSS |
| **F13** | Tello 飛行日誌的混淆求解（單位元組 XOR，金鑰存於酬載 `byte[2]`），並交叉驗證封包與檔案適用同一規則 |
| **F11** | 權限 A/B 對照：拒絕位置與相簿**不改變**待機流量 |

> **F13 的新穎性須保留**：DJI 的 DAT 格式有既存的第三方解析工具（如 DatCon）。
> 本研究**未查證**該格式的混淆方式是否早有公開文件，
> 亦**未驗證**既有工具是否適用於 Tello 的日誌。
> 在補上此查證前，F13 應敘述為「本研究獨立求解」而非「首次發現」。

## 對外發表時的敘述原則

- ❌ 不可寫：「本研究發現 Tello 可被未認證接管」
- ✅ 應寫：「本研究複現了已知的 SDK 劫持，並補上前人未涵蓋的三點：
  二進位協定具工作階段綁定、WPA2 無法緩解、影像中斷不可恢復」
- ✅ 主軸應放在 **L3 的 App 層與資料流**——那才是查無前人研究的部分

## 尚待查證

- [ ] 取得並精讀《Analysis of Control Channel Cybersecurity…》全文，確認其涵蓋範圍
- [ ] 查證 DJI DAT v3 的混淆方式是否已有公開文件
- [ ] 查證是否有人分析過 Tello App（而非 DJI GO 4／Pilot）的第三方 SDK
- [ ] 確認 RVDP#1208 是否已進入 CVE
