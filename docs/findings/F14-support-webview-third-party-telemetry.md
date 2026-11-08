# F14 — 客服 WebView 載入阿里雲 ARMS 與 Google Analytics，含持久性使用者識別碼

| 欄位 | 內容 |
|---|---|
| 編號 | F14 |
| 層級 | L3 供應鏈與資料主權 |
| 分類 | 隱私 / 未揭露的第三方 |
| 嚴重度 | **Medium** |
| 受影響版本 | 1.6.8.0 |
| 狀態 | **T3 — payload 已解密取得**（但取得條件有重大限制，見下） |
| 對應測試 | TC-L3-10 |
| 證據 | `flow:TC-L1-07-fwcheck.flow` |

## ⚠️ 先講限制：本次擷取是在 VPN 未關閉的情況下取得的

擷取當下電腦仍掛著 Surfshark，出口 IP 為 **Phoenix, Arizona (US)**。
Ryze 自家後端的 `GetIPRegion` 對我們的判定是：

```json
{"country":"UNITED KINGDOM","countryCode":"GB","ip1":"172.216.11.43",
 "country2":"CHINA","countryCode2":"CN","ip2":"172.31.30.229"}
```

> `country2: CHINA` 不可採信——`172.31.30.229` 是 RFC1918 私有位址，
> 對私有 IP 做地理定位本身就是無效查詢。

因此**凡與地區分流有關的觀察，本findings一律不下結論**：

| 觀察項目 | 是否受 VPN 影響 |
|---|---|
| App 走英文客服端點（`enchatsupport`、`lan=en`） | ⚠️ **可能是 IP 造成的，不可據此推論台灣使用者的行為** |
| 頁面載入哪些第三方 SDK | ❓ 若存在地區版本差異則仍可能受影響，**待台灣 IP 重測** |
| 信標中的 `ul=zh-CN` | ✅ 由裝置決定，與 IP 無關 |

**台灣 IP 下的對照測試尚未執行。** 這是本findings最主要的缺口。

## 觸發路徑

使用者操作（已由使用者確認）：

```
飛控警告列 →（點擊）→ 錯誤說明頁 →（點擊）「獲取技術支持」→ 開啟客服 WebView
```

## 請求鏈

```
enchatsupport.ryzerobotics.com/visitor/ryze/chat.html?companyId=42&echatTag=guava_support&lan=en
  └─ 301 ─▶ chatcollege.ryzerobotics.com/EchatRobotWeb/en/ECHATROBOT/index?lang=Others&from=ryze&product=acinquiry
              ├─ service.djicdn.com   … jQuery / Knockout / echatroot 等前端資源
              ├─ repair.djicdn.com    … 字型
              ├─ retcode.alicdn.com/retcode/bl.js        ← 阿里巴巴前端監控 SDK
              ├─ retcode-us-west-1.arms.aliyuncs.com     ← 遙測上報目的地
              ├─ googletagmanager.com  (UA-154665611-3、G-87E5T7694J)
              └─ google-analytics.com  /g/collect
```

## 五個端點皆不在既有的靜態清單中

| 端點 | `Server` | 歸屬 |
|---|---|---|
| `chatcollege.ryzerobotics.com` | Tengine | 阿里系 |
| `service.djicdn.com` | Tengine | DJI CDN |
| `repair.djicdn.com` | **AliyunOSS** | 阿里雲 OSS |
| `retcode.alicdn.com` | Tengine | **阿里巴巴 CDN** |
| `retcode-us-west-1.arms.aliyuncs.com` | **AliyunSLS** | **阿里雲日誌服務** |

F02 的端點盤點涵蓋 dex 字串與 pinning 憑證素材，**這五個一個都沒有**。
它們只在 WebView 實際載入頁面時才出現。

> 這是 F02「靜態方法無法產出完整端點清單」的第二個實例，
> 第一個是 F10 的 `terra-2-g-a.djicdn.com`。

## 上報內容

`retcode.alicdn.com/retcode/bl.js` 是阿里巴巴 ARMS 的前端監控 SDK。
載入後向阿里雲日誌服務送出：

```
HEAD retcode-us-west-1.arms.aliyuncs.com/r.png
     ?t=pv&times=1
     &uid   = <已遮蔽，28 字元英數>     ← 持久性使用者識別碼
     &sid   = <已遮蔽，28 字元英數>     ← 工作階段識別碼
     &pv_id = <已遮蔽，28 字元英數>
     &pid   = ififn93np0@a8ac277f7c20d9a       ← ARMS 專案識別碼
     &dt    = DJI Support
     &page  = chatcollege.ryzerobotics.com/echatrobotweb/en/echatrobot/index
     &ul    = zh-CN                            ← 語言
     &sr    = 892x412                          ← 螢幕解析度
     &dpr   = 3.50                             ← 像素密度
     &ct    = 4g                               ← 連線類型
     &release = school   &environment = prod
→ 200, Server: AliyunSLS
```

同時 Google Analytics 送出 `POST /g/collect?tid=G-87E5T7694J`。

### 判讀

- **`uid` 與 `sid` 為不同欄位**，`sid` 標示為工作階段識別碼，`uid` 則否。
  依此推測 `uid` 的存續範圍大於單次工作階段，但其產生方式與存續期間未經驗證。
- `sr` / `dpr` / `ct` 構成基本的裝置指紋。
- 上報目的地為 **`us-west-1`**（阿里雲美西節點），**不是中國節點**。
  資料落地位置需以此為準，**不可寫成「傳往中國」**。
  阿里巴巴為中國企業，其海外節點的法律管轄屬另一層次的討論，
  不應與技術上的資料落地位置混為一談。

## 揭露落差：一個對稱的模式

檢索三個版本的內建政策（`RYZE_Privacy_Policy.html` / `ZH_RYZE_Privacy_Policy.htm`）
與四個版本的線上政策全文：

| 第三方 | 中文政策 | 英文政策 |
|---|---|---|
| `Bugly` | ✅ 4 次 | ❌ 0 次（F05 已證） |
| `BaiduLBS` | ✅ 1 次 | ❌ 0 次（F05 已證） |
| **`Google Analytics`** | ❌ **0 次** | ✅ **有揭露（三版皆有）** |
| **阿里雲 / `Alibaba` / `Aliyun` / `ARMS` / `retcode`** | ❌ **0 次** | ❌ **0 次** |
| `GameSir` / `vgabc` / `小鸡` | ❌ 0 次 | ❌ 0 次（F09 已證） |

英文政策的原文（Cookie Policy 章節）：

> we use Google Analytics to collect and process certain analytics data

中文政策雖有 62 處 `Cookie`、92 處「第三方」、12 處「统计」，
但**從未點名任何分析類第三方**——「统计、分析」一詞皆指睿炽自身對資料的處理。
中文版唯二點名的第三方就是 `Bugly` 與 `BaiduLBS`。

> **檢索方法的有效性驗證**：同一批檢索對 `Bugly`（7 次）與 `BaiduLBS`（2 次）
> 皆有命中，故零命中反映的是文本內容，不是檢索失效。
> （`百度` 與 `Tencent` 為 0 次——廠商使用的是 SDK 名而非公司中文名，
> 這正是 F01 曾踩過的坑。）

### 判讀：揭露落差是對稱的

F05 記錄的是「中文版揭露 BaiduLBS、英文版沒有」。
本findings發現**反方向也成立**：英文版揭露 Google Analytics、中文版沒有。

→ **各語言版本只揭露該語言受眾「預期會看到」的第三方。**
   這比單向的落差更能說明問題——兩份文件都不是完整的揭露，
   而是各自針對受眾預期所做的取捨。

而**阿里雲 ARMS 與 GameSir 兩者，在任何語言、任何版本中皆未揭露**。
它們才是真正的揭露缺口。

## `ul = zh-CN` — F05 的第五個層級

信標中的 `ul` 為 `zh-CN`，而測試裝置：

```
persist.sys.locale = zh-Hant-TW
ro.product.locale  = en-US
```

**兩者皆非 `zh-CN`**，故該值是 App／頁面自行帶入，非繼承自裝置。
此值由裝置端產生，**不受 VPN 出口 IP 影響**，因此為有效證據。

> 保留意見：`ul` 的確切來源（`navigator.language` 或頁面設定值）未經驗證。

## 觀測邊界

- **VPN 未關閉**（見開頭）。地區分流相關的觀察一律不下結論。
- 僅觸發一次，未確認每次開啟客服是否都載入同一批第三方
- 未驗證 `uid` 的產生方式與存續期間（是否跨 App 重裝仍相同）
- 未檢視 `bl.js` 的實際行為，僅由其上報內容推斷
- 未測試中文客服端點 `chatsupport.ryzerobotics.com`（解析於中國境內阿里雲）
  是否載入不同的第三方

## 下一步

- [ ] **台灣 IP 下重做同一操作** —— 補上本findings最大的缺口
- [ ] 比對 `chatsupport`（中文）與 `enchatsupport`（英文）兩條路徑的第三方差異
- [ ] 檢查 `uid` 是否寫入 WebView 的 localStorage，以及重裝後是否重置
- [ ] 確認客服頁面是否有其他入口（設定選單等）
