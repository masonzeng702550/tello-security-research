# F11 — 權限 A/B 對照：拒絕位置與相簿權限**不會**改變待機流量

| 欄位 | 內容 |
|---|---|
| 編號 | F11 |
| 層級 | 方法論驗證 / L3 |
| 分類 | 假設檢驗（否證） |
| 嚴重度 | — （本findings為方法論結果，非漏洞） |
| 受影響版本 | 1.6.8.0 |
| 狀態 | **T2 — 執行期已觀測** |
| 對應測試 | TC-L3-04 補充 |
| 證據 | `flow:AB-perm-A.flow`、`flow:AB-perm-B.flow` |
| 腳本 | `tools/run_permission_ab.ps1`、`tools/diff_flows.py` |

## 待檢驗的假設

先前觀測到 App 在待機時幾乎不發出網路請求（F08）。
一個直覺的解釋是：

> 「因為測試裝置拒絕了位置與相簿權限，所以 App 在待機時沒有東西可傳。」

若成立，則所有「無外送流量」的觀察都只是權限設定的產物，
不能推論到一般使用者的實際情境——**這會使先前的觀測失去外部效度**。
故必須檢驗。

## 測試設計

| | A 組 | B 組 |
|---|---|---|
| `ACCESS_FINE_LOCATION` | ❌ | ✅ |
| `ACCESS_COARSE_LOCATION` | ❌ | ✅ |
| `READ_MEDIA_IMAGES` | ❌ | ✅ |
| `READ_MEDIA_VIDEO` | ❌ | ✅ |
| `READ_EXTERNAL_STORAGE` | ❌ | ✅ |
| `WRITE_EXTERNAL_STORAGE` | ❌ | ✅ |
| 待機觀測 | 180 秒 | 180 秒 |
| 其餘條件 | 相同 | 相同 |

### 混淆變因的控制

**這是本測試成立的關鍵。**

GameSir SDK 以 `shared_prefs/gamesir_config.xml` 的 `gamesir_lastTime` 做節流。
若不重置，**兩組都會因節流而無流量**，A/B 將測不出任何差異，
而該零差異會被誤讀為「權限無影響」——結論碰巧正確但論證無效。

故兩組在啟動前均將該值歸零：

```sh
sed -i 's/name="gamesir_lastTime" value="[0-9]*"/name="gamesir_lastTime" value="0"/' \
    /data/data/com.ryzerobotics.tello/shared_prefs/gamesir_config.xml
```

其餘控制項：

- **只 `force-stop`，不清除 App 資料** —— 避免 B 組多跑一次首次啟動流程
- 免責聲明已接受（`DisclaimerShowState=1`），兩組 UI 起點相同
- 兩組使用相同的 Frida 解 pinning 腳本、相同 mitmproxy 設定
- **全程不觸碰畫面**，純待機

### 權限確實生效的驗證

測試後以 `dumpsys package` 確認 B 組六項權限皆 `granted=true`，
排除「`pm grant` 未生效」這個失敗模式。

## 結果：兩組完全相同

```
=== 請求數 ===
A拒絕: 1    B授予: 1

=== 端點出現次數 ===
端點                                          A拒絕  B授予  差異
POST client.vgabc.com/clientapi/                1     1     =

=== 僅出現於單一組的端點 ===
（無）—— 兩組打到完全相同的端點集合

=== 請求 body 逐一比對 ===
  [相同] POST client.vgabc.com/clientapi/ #1  (110 bytes)

=== 回應大小 ===
  POST client.vgabc.com/clientapi/    A拒絕=[2053]  B授予=[2053]
```

請求 body 在兩組中**逐位元組相同**：

```
model=appstore&action=connectmodel&brand=google&device=Pixel 6 Pro
&package=com.ryzerobotics.tello&sdkversion=5
```

## 結論

**假設否證。** 位置與相簿權限對待機流量**沒有任何影響**——
不影響端點、不影響請求數、不影響 payload 的任何一個位元組。

### 這對先前的發現有何意義

1. **F08 的「首次啟動零請求」不是權限設定的產物**，
   可推論到一般使用者情境。外部效度成立。

2. **F09 的 GameSir 上報與權限無關**——
   該請求在**六項權限全部拒絕**的情況下照樣送出。
   使用者無法以拒絕權限來阻止它。這強化了 F09 的嚴重度判定：
   未揭露的上報不受使用者可見的權限控制項所節制。

3. 送出的欄位（廠牌、機型、套件名、SDK 版本）**本來就不需要任何危險權限**，
   全部可由 `android.os.Build` 取得。這解釋了為何權限無影響。

## 附帶發現：DJI 韌體檢查不是待機心跳

先前工作階段（F10）擷取到 `mydjiflight.dji.com` 的兩個請求與後續的
`terra-2-g-a.djicdn.com` 韌體檔下載。**本次 A/B 的兩組都完全沒有觸發它們。**

兩者的差異在於：**本次全程未觸碰畫面**。

→ **DJI 韌體檢查需要使用者互動才會發生，並非待機期間的定期回報。**

這修正了 F10 可能引起的誤讀——該通道不是背景心跳。
確切的觸發條件（進入某畫面／點擊某按鈕）尚未定位。

## 觀測邊界

- 觀測時長為 **180 秒**。更長週期的心跳（小時級、日級）不在觀測範圍內
- **未連接無人機**。授予權限後若連機飛行，是否上傳飛行軌跡或相片，
  本測試**未涵蓋**——那是另一組必要的 A/B
- **未登入帳號**
- 僅測試單一裝置（Pixel 6 Pro / Android 13）
- 授予權限 ≠ App 實際取用。本測試證明的是「不影響網路流量」，
  **未證明**「App 沒有讀取位置或相簿」——本機讀取不經過 mitmproxy。
  若要回答後者，需以 Frida hook `LocationManager` 與 `MediaStore` 查詢

## 下一步

- [ ] 連機後重跑同一組 A/B —— 飛行資料的上傳才是真正的風險點
- [ ] 定位 `mydjiflight` 韌體檢查的實際觸發條件
- [ ] 以 Frida hook 本機 API，區分「未讀取」與「讀取但未外送」
- [ ] 延長觀測至數小時，檢驗是否存在長週期心跳
