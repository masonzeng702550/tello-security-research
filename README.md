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
| `docs/procedures/` | 現場測試操作程序 |
| `notes/lab-journal.md` | 實驗日誌（照時間順序，逐筆記錄） |

## 現況（2026-08-16 查證）

- Google Play 上架頁面已 **404**，App 已下架 → APK 只能從第三方鏡像取得，**來源與簽章驗證是研究可信度的前提**。
- 已知可取得版本：**1.3.0.0 (2019) → 1.6.8.0 (2024)**，共 5 個版本，足以做縱向比對。
- DJI 於 2023–2024 陸續停售 Tello / 教育產品線；後端服務是否仍在運作**需實測確認**。

詳見 `samples/MANIFEST.md` 與 `docs/00-research-plan.md`。

## 發現索引

證據等級：**T0** 靜態存在 ／ **T0′** 靜態不存在 ／ **T1** 可達程式路徑 ／
**T2** 執行期觀測 ／ **T3** 已解密 payload（定義見 `docs/02-threat-model.md`）

| # | 標題 | 層級 | 證據 | 嚴重度 |
|---|---|---|---|---|
| [F01](docs/findings/F01-third-party-sdk-longitudinal.md) | 第三方 SDK 縱向演變：百度與 Bugly 確於 1.6.8.0 移除 | L3 | T0/T0′ | — |
| [F02](docs/findings/F02-endpoint-attribution.md) | 端點歸屬：六版皆存在的非本機端點與其營運方 | L3 | T0→T2 | 待定 |
| [F03](docs/findings/F03-ijiami-packer.md) | 愛加密加殼：89% 方法主體被抽取，靜態分析的邊界 | 方法論 | T0 | — |
| [F04](docs/findings/F04-stale-pinned-certificates.md) | 內建 pinning 憑證全數過期，並暴露未揭露網域 | L3 | T0→T2 | Medium |
| [F05](docs/findings/F05-privacy-policy-language-asymmetry.md) | 隱私政策的語言與地區落差；App 已判定 TW 仍套用簡中 | L3 | T2 | — |
| [F06](docs/findings/F06-control-channel-no-auth.md) | 控制通道無認證，可被同網段裝置接管 | L1 | T2 | **High** |
| [F07](docs/findings/F07-l2-attack-surface.md) | 同裝置攻擊面：0 個匯出元件 | L2 | T0′ | Low |
| [F08](docs/findings/F08-dynamic-first-launch.md) | 首次啟動零網路請求 | L3 | T2 | — |
| [F09](docs/findings/F09-undisclosed-gamesir-transmission.md) | **未揭露的第三方境外上報，且無法以權限阻止** | L3 | **T3** | **High** |
| [F10](docs/findings/F10-dji-backend-firmware-channel.md) | DJI 後端與韌體更新通道完整協定 | L3/L1 | **T3** | Info |
| [F11](docs/findings/F11-permission-ab-idle-traffic.md) | 權限 A/B：拒絕位置與相簿**不改變**待機流量 | 方法論 | T2 | — |
| [F12](docs/findings/F12-app-control-protocol-no-replay-protection.md) | **App 控制協定明文、搖桿指令序號恆為 0、Wi-Fi 無密碼** | L1 | T2 | **High** |
| [F13](docs/findings/F13-flight-log-stored-locally-not-uploaded.md) | 飛行紀錄以 DJI_LOG_V3 存於本機；時間差上傳**未觀測到** | L3 | T2 | Info |
| [F14](docs/findings/F14-support-webview-third-party-telemetry.md) | 客服 WebView 載入阿里雲 ARMS 與 GA，含持久性 uid | L3 | **T3** | Medium |
| [F15](docs/findings/F15-unauthenticated-video-and-log-exfiltration.md) | **未經認證即可取得即時影像與飛行日誌（已實測）** | L1 | T2 | **High** |

## 開始之前

1. 先跑 `docs/03-ethics-legal.md` 的檢查表。
2. 取得 APK 後，用 `tools/verify_apk.ps1` 記錄雜湊與簽章，填入 `samples/MANIFEST.md`。
3. 每次實驗都寫進 `notes/lab-journal.md`，含時間、環境、指令、結果。**沒記錄的實驗等於沒做過。**
