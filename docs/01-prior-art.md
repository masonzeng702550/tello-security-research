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
