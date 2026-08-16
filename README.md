# Tello App 逆向與資安分析研究

針對 Ryze Tello（`com.ryzerobotics.tello`）Android App 與 Tello 無人機的資安分析專案。
研究兩個獨立問題：**(A) 可被攻擊的漏洞面**、**(B) 資料是否／如何回傳至境外（中國）**。

## 目錄結構

| 路徑 | 用途 |
|---|---|
| `docs/00-research-plan.md` | 研究問題、前置關卡、階段時程 |
| `docs/01-prior-art.md` | 前人研究盤點與缺口定位 |
| `docs/02-threat-model.md` | 三層威脅模型與舉證標準 |
| `docs/03-ethics-legal.md` | 倫理與法規邊界 |
| `docs/findings/` | 每個發現一份 `Fxx-*.md`（用 `TEMPLATE-finding.md`） |
| `samples/` | APK 樣本（**不進版控**），`MANIFEST.md` 記錄來源與雜湊 |
| `static/` | jadx / apktool / Ghidra 產出（**不進版控**） |
| `dynamic/pcap/` | Wireshark / tcpdump / PCAPdroid 封包 |
| `dynamic/mitm/` | mitmproxy flow dump、解密後的 HTTP 交易 |
| `dynamic/frida/` | Frida hook 腳本 |
| `tools/` | 分析輔助腳本 |
| `notes/lab-journal.md` | 實驗日誌（照時間順序，逐筆記錄） |

## 現況（2026-08-16 查證）

- Google Play 上架頁面已 **404**，App 已下架 → APK 只能從第三方鏡像取得，**來源與簽章驗證是研究可信度的前提**。
- 已知可取得版本：**1.3.0.0 (2019) → 1.6.8.0 (2024)**，共 5 個版本，足以做縱向比對。
- DJI 於 2023–2024 陸續停售 Tello / 教育產品線；後端服務是否仍在運作**需實測確認**。

詳見 `samples/MANIFEST.md` 與 `docs/00-research-plan.md`。

## 開始之前

1. 先跑 `docs/03-ethics-legal.md` 的檢查表。
2. 取得 APK 後，用 `tools/verify_apk.ps1` 記錄雜湊與簽章，填入 `samples/MANIFEST.md`。
3. 每次實驗都寫進 `notes/lab-journal.md`，含時間、環境、指令、結果。**沒記錄的實驗等於沒做過。**
