/*
 * 只攔 Android／Java 框架 API —— 繞過愛加密的方法抽取（F03）
 *
 * 為何有效：
 *   殼抽走的是 App 自有方法的主體，且類別名經過混淆（如 d.a()）。
 *   但 App 終究得呼叫框架 API 才能做事，而**殼不會、也無法保護框架**。
 *   因此不必脫殼，攔框架即可回答多數未決問題。
 *
 * 對應的未決問題：
 *   MessageDigest          → F10：mydjiflight 的 signature 欄位如何產生
 *   SharedPreferences      → F05：AreaCodeTello 的寫入來源
 *   WebView / AssetManager → F05：政策語系如何選擇
 *   URL / URLConnection    → F02：執行期組出的完整端點清單
 *
 * 須以 attach 模式使用；spawn 注入會與殼衝突使 App 立即死亡（見 F03）。
 */
'use strict';

function hex(b) {
    if (!b) return '(null)';
    var s = '', n = Math.min(b.length, 64);
    for (var i = 0; i < n; i++) s += ('0' + (b[i] & 0xff).toString(16)).slice(-2);
    return s + (b.length > n ? '…(' + b.length + 'B)' : '');
}
function ascii(b) {
    if (!b) return '';
    var s = '', n = Math.min(b.length, 120), printable = 0;
    for (var i = 0; i < n; i++) {
        var c = b[i] & 0xff;
        if (c >= 32 && c < 127) { s += String.fromCharCode(c); printable++; }
        else s += '.';
    }
    return printable > n * 0.7 ? s : '';
}

Java.perform(function () {
    var hooked = [];

    // ---------------------------------------------------- F10：signature 如何產生
    try {
        var MD = Java.use('java.security.MessageDigest');
        MD.digest.overload().implementation = function () {
            var out = this.digest();
            console.log('[MD ] ' + this.getAlgorithm() + ' digest() -> ' + hex(out));
            return out;
        };
        MD.update.overload('[B').implementation = function (b) {
            var a = ascii(b);
            console.log('[MD ] update(' + b.length + 'B) ' + (a ? '"' + a + '"' : hex(b)));
            return this.update(b);
        };
        MD.digest.overload('[B').implementation = function (b) {
            var a = ascii(b);
            console.log('[MD ] ' + this.getAlgorithm() + ' digest(' + b.length + 'B) ' +
                        (a ? '"' + a + '"' : hex(b)));
            var out = this.digest(b);
            console.log('[MD ]   -> ' + hex(out));
            return out;
        };
        hooked.push('MessageDigest');
    } catch (e) { console.log('[SKIP] MessageDigest: ' + e.message); }

    // ---------------------------------------------------- F05：AreaCodeTello 寫入來源
    try {
        var Ed = Java.use('android.app.SharedPreferencesImpl$EditorImpl');
        Ed.putString.implementation = function (k, v) {
            console.log('[PREF] putString("' + k + '", "' + v + '")');
            return this.putString(k, v);
        };
        hooked.push('SharedPreferences.putString');
    } catch (e) { console.log('[SKIP] SharedPreferences: ' + e.message); }

    // ---------------------------------------------------- F05：地區判定的來源
    ['android.telephony.TelephonyManager'].forEach(function (cn) {
        try {
            var T = Java.use(cn);
            ['getSimCountryIso', 'getNetworkCountryIso', 'getSimOperator', 'getNetworkOperator']
                .forEach(function (m) {
                    if (!T[m]) return;
                    T[m].overloads.forEach(function (ov) {
                        ov.implementation = function () {
                            var r = ov.apply(this, arguments);
                            console.log('[GEO ] ' + m + '() -> ' + r);
                            return r;
                        };
                    });
                });
            hooked.push('TelephonyManager');
        } catch (e) { console.log('[SKIP] ' + cn + ': ' + e.message); }
    });

    // ---------------------------------------------------- F05：政策檔如何被讀取
    try {
        var AM = Java.use('android.content.res.AssetManager');
        AM.open.overload('java.lang.String').implementation = function (n) {
            console.log('[ASSET] open("' + n + '")');
            return this.open(n);
        };
        hooked.push('AssetManager.open');
    } catch (e) { console.log('[SKIP] AssetManager: ' + e.message); }

    try {
        var WV = Java.use('android.webkit.WebView');
        WV.loadUrl.overload('java.lang.String').implementation = function (u) {
            console.log('[WEB ] loadUrl("' + u + '")');
            return this.loadUrl(u);
        };
        hooked.push('WebView.loadUrl');
    } catch (e) { console.log('[SKIP] WebView: ' + e.message); }

    // ---------------------------------------------------- F02：執行期組出的端點
    try {
        var U = Java.use('java.net.URL');
        U.$init.overload('java.lang.String').implementation = function (u) {
            console.log('[URL ] ' + u);
            return this.$init(u);
        };
        hooked.push('URL');
    } catch (e) { console.log('[SKIP] URL: ' + e.message); }

    console.log('[READY] 已掛載: ' + hooked.join(', '));
});
