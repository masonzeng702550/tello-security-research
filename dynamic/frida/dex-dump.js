/*
 * 自記憶體傾印還原後的 DEX —— 解開愛加密的殼（F03）
 *
 * 兩個關鍵設計，皆源自實測失敗的教訓：
 *
 * 1. **attach 而非 spawn**
 *    以 `frida -f` 於啟動時注入會使 App 立即死亡（2026-08-26 實測，
 *    即使腳本內容為空亦然）——與 F03／F08 記載的殼衝突一致。
 *    改為等 App 完全啟動後再 attach，App 可穩定存活。
 *
 * 2. **經 DexFile.mCookie 精準定位，而非掃描記憶體**
 *    本行程的匿名記憶體達 1,363 MB，全域掃描 DEX magic 不可行。
 *    改由 ART 自己的資料結構取得每個 dex 的位址與長度。
 *
 * 輸出寫入 App 自己的私有目錄——App 無權寫入 /data/local/tmp（SELinux）。
 *
 * ⚠️ 僅用於自有裝置上的自有 App 分析。
 */
'use strict';

const OUT_DIR = '/data/data/com.ryzerobotics.tello/files/dexdump';

function hdrSize(p) {
    // 驗證 DEX 檔頭並回傳 file_size；失敗回 0
    try {
        if (p.readU8() !== 0x64) return 0;                    // 'd'
        if (p.add(1).readU8() !== 0x65) return 0;             // 'e'
        if (p.add(2).readU8() !== 0x78) return 0;             // 'x'
        if (p.add(3).readU8() !== 0x0a) return 0;             // '\n'
        if (p.add(36).readU32() !== 0x70) return 0;           // header_size
        if (p.add(40).readU32() !== 0x12345678) return 0;     // endian_tag
        const sz = p.add(32).readU32();                       // file_size
        if (sz < 0x70 || sz > 128 * 1024 * 1024) return 0;
        return sz;
    } catch (e) { return 0; }
}

Java.perform(function () {
    try { new File(OUT_DIR + '/.keep', 'wb').close(); } catch (e) {}

    const seen = {}, out = [];
    let loaders = 0;

    Java.enumerateClassLoadersSync().forEach(function (cl) {
        loaders++;
        let pathList;
        try { pathList = cl.pathList.value; } catch (e) { return; }
        if (!pathList) return;
        let elements;
        try { elements = pathList.dexElements.value; } catch (e) { return; }
        if (!elements) return;

        for (let i = 0; i < elements.length; i++) {
            let dexFile;
            try { dexFile = elements[i].dexFile.value; } catch (e) { continue; }
            if (!dexFile) continue;
            let cookie;
            try { cookie = dexFile.mCookie.value; } catch (e) { continue; }
            if (!cookie) continue;

            // mCookie 為 long[]：[0] 是 OatFile*，其後為 DexFile*
            for (let j = 0; j < cookie.length; j++) {
                const raw = cookie[j];
                if (!raw || raw.toString() === '0') continue;
                const dexFilePtr = ptr(raw.toString());

                // art::DexFile 的前幾個欄位含 begin_（const uint8_t*）與 size_
                // 版本間位移不同，故逐一試探並以 DEX 檔頭驗證
                for (let off = 0; off <= 0x20; off += 8) {
                    let cand;
                    try { cand = dexFilePtr.add(off).readPointer(); } catch (e) { continue; }
                    if (cand.isNull()) continue;
                    const sz = hdrSize(cand);
                    if (!sz) continue;
                    const key = cand.toString();
                    if (seen[key]) break;
                    seen[key] = 1;
                    out.push({ addr: cand, size: sz, loader: cl.$className });
                    break;
                }
            }
        }
    });

    console.log('[INFO] 走訪 ClassLoader ' + loaders + ' 個');
    console.log('[INFO] 定位到 DEX ' + out.length + ' 個');

    out.sort(function (a, b) { return b.size - a.size; });
    let n = 0;
    out.forEach(function (d) {
        const path = OUT_DIR + '/dex_' + d.addr.toString(16) + '_' + d.size + '.dex';
        try {
            const f = new File(path, 'wb');
            f.write(d.addr.readByteArray(d.size));
            f.flush(); f.close();
            n++;
            console.log('[DUMP] ' + String(Math.round(d.size / 1024)).padStart(6) +
                        ' KB  ' + d.loader.replace(/^.*\./, '') + '  -> ' + path.replace(/^.*\//, ''));
        } catch (e) {
            console.log('[FAIL] ' + d.addr + ' : ' + e.message);
        }
    });
    console.log('[DONE] 寫出 ' + n + ' 個');
});
