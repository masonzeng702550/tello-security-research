# 截圖歸檔

供撰寫報告／文章使用的過程截圖。

## ⚠️ 公開前必須逐張審視

本目錄的檔案**不進版控**（見 `.gitignore`），因為可能含有：

- 裝置序號、SSID 後綴（即機身 MAC 後三組）
- 測試環境實景（`TC-L1-05_frame.png` 為無人機攝影機畫面）
- 本機網路資訊

## 現有檔案

| 檔名 | 內容 | 可公開性 |
|---|---|---|
| `03-magisk-superuser-settings.png` | Magisk Superuser 設定頁 | ✅ 無敏感資訊 |
| `04-magisk-installed.png` | Magisk 主畫面，版本 30.7 | ✅ |
| `05-magisk-shell-policy.png` | `com.android.shell` 的 root 政策 | ✅ |
| `06-tello-crash-frida-javahook.png` | Java hook 導致的崩潰對話框 | ✅ |
| `07-tello-first-launch-agreement.png` | **首次啟動的用戶協議（台灣裝置顯示簡體內文）** | ✅ F05 的關鍵證據 |
| `08-tello-main-screen.png` | 主控制畫面 | ✅ |

## 未截到的節點

下列步驟當時未截圖，補拍需重做流程，不建議：

- bootloader 解鎖確認畫面
- Magisk patch boot.img 的過程
- fastboot 刷入

→ 這些改以**終端機輸出**呈現，比截圖更精確且可驗證。
相關輸出完整記錄於 `notes/lab-journal.md`。