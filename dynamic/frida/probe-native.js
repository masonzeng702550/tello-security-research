/*
 * 最小侵入版：只在 native 層攔截函式庫載入。
 *
 * 為什麼要有這一版：
 *   probe-launch.js 的 Java 層 hook 會讓加殼的 App 崩潰——
 *   1. hook java.lang.System.loadLibrary → overload 分派錯亂，
 *      libframework-connectivity-jni.so 解析失敗（2026-08-17 實測）
 *   2. hook java.lang.ClassLoader.loadClass → 干擾愛加密的執行期 dex 還原，
 *      ART 驗證器以 VerifyError 拒絕 MyApplication（同日實測）
 *
 *   本版完全不碰 Java 方法分派，只用 Interceptor 掛 native 匯出符號，
 *   對 App 行為的影響最小。
 *
 * 能回答的問題：
 *   F01 — liblocSDK8a.so / libRoadLineRebuildAPI.so / libpatchtool.so
 *         在執行期是否真的被載入？（字串池已無其名，但檔案仍打包）
 *   F03 — 加殼器解密出的 dex 從何處載入？
 */

'use strict';

const seen = new Set();

// Frida 17 移除了 Module.findExportByName(null, ...)
function globalExport(sym) {
    if (typeof Module.findGlobalExportByName === 'function') return Module.findGlobalExportByName(sym);
    if (typeof Module.findExportByName === 'function') return Module.findExportByName(null, sym);
    return null;
}

// F01 的觀測標的：這些 .so 仍打包在 APK，但 dex 字串池已無對應名稱
const WATCH = /locSDK|RoadLine|patchtool|bugly|baidu|dreamDrone/i;
// F03 的觀測標的：執行期解密產生的 dex
const DEX = /\.jar$|\.dex$|DexFile|\.odex$/i;

['dlopen', 'android_dlopen_ext'].forEach(function (sym) {
    const p = globalExport(sym);
    if (!p) { console.log(`[WARN] 找不到 ${sym}`); return; }
    Interceptor.attach(p, {
        onEnter(args) { this.path = args[0].isNull() ? null : args[0].readCString(); },
        onLeave(retval) {
            if (!this.path) return;
            if (seen.has(this.path)) return;
            seen.add(this.path);
            const name = this.path.split('/').pop();
            const ok = !retval.isNull();
            let tag = 'LIB ';
            if (WATCH.test(name)) tag = 'HIT!';
            else if (DEX.test(this.path)) tag = 'DEX ';
            console.log(`[${tag}] ${ok ? '載入' : '失敗'}  ${this.path}`);
        }
    });
});

// 檔案開啟：追蹤憑證（F04）與未被 dex 引用的資產（F07）是否真的被讀取
['open', 'openat'].forEach(function (sym) {
    const p = globalExport(sym);
    if (!p) return;
    const idx = (sym === 'openat') ? 1 : 0;
    Interceptor.attach(p, {
        onEnter(args) { this.f = args[idx].isNull() ? null : args[idx].readCString(); },
        onLeave() {
            if (!this.f) return;
            if (!/\.(cer|crt|pem|jet|bin|ajm)$|ijiami|Privacy|Policy/i.test(this.f)) return;
            if (seen.has('F:' + this.f)) return;
            seen.add('F:' + this.f);
            console.log(`[FILE] ${this.f}`);
        }
    });
});

console.log('[READY] native hook 就緒（不干涉 Java 分派）');
