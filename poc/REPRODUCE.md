# 重現指引

> 本文件說明如何獨立驗證本研究的主要發現。
> 每一項都標註了所需器材、預期輸出，以及**該發現是否為本研究首次提出**。
>
> 新穎性的完整界定見 `docs/01-prior-art.md`。

---

## 快速對照

| # | 驗證項目 | 需要無人機 | 需要手機 | 耗時 | 新穎性 |
|---|---|---|---|---|---|
| A | 飛行日誌的混淆解碼 | ❌ | ❌ | 1 分鐘 | 本研究獨立求解 |
| B | 隱私政策的對稱揭露落差 | ❌ | ❌ | 2 分鐘 | **查無前人研究** |
| C | 原生程式庫與孤兒 JNI | ❌ | ❌ | 2 分鐘 | **查無前人研究** |
| D | SDK 未認證存取的量測 | ✅ | ❌ | 3 分鐘 | 現象已知，量測為增量 |
| E | 未揭露的境外上報 | ❌ | ✅ | 20 分鐘 | **查無前人研究** |

**A 至 C 完全不需要硬體**——只要有 APK 樣本與一份飛行日誌即可。

---

## A. 飛行日誌的混淆解碼

**假設**：`droneLog/*.DAT` 的混淆為單位元組 XOR，金鑰存於每筆記錄酬載的 `byte[2]`。

```bash
python tools/decode_dji_dat.py <你的 flight.DAT>
```

**預期輸出**

```
記錄 60,115 筆
解碼後為 0 的位元組: 30.5%   （隨機約 0.4%，偏高即代表金鑰正確）
```

**判讀**：若「解碼後為 0 的位元組」顯著高於 0.4%，即證明金鑰假設正確。
隨機資料不會在 XOR 後產生三成的零值。

> 日誌檔位於手機的
> `/sdcard/Android/data/com.ryzerobotics.tello/files/droneLog/`。
> 該檔屬個人資料，本專案不隨附。

---

## B. 隱私政策的對稱揭露落差

**假設**：中文政策揭露百度／騰訊但不提 Google；英文政策相反。兩份都不完整。

```bash
# 於各版本 APK 解包後的 assets/ 中檢索
grep -c "Bugly"            static/1.6.4.0/resources/assets/ZH_RYZE_Privacy_Policy.htm
grep -c "Google Analytics" static/1.6.4.0/resources/assets/RYZE_Privacy_Policy.html
grep -c "Google"           static/1.6.4.0/resources/assets/ZH_RYZE_Privacy_Policy.htm
grep -ci "alibaba\|aliyun\|ARMS" static/1.6.8.0/resources/assets/*Privacy*
```

**預期**：中文版 `Bugly` 有命中、`Google` 為 0；英文版 `Google Analytics` 有命中、`Bugly` 為 0；
阿里雲相關字串**兩份皆為 0**。

**檢索有效性的對照組**：以 `Bugly`／`BaiduLBS` 驗證檢索方法本身可用——
若這兩者也是 0，代表檢索失效而非文本內容如此。

> ⚠️ 本研究曾在此犯錯：初稿以過窄的關鍵字得出「英文版從未提及 Google Analytics」，
> 查證後為誤。**否定性主張必須以多組同義詞交叉檢索。**

### 附帶：繁中資源的在地化程度

```bash
grep -o "設置\|屏幕\|點擊\|當前\|視頻\|網絡" \
  static/1.6.8.0/resources/res/values-zh-rTW/strings.xml | wc -l
grep -o "設定\|螢幕\|點選\|目前\|影片\|網路" \
  static/1.6.8.0/resources/res/values-zh-rTW/strings.xml | wc -l
```

**預期**：中國用語遠多於台灣用語（本研究量得 57 : 4，佔 93.4%）。

---

## C. 原生程式庫與孤兒 JNI

**假設**：百度的 `liblocSDK8a.so` 仍隨 1.6.8.0 出貨，
但其 JNI 進入點所需的 Java 類別已不存在，故結構上無法被呼叫。

```bash
# 1. 確認 .so 仍在 APK 內
unzip -l samples/tello-1.6.8.0-apkmirror.apk | grep -i locsdk

# 2. 確認其 JNI 進入點指向 com.baidu.*
strings lib/arm64-v8a/liblocSDK8a.so | grep "^Java_com_baidu"

# 3. 確認 dex 中已無任何 com/baidu 類別
```

第 3 步可用 `tools/` 下的類別清單工具，或任何 dex 解析器。

**預期**：`.so` 存在、JNI 符號指向 `com.baidu.location.Jni` 等，
但 1.6.8.0 的 dex 中 `com/baidu` 開頭的類別數為 **0**。

**判讀**：JNI 函式必須有對應的 Java 類別才可能被觸發。
類別不存在 ⇒ 該原生模組結構上為死程式碼。
此證據**不依賴執行期觀測，也不受加殼影響**。

---

## D. SDK 未認證存取的量測

> **新穎性**：「Tello SDK 無認證、可劫持」**已有前人發表**
> （Alias Robotics RVDP#1208；同儕審查論文；公開技術文章）。
> 本項驗證的是前人未涵蓋的**量測值**。

**器材**：Tello 一台。**機體置於地面，建議拆下螺旋槳。**

```bash
# 1. 將執行環境連上該 Tello 的 Wi-Fi
# 2. 執行唯讀量測
python poc/poc_sdk_unauth.py
```

**預期輸出**

```
[1] command  → 'ok'   延遲 18.x ms
    未提供帳號、密碼、配對碼或任何憑證。

[2] 未經認證可取得的資訊：
      battery?   → '92'
      wifi?      → '90'
      temp?      → '76~78C'
      ...
    · sn?        → 'unknown command: sn?'

[3] 飛機主動廣播的遙測（UDP 8890，3 秒）：
    欄位 (16): pitch, roll, yaw, vgx, vgy, vgz, templ, temph, tof, h, bat, baro, time, agx, agy, agz
```

### 本腳本的安全邊界

`takeoff`／`land`／`rc`／`emergency`／`motoron`／`wifi`／`speed` 等
**一律拒絕送出，且該阻擋不可由參數繞過**。可自行驗證：

```bash
python -c "
import importlib.util
s=importlib.util.spec_from_file_location('p','poc/poc_sdk_unauth.py')
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
for c in ['takeoff','emergency','rc 0 0 0 100']:
    try: m.refuse_if_unsafe(c); print('未擋住:', c)
    except SystemExit: print('已擋下:', c)
"
```

> `sn?` 回 `unknown command` 是**預期**的——該指令屬 Tello EDU／SDK 2.0 指令集。
> 這代表攻擊者**取不到機體序號**，即缺少可用於長期追蹤的持久識別碼。
> 此點對隱私評估有利，應如實記錄。

---

## E. 未揭露的境外上報

> **本研究的主要新穎貢獻。** 商業資安公司的 Tello 案例研究明確未涵蓋 App 層分析。

**器材**：已 root 的 Android 手機、電腦、`mitmproxy`。**不需要無人機。**

### 步驟

1. 手機安裝 Tello App 1.6.8.0，**拒絕全部權限**
2. 電腦啟動 `mitmdump`，手機設定全域 proxy 指向之
3. **重置節流值**——這是本測試成立的前提：

```bash
adb shell su -c "sed -i \
  's/name=\"gamesir_lastTime\" value=\"[0-9]*\"/name=\"gamesir_lastTime\" value=\"0\"/' \
  /data/data/com.ryzerobotics.tello/shared_prefs/gamesir_config.xml"
```

4. 啟動 App，觀察 mitmproxy

### 預期

```
POST https://client.vgabc.com/clientapi/
body: model=appstore&action=connectmodel&brand=<廠牌>
      &device=<機型>&package=com.ryzerobotics.tello&sdkversion=5
```

### 關鍵對照：權限不影響此上報

以 `tools/run_permission_ab.ps1` 執行 A/B：

```
A 組（六項權限全拒絕）  請求 1 筆，body 110 bytes
B 組（六項權限全授予）  請求 1 筆，body 110 bytes，逐位元組相同
```

**若不重置 `gamesir_lastTime`，兩組都會因節流而無流量**，
零差異會被誤讀為「權限無影響」——結論碰巧正確，但論證無效。

---

## 未能重現的部分

以下為本研究**嘗試後失敗**的項目，一併記錄以免他人重複投入：

| 項目 | 結果 |
|---|---|
| 自記憶體傾印還原加殼後的 dex | 傾印所得與 APK 內的 `classes.dex` **位元組完全相同**。愛加密在 `ArtMethod` 層運作，非「還原整份 dex」。 |
| 離線反推 `signature` 的組成 | 窮舉參數排列、空值處理與 16 組常見鹽值前後綴，**全數未命中**。存在未知祕密，須執行期攔截。 |
| 飛行中注入二進位搖桿封包 | 滿舵、21.5 秒、飛手未操作，**飛機零反應**。二進位協定具工作階段綁定。 |
| 飛行日誌的欄位語意對應 | 以已知數值範圍找錨點無命中。正確做法為同步記錄 SDK 8890 串流與 `.DAT` 檔後對時間軸比對。 |

---

## 倫理邊界

- 全部測試皆在研究者**自有**的裝置與機體上進行
- 未對他人設備、未對公共頻譜進行任何操作
- 未執行任何具破壞性的指令（`emergency`／`rc`／`takeoff` 從未送出）
- 含住家環境的影像素材不對外提供

重現本研究時請遵守相同邊界。
