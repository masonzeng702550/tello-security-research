# 部落格素材包

> 這個目錄裡的東西**全部可以直接發布**。含住家環境的影像一律未收錄。
> 撰寫方向見 [`../docs/07-blog-outline.md`](../docs/07-blog-outline.md)。

---

## `PROMPT.md`

**在另一台機器上要開始寫的時候，先看這份。**
裡面有一段可直接複製給 AI 的完整 prompt，含閱讀順序、硬性限制與產出要求。

---

## 圖片（`img/`）

| 檔名 | 內容 | 建議用在 |
|---|---|---|
| `01-attack-statusbar-before-after.jpg` | 攻擊前後的 App 狀態列對照，Wi-Fi 圖示由正常變為斷線 | **第一幕的主圖**。影像區已裁去 |
| `02-video-killed-blackscreen.jpg` | 送出 7 個位元組後，App 畫面全黑 | 第一幕，接在 01 之後 |
| `03-still-black-after-45s.jpg` | 45 秒後畫面依然全黑 | 說明「不可恢復」時使用 |
| `04-app-connect-guide.jpg` | App 的「如何連接」畫面 | 開場鋪陳，或說明繁體字配中國用語時 |
| `05-app-control-disconnected.jpg` | 控制畫面，未連線狀態 | 備用 |
| `06-first-launch-agreement.jpg` | 首次啟動的使用者協議 | 談隱私政策那一段 |
| `07-env-magisk-superuser.jpg` | Magisk 超級使用者設定 | 談研究環境建置 |
| `08-env-magisk-installed.jpg` | Magisk 安裝完成 | 同上 |
| `09-env-shell-policy.jpg` | shell 的 root 授權政策 | 同上 |
| `10-frida-hook-crash.jpg` | Frida 的 Java hook 導致 App 崩潰 | 談加殼對抗、談 attach 為何要延遲掛載 |

### `04-app-connect-guide.jpg` 有一個容易被忽略的細節

畫面上的文字是**繁體字，但用的是中國用語**：

- 「在手機無線**局域網**中選擇」——台灣說「區域網路」
- 「**當前設備**未連接上飛行器」——台灣說「目前裝置」

這張圖可以直接當作 F05 的視覺佐證。

---

## `report.html`

完整的階段性報告，**圖片已內嵌為 data URI，可離線開啟**。
線上版：<https://claude.ai/code/artifact/c44422f1-34ab-427d-b169-b5262d40cd71>

直接用瀏覽器開啟即可。裡面的結構、數字、表格都可以直接搬進部落格。

---

## `quotes.md`

可直接引用的原始數據——封包內容、遙測字串、統計數字。
**寫作時不要憑記憶重打這些**，直接從該檔複製，避免抄錯。

---

## 不在這個目錄裡的東西（以及為什麼）

| 素材 | 為何未收錄 |
|---|---|
| 含相機畫面的截圖（8 張） | 全部含研究者住家環境 |
| 解碼出的影像畫格 | 同上 |
| pcap 檔 | 含無人機 SSID，可識別特定機體 |
| 飛行日誌 `.DAT` | 使用者個人資料 |
| APK 樣本 | 版權考量，且體積過大 |

若文章需要「攻擊者能看到你的攝影機畫面」這個視覺效果，
**請自行拍攝一個不含個人環境的場景重做一次**，不要使用既有素材。

---

## 撰寫時的必要提醒

寫作前請先讀 [`../docs/01-prior-art.md`](../docs/01-prior-art.md) 的新穎性評估。

**L1 的控制通道問題大多已有前人發表**（Alias Robotics RVDP#1208、CVSS 9.4；
同儕審查論文）。文章中提及時必須標註，不可寫成自己的發現。

真正查無前人研究的是 **L3 的 App 層與資料流**——F09、F14、F05、F13、F17。

完整的「不可寫 vs 應改寫」對照表見
[`../docs/07-blog-outline.md`](../docs/07-blog-outline.md) 第四節。
