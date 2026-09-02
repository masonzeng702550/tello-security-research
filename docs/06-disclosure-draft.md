# 負責任揭露：通報草稿

> **狀態：草稿，尚未寄出。**
> 是否寄出、寄給誰、何時寄，均由研究者決定。
> 本文件僅備妥內容與判斷依據。

---

## 一、該不該通報

### 支持通報的理由

- **F09 與 F14 屬未公開的隱私問題**，且直接影響使用者：
  未揭露的第三方境外傳輸、且使用者無法以任何權限設定阻止
- 通報是研究倫理的標準程序，也是對外發表前的合理前置動作
- 即使產品已停產，**已售出的機體仍在使用中**（教育場域尤其）

### 需要納入考量的現實

- **Tello 產品線已於 2023–2024 陸續停售**，是否仍有維護管道未知
- **L1 的控制通道問題早已公開**（Alias Robotics RVDP#1208、CVSS 9.4、
  同儕審查論文），再次通報不具新意，**不應作為通報主體**
- 深圳市睿炽科技（Ryze Tech）與 DJI 的權責分工不明；
  App 由 Ryze 發行，後端與韌體通道指向 DJI

### 建議

**通報主體限於 F09、F14、F05 三項未公開的隱私與揭露問題。**
L1 的控制通道部分僅作背景提及，並主動聲明其為已知。

---

## 二、收件對象

| 對象 | 用途 | 備註 |
|---|---|---|
| DJI Security（`security@dji.com`） | 主要窗口 | DJI 設有漏洞獎勵計畫；Tello 是否納入範圍未確認 |
| Ryze Tech | App 發行方 | 公開聯絡管道有限，待查 |
| 台灣的教育主管機關 | 若確認教育場域廣泛使用 | **僅在 F18 的教室情境完成實地驗證後**才考慮 |

> ⚠️ 目前 F18 的教室情境**尚未實地驗證**（無第二台機體）。
> 在完成驗證前，不應向教育單位提出任何建議。

---

## 三、揭露時程建議

| 階段 | 時點 |
|---|---|
| 首次通報 | T |
| 等待回覆 | T + 14 天 |
| 若無回覆，寄出第二次 | T + 30 天 |
| 公開發表 | **T + 90 天**（業界慣例）或廠商修復後，以較早者為準 |

---

## 四、通報信草稿（中文）

> 主旨：Ryze Tello Android App 的第三方資料傳輸與隱私政策揭露問題

敬啟者，

我是一名獨立資安研究者。近期針對 Ryze Tello Android App
（`com.ryzerobotics.tello`，版本 1.6.8.0）進行分析時，發現三項與
第三方資料傳輸及隱私揭露相關的問題，在此依負責任揭露的慣例向貴公司通報。

**在說明之前先聲明**：本通報**不包含**控制通道的認證問題。
該部分已有公開發表的研究與評分紀錄，非本次通報的內容。

---

**問題一：未揭露的第三方資料傳輸，且使用者無法阻止**

App 啟動時，內嵌的手把控制 SDK（`com.xj.gamesir`）會向
`https://client.vgabc.com/clientapi/` 送出下列資料：

```
model=appstore&action=connectmodel&brand=<裝置廠牌>
&device=<裝置型號>&package=com.ryzerobotics.tello&sdkversion=5
```

該端點解析至中國境內的雲端服務。

檢索 1.3.0.0、1.6.0.1、1.6.4.0、1.6.8.0 四個版本的中文與英文隱私政策，
`gamesir`、`vgabc`、`小鸡` 等關鍵字的命中數**均為零**。
1.6.4.0 的附件一（貴公司最詳盡的一次第三方揭露）僅列出 Bugly 與 BaiduLBS。

以受控 A/B 測試確認：在位置、相片、影片、儲存空間等
**六項權限全部拒絕**的情況下，該請求仍照常送出，
且 payload 與六項全部授予時**逐位元組相同**。

亦即：**使用者既無從得知此傳輸存在，也無法透過任何系統設定阻止它。**

---

**問題二：客服頁面載入未揭露的第三方監控**

自 App 內開啟技術支援後，WebView 會載入
`retcode.alicdn.com/retcode/bl.js`（阿里巴巴前端監控 SDK），
並向 `retcode-us-west-1.arms.aliyuncs.com` 送出含
**持久性使用者識別碼**（`uid`）、工作階段識別碼、螢幕解析度、
像素密度與連線類型的信標。同時載入兩組 Google Analytics 追蹤碼。

隱私政策中對「阿里」「Alibaba」「Aliyun」「ARMS」「retcode」等字串的
命中數**均為零**。

---

**問題三：隱私政策的揭露落差**

中文政策揭露 Bugly 與 BaiduLBS，但未提及 Google Analytics；
英文政策揭露 Google Analytics，但未提及前兩者。
亦即**兩種語言的使用者各自看到不完整的第三方清單**。

而問題一、二所述的第三方，**在任何語言、任何版本中皆未揭露**。

---

**建議**

1. 於隱私政策中補充完整的第三方 SDK 清單，兩種語言內容一致
2. 為手把 SDK 的資料上報提供可關閉的選項，或於首次啟動時取得同意
3. 檢視客服 WebView 所載入的第三方監控是否為必要

**關於發表**

本研究預計於通報後 90 天公開發表。
若貴公司需要更長的修復時間，請告知，我方可討論延後。
若貴公司認為上述任一描述有誤，也請指正——我方會更正並記錄。

本研究全程僅在自有裝置與自有機體上進行，未對他人設備或公共頻譜進行任何操作。

敬祝 安好

（署名／聯絡方式）

---

## 五、隨附資料

通報時建議一併提供：

- [ ] 受測 APK 的 SHA-256 與取得來源
- [ ] 問題一的 mitmproxy flow（已去識別化）
- [ ] 權限 A/B 測試的完整輸出
- [ ] 政策檢索的指令與結果（含 `Bugly`／`BaiduLBS` 對照組，
      以證明檢索方法有效而非失效）

**不提供**：含住家環境的影像、飛行日誌原始檔、無人機 SSID。

---

## 六、英文版摘要（供國際窗口使用）

> Subject: Undisclosed third-party data transmission in Ryze Tello Android app

This report concerns **privacy and disclosure issues only**. It deliberately
excludes the control-channel authentication weaknesses, which are already
publicly documented and are not the subject of this report.

**1. Undisclosed transmission, not blockable by permissions.**
On launch, the bundled gamepad SDK (`com.xj.gamesir`) posts device brand,
model and package name to `https://client.vgabc.com/clientapi/`, an endpoint
resolving to a China-based cloud provider. This third party appears in **none**
of the privacy policies across four versions in either language. A controlled
A/B test confirms the request is sent **byte-for-byte identically** whether all
six location/media/storage permissions are granted or denied — the fields come
from standard system APIs and require no dangerous permission.

**2. Undisclosed monitoring in the support WebView.**
Opening in-app technical support loads Alibaba's ARMS front-end monitoring SDK,
which transmits a **persistent user identifier**, session ID, screen metrics and
connection type to Alibaba Cloud, alongside two Google Analytics properties.
No policy mentions Alibaba, Aliyun, ARMS or retcode.

**3. Asymmetric disclosure between languages.**
The Chinese policy names Bugly and BaiduLBS but not Google Analytics; the English
policy names Google Analytics but neither of the former. Users of each language
see an incomplete third-party list.

We intend to publish 90 days after this report. We are happy to extend that if
more time is needed, and to correct any factual error you identify.
All testing was performed on equipment owned by the researcher.
