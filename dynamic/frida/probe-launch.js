/*
 * F01 / F03 / F04 的首次啟動觀測腳本
 *
 * 目的：在不修改 App 行為的前提下，記錄三件靜態分析無法回答的事——
 *   1. 執行期實際載入哪些 native 函式庫  → 覆核 F01（liblocSDK8a / libpatchtool 是否被載入）
 *   2. 是否出現 com.baidu.* 類別         → 覆核 F01（是否藏在加殼 payload 中）
 *   3. 憑證與 TLS 相關 API 的呼叫        → 覆核 F04（pinning 實際行為）
 *
 * 純觀測，不改變任何回傳值。若腳本本身影響了 App 行為，觀測就失去意義。
 */

'use strict';

const seen = { libs: new Set(), classes: new Set(), assets: new Set() };
function log(tag, msg) { console.log(`[${tag}] ${msg}`); }

// ---------------------------------------------------------------- native 函式庫載入
// F01 的關鍵：liblocSDK8a.so 與 libRoadLineRebuildAPI.so 仍打包在 APK 中，
// 但字串池已無 "locSDK8a"。若執行期仍載入，代表另有載入路徑。
// Frida 17 移除了 Module.findExportByName(null, ...)，改為 findGlobalExportByName。
// 保留舊 API 的回退分支，讓腳本在 16.x 也能跑。
function globalExport(sym) {
    if (typeof Module.findGlobalExportByName === 'function') return Module.findGlobalExportByName(sym);
    if (typeof Module.findExportByName === 'function') return Module.findExportByName(null, sym);
    return null;
}

['dlopen', 'android_dlopen_ext'].forEach(function (sym) {
    const p = globalExport(sym);
    if (!p) { log('WARN', `找不到匯出符號 ${sym}`); return; }
    Interceptor.attach(p, {
        onEnter(args) { this.path = args[0].isNull() ? null : args[0].readCString(); },
        onLeave(retval) {
            if (!this.path || retval.isNull()) return;
            const name = this.path.split('/').pop();
            if (seen.libs.has(name)) return;
            seen.libs.add(name);
            const hot = /locSDK|RoadLine|patchtool|bugly|baidu/i.test(name);
            log(hot ? 'LIB!' : 'LIB ', `${name}   (${this.path})`);
        }
    });
});

Java.perform(function () {
    // ⚠️ 不要 hook java.lang.System.loadLibrary。
    //
    // 它有 Java 與 native 兩個 overload，Frida 的 Java 橋接會把分派搞混：
    // Android framework 內部（NetworkUtils.<clinit>）呼叫 native 版時被攔下、
    // 轉到 Java 版，導致 libframework-connectivity-jni.so 解析失敗，
    // App 在 ActivityThread.handleBindApplication 就 UnsatisfiedLinkError 崩潰。
    // 2026-08-17 實測踩到，崩潰與加殼偵測無關。
    //
    // native 層的 dlopen / android_dlopen_ext hook 已涵蓋所有函式庫載入，
    // 且不干擾 Java 方法分派，是更安全的觀測點。

    // ------------------------------------------------------------ 類別載入
    // F03 已證實 89% 方法主體被抽取；若百度類別在執行期由加密 payload 還原，
    // 會在此處現形。
    // 用 Interceptor 附掛而非 replace implementation，避免改變分派行為。
    try {
        const CL = Java.use('java.lang.ClassLoader');
        const orig = CL.loadClass.overload('java.lang.String');
        orig.implementation = function (n) {
            const r = orig.call(this, n);          // 先照原樣執行，確保行為不變
            if (/baidu|bugly|tencent|locSDK|patchtool/i.test(n) && !seen.classes.has(n)) {
                seen.classes.add(n);
                log('CLASS!', n);
            }
            return r;
        };
    } catch (e) { log('WARN', 'ClassLoader hook 失敗: ' + e); }

    // ------------------------------------------------------------ assets 開啟
    // 追蹤憑證檔（F04）與那些不被 dex 引用的資產（F07）是否真的被讀取
    try {
        const AM = Java.use('android.content.res.AssetManager');
        AM.open.overload('java.lang.String').implementation = function (n) {
            if (!seen.assets.has(n)) {
                seen.assets.add(n);
                const hot = /\.(cer|crt|pem)$|ijiami|\.jet$|\.bin$|Privacy|Policy/i.test(n);
                log(hot ? 'ASSET!' : 'ASSET', n);
            }
            return this.open(n);
        };
    } catch (e) { log('WARN', 'AssetManager hook 失敗: ' + e); }

    // ------------------------------------------------------------ TLS 信任決策（F04）
    try {
        const TMF = Java.use('javax.net.ssl.TrustManagerFactory');
        TMF.getTrustManagers.implementation = function () {
            log('TLS', 'TrustManagerFactory.getTrustManagers()');
            return this.getTrustManagers();
        };
    } catch (e) {}

    try {
        const CF = Java.use('java.security.cert.CertificateFactory');
        CF.generateCertificate.implementation = function (s) {
            log('TLS!', 'CertificateFactory.generateCertificate()  ← 正在載入憑證');
            return this.generateCertificate(s);
        };
    } catch (e) {}

    // ------------------------------------------------------------ 網路請求（端點覆核，F02）
    try {
        const URL = Java.use('java.net.URL');
        URL.openConnection.overload().implementation = function () {
            log('NET', this.toString());
            return this.openConnection();
        };
    } catch (e) {}

    log('READY', '所有 hook 就緒，等待 App 行為');
});
