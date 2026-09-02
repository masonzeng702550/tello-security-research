# 可直接引用的原始數據

> 寫作時**從這裡複製，不要憑記憶重打**。每一項都標註了出處 findings。
> 所有數字皆為本研究實測值。

---

## 一、SDK 攻擊（F16）

### 攻擊酬載

```
command
```

7 個 ASCII 字元。無標頭、無校驗、無認證。

### 時間軸（實測）

```
t = 10.106 s   我方 45998 → 8889    "command"
t = 10.120 s   飛機 8889  → 45998   "ok"                 ← 18 毫秒
t = 10.11  s   App 影像串流停止                          ← 相隔 4 毫秒
t = 10.228 s   飛機 8889  → 8890    "pitch:0;roll:1;…"
```

### 影像封包數

| 區間 | 封包數 |
|---|---|
| 攻擊前（0–12.1 s） | **1,766** |
| 攻擊後 +0 ~ +10 s | **0** |
| 攻擊後 +10 ~ +25 s | **0** |
| 攻擊後 +25 ~ +47 s | **0** |

同期間 App 的控制流：**2,893 個封包，至 59 秒仍在送（49–51 Hz）**。

### 飛機廣播給攻擊者的遙測（明文）

```
pitch:0;roll:1;yaw:8;vgx:0;vgy:0;vgz:0;templ:70;temph:73;
tof:10;h:0;bat:85;baro:49.44;time:0;agx:1.00;agy:-27.00;agz:-999.00;
```

16 個欄位：三軸姿態、三軸速度、三軸加速度、機體溫度上下限、
測距感測器高度、氣壓高度、**電量百分比**、氣壓計、飛行計時。

### WPA2 密碼無效（實測）

```
設定前：TELLO-XXXXXX   Security type: open
設定後：TELLO-XXXXXX   Security type: wpa2-psk / wpa3-sae

以密碼合法連上後，自陌生來源埠重送 command：
t = 10.107 s   command
t = 10.120 s   "ok"                     ← 13 毫秒，與開放網路無實質差異
t = 10.276 s   SDK 廣播開始（431 個封包）
App 影像：前 1,499 個 → 後 6 個 → 0
```

### 廠商自己的字串（App 資源檔，1.6.8.0）

英文 `values/strings.xml`：

> The aircraft's Wi-Fi network **has no password by default**. If you set a
> password and forget it, press and hold the power button for 5 seconds when
> the aircraft is powered on to restore default settings.

繁中 `values-zh-rTW/strings.xml`：

> 飛行器**默認無密碼**；忘記密碼時，可在開機後長按開機鍵5秒重置密碼

---

## 二、未揭露的境外上報（F09）

### 請求內容（完整，T3）

```http
POST https://client.vgabc.com/clientapi/

model=appstore&action=connectmodel&brand=google&device=Pixel 6 Pro
&package=com.ryzerobotics.tello&sdkversion=5
```

端點解析至中國境內阿里雲。

### 權限 A/B 對照（實測）

```
=== 請求數 ===
A（六項權限全拒絕）: 1    B（六項權限全授予）: 1

POST client.vgabc.com/clientapi/     A=1  B=1   =
[相同] body 110 bytes（逐位元組相同）
回應大小  A=[2053]  B=[2053]
```

受測的六項權限：`ACCESS_FINE_LOCATION`、`ACCESS_COARSE_LOCATION`、
`READ_MEDIA_IMAGES`、`READ_MEDIA_VIDEO`、`READ_EXTERNAL_STORAGE`、
`WRITE_EXTERNAL_STORAGE`。

### 隱私政策檢索

`gamesir` / `vgabc` / `小鸡` / `xj` 於 1.3.0.0、1.6.0.1、1.6.4.0、1.6.8.0
的中文與英文政策中，**命中數皆為 0**。

---

## 三、客服 WebView 的第三方遙測（F14）

### 阿里雲 ARMS 信標（完整參數）

```
HEAD retcode-us-west-1.arms.aliyuncs.com/r.png
  t     = pv
  uid   = <已遮蔽，28 字元英數>     ← 持久性使用者識別碼
  sid   = <已遮蔽，28 字元英數>
  pid   = ififn93np0@a8ac277f7c20d9a
  dt    = DJI Support
  ul    = zh-CN                            ← 裝置為 zh-Hant-TW
  sr    = 892x412
  dpr   = 3.50
  ct    = 4g
  release = school   environment = prod
→ 200, Server: AliyunSLS
```

同時載入 Google Analytics 兩組：`UA-154665611-3`、`G-87E5T7694J`。

### 五個新端點（皆不在靜態清單中）

| 端點 | Server |
|---|---|
| `chatcollege.ryzerobotics.com` | Tengine |
| `service.djicdn.com` | Tengine |
| `repair.djicdn.com` | **AliyunOSS** |
| `retcode.alicdn.com` | Tengine |
| `retcode-us-west-1.arms.aliyuncs.com` | **AliyunSLS** |

> 上報目的地為 **us-west-1（美西）**，不是中國節點。
> **不可寫成「傳往中國」。**

---

## 四、隱私政策的對稱揭露落差（F05）

| 第三方 | 中文政策 | 英文政策 |
|---|---|---|
| `Bugly` | 4 次 | **0 次** |
| `BaiduLBS` | 1 次 | **0 次** |
| `Google Analytics` | **0 次** | 三版皆有揭露 |
| 阿里雲 / `Alibaba` / `Aliyun` / `ARMS` / `retcode` | **0 次** | **0 次** |
| `GameSir` / `vgabc` / `小鸡` | **0 次** | **0 次** |

英文政策原文（Cookie Policy 章節）：

> we use Google Analytics to collect and process certain analytics data

### 繁中資源的在地化程度

`values-zh-rTW/strings.xml`，共 316 條字串：

| 中國用語 | 次數 | 台灣用語 | 次數 |
|---|---|---|---|
| 設置 | 19 | 設定 | 1 |
| 屏幕 | 9 | 螢幕 | **0** |
| 點擊 | 9 | 點選 | **0** |
| 當前 | 6 | 目前 | **0** |
| 視頻 | 5 | 影片 | **0** |
| 網絡 | 4 | 網路 | **0** |
| 用戶 / 賬號 / 默認 / 鏈接 / 局域網 | 各 1 | 對應台灣用語 | **各 0** |

```
中國用語合計 57 次    台灣用語合計 4 次    → 93.4%
12 組對照中有 9 組完全只出現中國用語
```

逐字比對（用詞完全相同，僅字元不同）：

```
zh-rCN:  账号密码将在重启后生效。假如1分钟内无法自动连接上飞行器，请手动连接WI-FI
zh-rTW:  賬號密碼將在重啟後生效。假如1分鐘內無法自動連接上飛行器，請手動連接WI-FI
```

### App 內部狀態

`shared_prefs/share_date.xml`：

```xml
<string name="AreaCodeTello">TW</string>
```

裝置 locale 為 `zh-Hant-TW`，但送出 `language: zh_cn`（見 F10）。
**App 已正確判定地區為台灣，仍套用簡中。**

---

## 五、飛行日誌解碼（F13）

### 混淆方式

```
plain[i] = cipher[i] ^ cipher[2]
```

單位元組 XOR，金鑰存放在酬載的第 3 個位元組，**隨密文一同送出**。

### 全量驗證

| 指標 | 解碼前 | 解碼後 |
|---|---|---|
| 為 0 的位元組比例 | — | **30.5%**（隨機約 0.4%） |
| 位元組熵 | 7.962 / 8.0 | **6.356 / 8.0** |

### 檔案結構

```
記錄框架  0x55 | 長度(1) | 0x00 | 型別(1) | 酬載…
起始 offset 1256

記錄總數    60,115
檔案涵蓋率  100%
相異型別    58 種
飛行時長    約 4 分鐘 → 每秒約 250 筆
```

### 解碼後的結構

```
型別 0x7a:  f01a0079d11b 0000000100000000000000000000 c309 995c
            f8120096de13 0000000100000000000000000001 c309 3eac

型別 0x8b:  cbd40084e0d2 adfec3ff04006a01 adfec3ff04006a01 8202…
                         └──── 同一組欄位重複兩次 ────┘
```

### 封包與檔案適用同一規則

```
0x1051 封包 1,172 個 → 內含 0x55 記錄 3,543 筆
byte[2] 解碼後為 0   → 3,543 / 3,543  (100%)
解碼後零值比例       → 28.2%（DAT 檔 30.5%）
```

---

## 六、原生程式庫（F17）

### 百度模組的孤兒狀態

```
liblocSDK8a.so  43,112 bytes，1.6.8.0 仍隨 APK 出貨
JNI 進入點 18 個，全部指向 com.baidu.location.Jni / com.baidu.serverLoc.Jni

而 1.6.8.0 的 dex 中，com/baidu 開頭的類別數：0
```

其他匯出符號：

```
_ZN12GcjEncryptor13Transform_yj5Edd    ← GCJ-02 座標轉換（中國法規要求的偏移）
_ZN3MD58MD5FinalEPhP7MD5_CTX           ← MD5
_Z13decode_base64PhPKcjRj              ← Base64
_Z12gzdecompressPhmS_Pm                ← gzip
```

### 執行期驗證

| 條件 | `liblocSDK8a.so` | 載入的 .so 總數 |
|---|---|---|
| 位置權限**拒絕** | 未載入 | 267 |
| 位置權限**授予**、等 20 秒 | **仍未載入** | 267 |

### 名稱容易誤導的那個

```
libdreamDroneParser.so  9,992 bytes
Java_com_sdk_DreamDroneParser_decodeVideoWH
Java_com_sdk_DreamDroneParser_yuv420pToyuv420sp
h264_decode_seq_parameter_set
```

**只做 H.264 解析度擷取與 YUV 格式轉換**，不含協定解析、加密或網路。

---

## 七、官方 SDK 文件（F18）

來源：`Tello SDK 2.0 User Guide`（Ryze 官方 CDN，8 頁）

```
emergency        "Stop motors immediately."
rc a b c d        直接搖桿控制
wifi ssid pass    設定飛機的 Wi-Fi 名稱與密碼

全文檢索 "auth" 出現次數：0
```

文件原文：

> Before sending any other commands, send "command" to the Tello via UDP PORT 8889

```
Tello IP: 192.168.10.1   UDP PORT: 8889     ← 指令
Tello IP: 192.168.10.1   UDP PORT: 8890     ← 狀態
Tello IP: 192.168.10.1   UDP PORT: 11111    ← 影像
```

### `rc` 指令的對照組驗證（F16）

```
t =  9.11s  送出 'command'       → 回應 'ok'
t = 13.20s  送出 'rc 0 0 0 0'    → 無回應、無錯誤
t = 17.25s  送出 'rc?'           → 回應 'unknown command: rc?'   ← 對照組
t = 21.35s  送出 'rc 0 0 0 0'    → 無回應、無錯誤
```

無效指令觸發錯誤、有效指令不觸發 → **`rc` 為此韌體識別的指令**。

---

## 八、二進位協定（F12，注入實測失敗）

### 封包結構

```
cc b000 7f 60 5000 0000 042000290d0114258700 b956
│  │    │  │  │    │    │                    └── CRC16
│  │    │  │  │    │    └── payload
│  │    │  │  │    └── 序號（小端序）
│  │    │  │  └── 命令碼 0x0050（搖桿控制）
│  │    │  └── 封包類型
│  │    └── 標頭 CRC8
│  └── 長度 << 3
└── 魔術位元組
```

### CRC 參數（暴力搜尋求得，16,849 封包全數吻合）

```
CRC8   poly=0x8c  init=0x77   reflect   覆蓋 byte[0:3] → byte[3]
CRC16  poly=0x8408 init=0x3692 reflect  覆蓋 byte[0:-2] → 末兩位元組
```

### 軸序（實測校正，八段全中）

```
軸1 = roll      ＋向右平移
軸2 = pitch     ＋向前
軸3 = throttle  ＋上升
軸4 = yaw       ＋右轉
滿舵 = 中位 1024 ± 660，即 364 – 1684
```

### 注入失敗的決定性測試

```
注入軸    yaw（軸4）
幅度      1684 = 滿舵右轉（+660，100%）
持續      21.5 秒，250 個封包，13.5 Hz
飛手      手離開搖桿（pcap 佐證：App 的 yaw 全程為 1024 中位）

結果      飛機完全沒有旋轉
```

滿舵偏航若生效，Tello 偏航率約 100°/s；即使按佔比折算仍應有約 20°/s，
21.5 秒足以轉超過一整圈。**實際旋轉量為零。**

---

## 九、專案統計

```
findings   18 份
commits    110
APK 版本   6 個（1.3.0.0 – 1.6.8.0，2019–2024）
pcap       19 個
工具       12 支
被自己推翻的推論  4 項
```

---

## 十、前人研究（引用時必須標註）

| 已發表 | 來源 |
|---|---|
| Tello Wi-Fi 預設無密碼 | Alias Robotics，**RVDP#1208**，RVSS 10.0／CVSS 9.4 |
| SDK 協定無認證、可劫持 | 《Analysis of Control Channel Cybersecurity of the Consumer-Grade UAV by the Example of DJI Tello》 |
| 以 SDK 指令踢掉已連線的手機 | 公開技術文章 |
| DJI GO 4 的加殼與第三方 SDK 問題 | Synacktiv (2020)、GRIMM (2020) |

**Alias Robotics 的案例研究明確未涵蓋**：SDK 協定、影像串流、韌體、
Android App 分析、飛行日誌、第三方 SDK 與遙測。
