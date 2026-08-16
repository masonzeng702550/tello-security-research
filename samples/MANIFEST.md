# APK 樣本清冊

> 每一支樣本都必須填滿本表才可用於分析。**來源不明或簽章不符的樣本不得作為研究證據。**

## 目標套件

- Package: `com.ryzerobotics.tello`
- Developer: Shenzhen RYZE Tech Co.,Ltd
- Google Play: **已下架**（2026-08-16 查證，`play.google.com/store/apps/details?id=com.ryzerobotics.tello` 回 404 / 「找不到」，en_US 與 zh_TW 皆同）
- **但官網仍直接散布 APK**（2026-08-17 查證）：`ryzerobotics.com/tello/downloads` 仍提供下載，CDN 為 `dl-cdn.ryzerobotics.com`。
  → 「下架」僅指 Play 商店，**廠商本身未停止散布**。此點修正了先前的敘述。

## 可取得版本（2026-08-16 調查）

| 版本 | versionCode | 大小 | 鏡像上架日 | APKMirror | APKPure |
|---|---|---|---|---|---|
| 1.6.8.0 | 160800 | 30.15 MB (31,618,407 B) | 2024-09-06 (AM) / 2024-12-09 (AP) | ✅ | ✅ |
| 1.6.4.0 | – | 31.15 MB | 2022-09-08 | ✅ | ✅ |
| 1.6.0.1 | – | 30.96 MB | 2022-03-11 | ✅ | ❌ |
| 1.6.0.0 | – | 30.94 MB | 2021-01-07 | ✅ | ✅ |
| 1.4.0.0 | – | 31.0 MB | 2020-01-09 | ❌ | ✅ |
| 1.3.0.0 | – | 29.8 MB | 2019-02-01 | ❌ | ✅ |

**共 6 個版本，橫跨 2019–2024**，足以做縱向演變分析。

> ⚠️ 兩個鏡像對 1.6.8.0 的上架日不一致（2024-09 vs 2024-12）。鏡像上架日 ≠ 官方發布日，
> 紀錄時應以 APK 內的 `versionCode` 與檔案簽章時間為準，鏡像日期僅供排序參考。

### 1.6.8.0 已知中繼資料（APKMirror）

```
versionCode : 160800
minSdk      : 18  (Android 4.3)
targetSdk   : 30  (Android 11)
ABI         : arm64-v8a + armeabi-v7a
密度        : nodpi
語系        : 72
權限        : 16
features    : 6
```

> **值得追問**：2024 年釋出的 App 仍以 `targetSdk 30` 為目標。
> targetSdk 過舊會豁免掉 Android 11+ 的多項隱私強化（分區儲存、套件可見性、單次授權等），
> 這本身可能就是一個發現。同時這也很可能是它被 Play 下架的直接原因（Play 的 targetSdk 政策）。
> → 待 `apktool` 解出 manifest 後確認。

### 版本更新說明（1.6.4.0 → 1.6.8.0，APKMirror 轉載）

```
- Adds support for Android 13.
- Updated Privacy Policy.          ← 追這條：政策改了什麼？
- Optimizes firmware upgrade logic to allow upgrades when the drone's battery is below 50%.
- Fixed the problem of video playback blurry screen.
- Fixed a crash on some phone models.
```

---

## 取樣紀律

1. **首選來源：實體裝置 `adb pull`**（若機器上已安裝原版 App）。這是唯一可完全確認未被第三方改動的來源。
2. 次選：**APKMirror**（會驗證簽章是否與 Play 上的發行者一致）。
3. 僅在 APKMirror 無此版本時用 APKPure（1.4.0.0 / 1.3.0.0）。
   → 這兩支**必須**用 `apksigner verify --print-certs` 比對簽章憑證，
     與 APKMirror 上已知良好版本的憑證指紋一致才採用。**不一致就丟棄並記錄。**
4. 下載後立刻執行 `tools/verify_apk.ps1`，把輸出貼進下表。

## 樣本紀錄表 ✅ 已取得（2026-08-16）

| 檔名 | 版本 | 來源 | SHA-256 | 大小 (bytes) | 簽章 |
|---|---|---|---|---|---|
| `tello-1.3.0.0-apkpure.apk` | 1.3.0.0 | APKPure | `493cde8b8b6312bdb3cdb9c09b04510e055b3881a8cc5e67df377e173dba957f` | 31,218,192 | ✅ |
| `tello-1.4.0.0-apkpure.apk` | 1.4.0.0 | APKPure | `31f478ed447547037da8071900ffc4572a3276e5670567ddcb8fc5d8a0871dfe` | 32,501,886 | ✅ |
| `tello-1.6.0.0-apkmirror.apk` | 1.6.0.0 | APKMirror | `7064eea5a7e77b6c6e2d1cbc89dd005a74a5eb1074432de7e7d9c2d8f9fb52bc` | 32,441,241 | ✅ |
| `tello-1.6.0.1-apkmirror.apk` | 1.6.0.1 | APKMirror | `b5e08e5a10d8e7380d7eb7f11fbd8f60c45d64823a1739d8f0d69866ef532e4c` | 32,463,209 | ✅ |
| `tello-1.6.4.0-apkmirror.apk` | 1.6.4.0 | APKMirror | `2bacec75a3d1179dd97b7abff53b18e8ff19bff64798c5811cd27c73ff29b40b` | 32,660,255 | ✅ |
| `tello-1.6.8.0-apkmirror.apk` | 1.6.8.0 | APKMirror | `b55f2e62cd4dff960e855a549c978f611f82683e86134a4bc9f2092b3703a8af` | 31,618,407 | ✅ |

> 1.6.8.0 實際大小 31,618,407 bytes 與 APKMirror 頁面標示完全一致。

取得方式：`tools/fetch_apkmirror.ps1`（APKMirror 三段跳轉）；
APKPure 兩支以 `curl.exe` 自 `d.apkpure.com/b/APK/com.ryzerobotics.tello?versionCode=<code>` 取得。
`Invoke-WebRequest` 會被兩站以 TLS 指紋擋下（403），必須用 `curl.exe`。

## ✅ 官方來源交叉驗證（2026-08-17）

自 `ryzerobotics.com` 官網取得 `TELLO_GOOGLEPLAY_release_2024-08-29_1.6.8.0_signed.apk`，
與本專案自 APKMirror 取得的 1.6.8.0 比對：

```
官網下載    31,618,407 bytes   b55f2e62cd4dff960e855a549c978f611f82683e86134a4bc9f2092b3703a8af
APKMirror   31,618,407 bytes   b55f2e62cd4dff960e855a549c978f611f82683e86134a4bc9f2092b3703a8af
                               ↑ 位元組完全相同
```

**意義**：APKMirror 的樣本即官方建置產物，未經任何改動。
本專案所有基於 1.6.8.0 的發現（F01、F03、F04、F05、F07）
皆錨定於官方來源的二進位檔，樣本來源鏈完整。

官方檔名透露的資訊：
- `GOOGLEPLAY` → **這是 Google Play 版本變體**，暗示可能存在其他變體（如中國版）
- `2024-08-29` → 建置日期，APKMirror 於 2024-09-06 上架，相隔 8 天，一致

## 簽章基準（signing certificate baseline）✅ 已驗證

**六個版本全部使用同一把簽章金鑰**，包含兩支來自可信度較低的 APKPure 的舊版
（1.3.0.0 / 1.4.0.0）——與 APKMirror 已驗證版本的憑證完全相同，**來源驗證通過，可採用**。

```
基準憑證 SHA-256 : 53c78b9d025b16620569dd06d17fd49246749f9fe8eb47f6472bbc819ba1f878
Subject / Issuer : CN=tello  (自簽)
Serial           : 1A9B4633
有效期           : 2018-01-09 → 2043-01-03
簽章區塊         : META-INF/TELLO.RSA (v1 JAR signing)
```

> **值得註記**：憑證的 DN 僅有 `CN=tello`，**不含 O / OU / C 等組織識別欄位**。
> 從簽章本身無法確認發行組織身分，只能靠商店的發行者綁定。
> 這在 App 已下架、只能從鏡像取得的情境下，是供應鏈信任的實質弱點。

驗證方法：直接解析 `META-INF/*.RSA` 的 PKCS#7（`System.Security.Cryptography.Pkcs.SignedCms`），
不需 Android build-tools。實作見 `tools/apk_quicklook.ps1`。

> ⚠️ 上述僅驗證 **v1（JAR）簽章**。v2/v3 APK Signing Block 的完整性驗證
> 仍需 `apksigner`，取得 Android build-tools 後應補做。
