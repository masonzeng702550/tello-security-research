# F02 — 端點歸屬：DJI 飛行紀錄與阿里雲（中國）端點存在於全部六個版本

| 欄位 | 內容 |
|---|---|
| 編號 | F02 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 隱私 |
| 嚴重度 | **待定** — 需動態驗證後評估 |
| 受影響版本 | 全部（1.3.0.0 – 1.6.8.0） |
| 狀態 | **靜態 + 被動 DNS/RDAP 已確認 / 流量待驗證** |
| 新穎性 | 本研究新發現 |

## 摘要

即使 1.6.8.0 移除了百度與騰訊 SDK，**仍有四個非本機端點存在於全部六個版本**，
其中 `mydjiflight.dji.com`（DJI 飛行紀錄）與兩個解析至**中國境內阿里雲**的端點
從未被移除。這是 RQ2 的核心線索。

## 證據：六版皆存在的端點

| 網域 | 解析結果（2026-08-16） | RDAP 歸屬 | 註冊國 | 研判用途 |
|---|---|---|---|---|
| `mydjiflight.dji.com` | CNAME → `dm2eaotchwnxg.cloudfront.net` → 54.192.248.x | Amazon.com (AMAZO-CF2) | – | **DJI 飛行紀錄上傳** |
| `report.ryzerobotics.com` | CNAME → `d1rdp6eq8lhhmy.cloudfront.net` → 3.169.121.x | Amazon.com (AMAZON-CF) | – | Ryze 自家回報／遙測 |
| `chatsupport.ryzerobotics.com` | 47.110.222.8 | **ALISOFT（阿里雲）** | **CN** | 客服（中文） |
| `enchatsupport.ryzerobotics.com` | 47.254.51.89 | Alibaba Cloud - US | – | 客服（英文） |
| `client.vgabc.com` | 120.78.95.33 | **ALISOFT（阿里雲）** | **CN** | **不明 — 最高優先追查** |
| `192.168.1.1` | – | – | – | 本機／裝置端 |

**所有端點在 2026-08-16 皆可正常解析** → 後端 DNS 仍在運作，
前置關卡 **P2 得到初步正面答案**（但 DNS 存活 ≠ 服務仍回應，需實測）。

## 三個關鍵判讀

### 1. CloudFront 前置不代表資料留在境外

`mydjiflight.dji.com` 與 `report.ryzerobotics.com` 都經 AWS CloudFront。
**CDN 邊緣節點的位置與 origin、與資料落地位置無關。**
不可據此宣稱「資料存在美國」——必須以實際回應標頭、
TLS 憑證簽發者、以及（若可得）廠商文件佐證。這個邏輯漏洞很容易被抓。

### 2. `chatsupport` / `enchatsupport` 的中英分流

中文客服端點在**中國境內**阿里雲，英文客服端點在阿里雲海外節點。
顯示廠商對地域分流有意識的設計。若 App 依語系／地區自動選擇端點，
則台灣使用者實際命中哪一個，需動態驗證。

### 3. `client.vgabc.com` — 已查明：GameSir 手把 SDK 後端

> **本節為修正紀錄。** 初次分析時將此端點列為「來歷不明、最高優先追查」，
> 追查後證實為**手把控制器 SDK 的後端**，屬功能性用途。
> 原判斷過度，保留此更正過程作為舉證紀律的實例。

#### 追查過程

**1. RDAP（`vgabc.com`，2026-08-16）**
```
registration : 2010-03-26      ← 早於 Tello 上市（2018）8 年
expiration   : 2028-03-26
last changed : 2024-11-01      ← 仍在積極維護
nameservers  : F1G1NS1.DNSPOD.NET, F1G1NS2.DNSPOD.NET   ← 騰訊 DNSPod
```

**2. 憑證透明度（crt.sh，319 張憑證，14 個子網域）**
```
vgabc.com / www.vgabc.com          47.89.25.131
client.vgabc.com                   120.78.95.33      ← App 內硬編碼的目標
img.vgabc.com                      120.78.95.33
clientgsw / helpgsw / imggsw / img.gsw.vgabc.com
ucenter.egg.vgabc.com              47.115.129.237
xjdl.vgabc.com / xjdl2 / xj001dl   ← 關鍵線索
```

**3. 決定性證據 — DEX 內的 SDK 套件路徑**
```
Lcom/xj/gamesir/sdk/ButtonEvent;
Lcom/xj/gamesir/sdk/GamesirIndex;
Lcom/xj/gamesir/sdk/bluetooth/*;
"driveName":"xiaoji Gamesir-G2", "driveName":"GameSir-G3s", …
```

**`xj` = 小雞（xiaoji）**，正是 GameSir 手把的品牌方。
與子網域 `xjdl` / `xj001dl`（xiaoji download）完全吻合。

**4. 網域主體**：`vgabc.com` 由**廣州電遊網絡科技有限公司**營運
（「電遊」＝電子遊戲，與遊戲周邊業務一致）。

**結論**：`https://client.vgabc.com/clientapi/` 是 **GameSir 手把 SDK 的後端**。
Tello App 支援以實體手把操控，此為功能性整合，非資料蒐集端點。
這也解釋了為何它在 1.6.8.0 的 SDK 清理中被保留——手把功能仍在。

#### ⚠️ 但衍生出一個真正的問題：憑證早已過期

`client.vgabc.com` 的憑證透明度紀錄共 11 張，**最新一張簽發於 2019-10-17，
於 2020-10-16 到期**。此後至今（2026-08）**未再簽發任何憑證**。
對照 `vgabc.com` 整體在 2025 年簽發 78 張、2026 年 53 張——
主網域極活躍，唯獨 `client.vgabc.com` 自 2020 年起停滯。

而 App 硬編碼的是 **`https://`** URL。

→ **若 App 實際呼叫此端點，TLS 交握應該失敗。** 兩種可能：
- (a) 此程式路徑實際上已不再被觸發 → 死程式碼
- (b) 仍會呼叫，但 **App 忽略憑證錯誤** → **這才是真正的資安問題**

**(b) 若成立，等於存在一個停用 TLS 驗證的網路路徑**，
可被中間人利用。這比原本以為的「可疑端點」更值得查。

**驗證方式**：
1. Frida hook 網路層，確認此端點在執行期是否真的被呼叫
2. 若有呼叫，以 mitmproxy 掛自簽憑證，觀察 App 是否照樣接受
   → 接受 = 憑證驗證被停用，屬可利用的中間人路徑

#### 對 F01 的補充

`com.xj.gamesir.sdk` 是先前 SDK 盤點**遺漏**的第三方元件
（`apk_quicklook.ps1` 的 marker 清單未涵蓋）。已補入，需重跑縱向比對。

## ⚠️ 觀測邊界（重要）

- 這些網域是**從 dex 抽出的硬編碼字串**。已證明「程式碼裡有」，
  **未證明**「執行期會連線」，更未證明「傳送了什麼」。
- 端點清單不完整：執行期組出的 URL、加密字串、
  以及 `assets/` 中的設定檔皆未涵蓋。
- RDAP 歸屬反映的是 **2026-08-16 當下**的 IP 配置，會變動。

**在動態流量驗證完成前，本發現只能敘述為「程式碼中存在指向 X 的端點」，
不得寫成「App 將資料傳送至 X」。**

## 下一步（依優先序）

- [ ] **追查 `client.vgabc.com`** — WHOIS、憑證透明度紀錄（crt.sh）、被動 DNS 歷史
- [ ] jadx 找出各端點的**呼叫點**與請求內容組成
- [ ] 確認 `mydjiflight.dji.com` 的上傳觸發條件與 payload 欄位
- [ ] 動態驗證：實機飛行 → 切回網路 → 抓第一波上行流量（對照 `02-threat-model.md` 的時間差路徑）
- [ ] 比對 Ryze 隱私權政策是否揭露「飛行紀錄分享給 DJI」
