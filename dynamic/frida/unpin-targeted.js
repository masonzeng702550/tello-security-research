/*
 * 針對性 SSL pinning 繞過 — 用於取得 mydjiflight.dji.com 的 payload
 *
 * 為什麼不用通用的 frida-multiple-unpinning：
 *   那類腳本會 hook 數十個 Java 類別。本 App 以愛加密加殼，
 *   先前實測顯示大範圍的 Java hook 會導致崩潰
 *   （System.loadLibrary → UnsatisfiedLinkError；
 *     ClassLoader.loadClass → VerifyError，見 F03/F08）。
 *   故此處只針對 TLS 驗證的三個決策點，把影響面壓到最小。
 *
 * 攔截點：
 *   1. SSLContext.init          — 用寬鬆 TrustManager 取代 App 提供的
 *   2. TrustManagerImpl.verifyChain — Conscrypt 的實際鏈驗證（Android 7+ 的關鍵點）
 *   3. okhttp3.CertificatePinner.check — OkHttp 的明示 pin 檢查
 *
 * ⚠️ 本腳本僅用於自有裝置上的自有 App 分析。
 */

'use strict';

let hooked = [];
function ok(n) { hooked.push(n); console.log('[HOOK] ' + n); }
function warn(n, e) { console.log('[SKIP] ' + n + '  (' + e + ')'); }

/*
 * 延遲掛載（DELAY_MS）——這是為加殼 App 而設的。
 *
 * 若在 spawn 後立刻 Java.perform，會與愛加密的 Application 實體化撞在一起：
 * 殼在 LoadedApk.makeApplicationInner 期間解密並載入 Anonymous-DexFile，
 * 此時註冊新類別（Java.registerClass）或替換核心方法會導致
 * ART 驗證器拒絕還原後的類別，App 崩潰（2026-08-17 實測兩次）。
 *
 * 時序（實測）：
 *   t=0      spawn
 *   t≈1–2s   殼完成 dex 還原與 Application 建立
 *   t≈4–5s   App 發出首波網路請求（mydjiflight / vgabc）
 * → 在 t≈2.5s 掛載可避開衝突，且趕得上攔截請求。
 *
 * 若仍崩潰，往上調；若錯過請求，往下調。
 */
const DELAY_MS = 2500;

function installHooks() {
Java.perform(function () {

    // ---------------------------------------------------------- 1. SSLContext.init
    try {
        const SSLContext = Java.use('javax.net.ssl.SSLContext');
        const TrustManager = Java.registerClass({
            name: 'com.research.PermissiveTM',
            implements: [Java.use('javax.net.ssl.X509TrustManager')],
            methods: {
                checkClientTrusted(chain, authType) {},
                checkServerTrusted(chain, authType) {
                    try {
                        if (chain && chain.length) {
                            console.log('[CERT] 接受鏈，leaf CN = ' +
                                chain[0].getSubjectDN().getName());
                        }
                    } catch (e) {}
                },
                getAcceptedIssuers() { return []; }
            }
        });
        const tms = Java.array('Ljavax.net.ssl.TrustManager;', [TrustManager.$new()]);
        const init = SSLContext.init.overload(
            '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;',
            'java.security.SecureRandom');
        init.implementation = function (km, tm, sr) {
            console.log('[TLS ] SSLContext.init — 以寬鬆 TrustManager 取代');
            return init.call(this, km, tms, sr);
        };
        ok('SSLContext.init');
    } catch (e) { warn('SSLContext.init', e); }

    // ---------------------------------------------------------- 2. Conscrypt 鏈驗證
    // Android 7+ 的實際驗證落點。App 自建的 TrustManager 最終仍會走到這裡。
    ['com.android.org.conscrypt.TrustManagerImpl',
     'com.google.android.gms.org.conscrypt.TrustManagerImpl'].forEach(function (cls) {
        try {
            const TMI = Java.use(cls);
            TMI.verifyChain.implementation = function (untrusted, trustAnchor, host, clientAuth, ocsp, tlsSct) {
                console.log('[TLS ] verifyChain 放行 — host=' + host);
                return untrusted;
            };
            ok(cls + '.verifyChain');
        } catch (e) { warn(cls, e); }
    });

    // ---------------------------------------------------------- 3. OkHttp 明示 pin
    ['okhttp3.CertificatePinner', 'com.squareup.okhttp.CertificatePinner'].forEach(function (cls) {
        try {
            const CP = Java.use(cls);
            CP.check.overloads.forEach(function (m) {
                m.implementation = function () {
                    console.log('[TLS ] CertificatePinner.check 略過 — ' + arguments[0]);
                    return;
                };
            });
            ok(cls + '.check');
        } catch (e) { warn(cls, e); }
    });

    // ---------------------------------------------------------- 4. HostnameVerifier
    try {
        const HV = Java.use('javax.net.ssl.HttpsURLConnection');
        HV.setDefaultHostnameVerifier.implementation = function (v) {
            console.log('[TLS ] setDefaultHostnameVerifier 攔截');
            return;
        };
        ok('HttpsURLConnection.setDefaultHostnameVerifier');
    } catch (e) { warn('HostnameVerifier', e); }

    console.log('[READY] 已掛載 ' + hooked.length + ' 個攔截點');
});
}

console.log('[WAIT ] ' + DELAY_MS + ' ms 後掛載，先讓加殼器完成 dex 還原');
setTimeout(installHooks, DELAY_MS);
