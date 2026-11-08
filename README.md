# Ryze Tello 無人機與其 Android 應用程式之資安分析

針對 Ryze Tello（`com.ryzerobotics.tello`）Android 應用程式與 Tello 無人機所做的獨立資安研究。
涵蓋 2019 年至 2024 年共六個應用程式版本，執行靜態逆向、動態流量分析與實機協定驗證。

研究分為兩條獨立的主線：

| 主線 | 問題 |
|---|---|
| **控制通道安全** | 無人機的控制與影像通道是否可被同網段的未認證裝置干擾或接管 |
| **資料主權** | 應用程式蒐集哪些資料、送往何處，與其隱私政策的揭露是否一致 |

共產出十八項具名發現。其中七項經前人研究查證後未見對應的公開資料，
主要集中在應用程式層而非控制通道。控制通道的核心機制多已有前人發表，
本研究於該層為複現與精化，界定見 `docs/01-prior-art.md`。

## 研究範圍與倫理邊界

這是一份含有**尚未修補之弱點細節**的研究紀錄。閱讀與引用前請先了解下列邊界。

- 全部測試僅於研究者**自有**的一台 Tello 機體、自有的 Android 裝置與自架的隔離網段上進行。
- 未對廠商後端做任何主動測試，僅被動觀測應用程式自身發起的連線。
- 未自未經認證的來源送出任何 SDK 動作指令（`takeoff`、`land`、`emergency`、`rc`）。
  該邊界以程式碼層的 `NEVER_SEND` 黑名單實作，見 `poc/poc_sdk_unauth.py`。
- 唯一對飛行中機體送出控制輸入的測試為 TC-L1-03 階段二，
  用於驗證二進位協定是否具工作階段綁定，於戶外空曠場地進行，擁有者全程待命降落。
  程序見 `docs/procedures/TC-L1-03-injection-field-test.md`。
- **尚未向廠商通報。** `docs/06-disclosure-draft.md` 為草稿，未寄出，其中記載了通報與否的評估。
- 本倉庫不附任何可直接使用的攻擊工具或觸發用檔案。相關技法於文件中已完整敘述。

重現任何實測前，請先讀 `docs/03-ethics-legal.md`。

## 閱讀順序

| 想知道什麼 | 從哪裡開始 |
|---|---|
| 有哪些發現 | 下方發現索引，再讀對應的 `docs/findings/Fxx-*.md` |
| 研究如何推進，走過哪些彎路 | `docs/08-research-journey.md` |
| 證據分級的定義 | `docs/02-threat-model.md` |
| 前人研究與本研究的界線 | `docs/01-prior-art.md` |
| 如何自行重現 | `poc/REPRODUCE.md` |

## 發現索引

證據分級：**T0** 靜態存在　**T0′** 靜態不存在　**T1** 可達程式路徑
**T2** 執行期觀測　**T3** 已解密酬載（定義見 `docs/02-threat-model.md`）

威脅層：**L1** 近場 Wi-Fi　**L2** 同裝置應用程式　**L3** 供應鏈與資料主權

| # | 標題 | 層 | 證據 | 嚴重度 | 新穎性 |
|---|---|---|---|---|---|
| [F01](docs/findings/F01-third-party-sdk-longitudinal.md) | 第三方 SDK 縱向演變：百度定位與騰訊 Bugly 於 1.6.8.0 自可見 dex 消失 | L3 | T0／T0′ | 待定 | 未見前人研究 |
| [F02](docs/findings/F02-endpoint-attribution.md) | 端點歸屬：六版皆存在的非本機端點與其營運方 | L3 | T0 至 T2 | 待定 | 未見前人研究 |
| [F03](docs/findings/F03-ijiami-packer.md) | 愛加密加殼：`com/ryzerobotics` 的方法主體 96.7% 遭抽離 | 方法論 | T0 | Info | 同型問題前人已提出 |
| [F04](docs/findings/F04-stale-pinned-certificates.md) | 內建 pinning 憑證全數過期，並暴露未揭露網域 | L3 | T0 至 T2 | **Medium** | 未見前人研究 |
| [F05](docs/findings/F05-privacy-policy-language-asymmetry.md) | 隱私政策的揭露落差，且落差為對稱 | L3 | T0 | **High** | 未見前人研究 |
| [F06](docs/findings/F06-control-channel-no-auth.md) | 控制通道無認證，同網段裝置可干擾 | L1 | T2 | High | 前人已發表 |
| [F07](docs/findings/F07-l2-attack-surface.md) | 同裝置攻擊面：0 個匯出元件（否定結果） | L2 | T0′ | Info | 未見前人研究 |
| [F08](docs/findings/F08-dynamic-first-launch.md) | 首次啟動零網路請求（否定結果） | L3 | T2 | Info | — |
| [F09](docs/findings/F09-undisclosed-gamesir-transmission.md) | **未揭露的第三方境外上報，且無法以權限阻止** | L3 | **T3** | **High** | 未見前人研究 |
| [F10](docs/findings/F10-dji-backend-firmware-channel.md) | DJI 後端與韌體更新通道完整協定 | L3／L1 | **T3** | Info | 未見前人研究 |
| [F11](docs/findings/F11-permission-ab-idle-traffic.md) | 權限對照：拒絕位置與相簿不改變待機流量 | 方法論 | T2 | — | 未見前人研究 |
| [F12](docs/findings/F12-app-control-protocol-no-replay-protection.md) | 應用程式控制協定明文、序號恆為 0，但**具工作階段綁定** | L1 | T2 | Low | 本研究修正 |
| [F13](docs/findings/F13-flight-log-stored-locally-not-uploaded.md) | 飛行日誌混淆求解，金鑰與密文一同送出。未觀測到上傳 | L3 | T2 | Info | 獨立求解 |
| [F14](docs/findings/F14-support-webview-third-party-telemetry.md) | 客服 WebView 載入阿里雲 ARMS 與 Google Analytics，並帶有使用者識別碼 | L3 | **T3** | **Medium** | 未見前人研究 |
| [F15](docs/findings/F15-unauthenticated-video-and-log-exfiltration.md) | 未經認證即可取得即時影像與飛行日誌 | L1 | T2 | **High** | 前人已發表 |
| [F16](docs/findings/F16-sdk-command-hijack-and-video-dos.md) | **7 個明文位元組即切斷擁有者影像並取得完整遙測** | L1 | T2 | **Critical** | 核心機制為前人成果 |
| [F17](docs/findings/F17-native-library-analysis.md) | 原生程式庫：所檢字串中未發現自訂端點。百度模組為孤兒程式碼 | L3 | T0／T0′／T2 | Info | 未見前人研究 |
| [F18](docs/findings/F18-education-sdk-same-as-attack-surface.md) | **教學用的 API 就是攻擊用的 API，SDK 規格零認證** | L1 | T0／T2 | **High** | — |

兩條控制路徑的安全模型相反，這是本研究在 L1 層的主要增量：
官方應用程式的二進位協定**具**以來源為基礎的工作階段綁定（F12 實測），
而 SDK 的純文字協定**完全不具**（F16）。
先前的公開資料未作此區分。

## 重現

本倉庫**不附樣本資料**。APK 因版權考量、原始擷取檔因含機體 SSID 與研究者網段，
均未納入版本控制。因此 `tools/` 下的分析工具需要自備輸入檔。

重現路徑見 `poc/REPRODUCE.md`，其中逐項列出每個結論的取得步驟。
大致流程為：

1. 依 `samples/MANIFEST.md` 記錄的來源與雜湊取得 APK，以 `tools/verify_apk.ps1` 驗證簽章。
2. 靜態結論（F01、F03、F05、F07、F17）可僅憑 APK 重現，不需要實機。
3. 動態與協定結論（F09 至 F16）需要已 root 的 Android 裝置與一台 Tello。

文件中引用到未隨附檔案的地方，所依據的數值均已寫在文件內，可據以核對。

### 工具

| 檔案 | 用途 |
|---|---|
| `tools/verify_apk.ps1` | 樣本雜湊與簽章驗證 |
| `tools/apk_quicklook.ps1` | APK 快速盤點 |
| `tools/derive_tello_crc.py` | 自封包反推 CRC 參數並全量驗證 |
| `tools/decode_tello_proto.py` | 二進位協定解碼與序號欄位統計 |
| `tools/decode_dji_dat.py` | DJI_LOG_V3 飛行日誌解碼 |
| `tools/diff_flows.py` | mitmproxy 流量逐位元組比對 |
| `tools/tello_probe.py`、`tools/tello_inject.py` | 協定探測與封包編碼器，內建安全限制 |
| `tools/capture_session.ps1`、`tools/run_l1_capture.ps1`、`tools/run_permission_ab.ps1` | 擷取流程自動化 |
| `poc/poc_sdk_unauth.py` | 無認證存取的唯讀量測，內建 `NEVER_SEND` 黑名單 |

## 目錄結構

```
docs/
  00-research-plan.md       研究問題、前置關卡、階段時程
  01-prior-art.md           前人研究盤點與缺口定位
  02-threat-model.md        三層威脅模型與證據分級標準
  03-ethics-legal.md        倫理與法規邊界
  06-disclosure-draft.md    負責任揭露的通報草稿（未寄出）
  07-blog-outline.md        對外發表的撰寫方向與發表前檢查表
  08-research-journey.md    研究歷程，含環境建置與自我推翻的結論
  findings/                 十八項發現，每項一份
  procedures/               現場測試操作程序
poc/                        重現指引與唯讀量測腳本
tools/                      分析工具，共 12 支
blog-assets/                可直接發布的圖片、報告與可引用數據
notes/lab-journal.md        實驗日誌，依時間順序逐筆記錄
samples/MANIFEST.md         APK 樣本的來源、雜湊與簽章指紋
static/privacy-policy/      各版本的隱私政策原文
```

### 不在版本控制內的項目

下列內容因體積、散布疑慮或個人資料而未納入，`.gitignore` 已明列規則。

| 項目 | 原因 |
|---|---|
| `samples/*.apk` | 體積與散布疑慮。來源、SHA-256 與簽章指紋見 `samples/MANIFEST.md` |
| `static/<版本>/` | jadx 與 apktool 的產出，可由樣本重建 |
| `dynamic/pcap/`、`dynamic/mitm/` | 原始擷取檔含機體 SSID 與研究者網段 |
| `dynamic/firmware/` | 體積大且受廠商條款限制 |
| `docs/screenshots/` | 含裝置識別碼與實景，需逐張審視後才可公開 |

## 執行環境

| 項目 | 版本 | 用於 |
|---|---|---|
| Python | 3.11 以上 | 全部分析工具 |
| tshark（Wireshark） | 任一近期版本 | pcap 解析的後端 |
| mitmproxy | 9 以上 | 流量比對 |
| Windows PowerShell | 5.1 | `tools/` 之自動化腳本 |
| Frida | 17.17.0（android-arm64） | 執行期檢測，需已 root 的實機 |

輸出含中文字元時須先設定 `PYTHONIOENCODING=utf-8`。

## 已知限制

- 六個版本中僅 1.6.8.0 執行動態觀測，其餘五個版本僅做靜態分析。
- 飛行日誌的混淆已解，但 58 種記錄型別的欄位語意僅部分對應。
- 原生層的檢查方法為可列印字串與 ELF 符號表，未含反組譯。
  「未發現自訂端點」為否定性觀察，不等於不存在。
- SDK `rc` 指令於飛行中的實際效果未測試。
  因此本研究**不宣稱**攻擊者可使飛行器墜落。
- 全程未登入帳號，登入後的流量未觀測。

## 授權與引用

授權條款尚未決定，在加入 `LICENSE` 之前請視為保留一切權利。
引用時請註明出處並連回本倉庫。

本研究與 Ryze Tech、DJI 或任何其他廠商無隸屬關係，亦未受其委託或贊助。
