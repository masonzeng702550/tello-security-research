#!/usr/bin/env python3
"""
解析並解碼 DJI_LOG_V3 飛行日誌（Tello 的 droneLog/*.DAT）。

混淆方式（本研究實測求得，非引用外部資料）：
    每筆記錄的酬載以**單一位元組 XOR**混淆，
    而該金鑰**就存放在酬載的 byte[2]**，隨記錄一同送出。

    亦即：plain[i] = cipher[i] ^ cipher[2]

    這不是密碼學保護——金鑰與密文放在一起，任何人都能還原。

記錄框架：
    0x55 | 長度(1) | 0x00 | 型別(1) | 酬載…

用法:
    python decode_dji_dat.py <flight.DAT> [--type 0x8b] [--limit 20]
"""
import sys
import struct
import argparse
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

START_OFFSET = 1256          # 檔頭之後的第一筆記錄；實測值


def parse(data, start=START_OFFSET):
    """切出所有記錄，回傳 (型別, 原始酬載, 解碼後酬載)。"""
    out, off = [], start
    while off + 4 < len(data):
        if data[off] != 0x55:
            nxt = data.find(b"\x55", off + 1)
            if nxt < 0:
                break
            off = nxt
            continue
        ln = data[off + 1]
        if ln < 5 or off + ln > len(data):
            off += 1
            continue
        payload = data[off + 4: off + ln]
        if len(payload) >= 3:
            key = payload[2]
            plain = bytes(b ^ key for b in payload)
        else:
            plain = payload
        out.append((data[off + 3], payload, plain))
        off += ln
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dat")
    ap.add_argument("--type", help="只顯示指定型別，如 0x8b")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    data = open(args.dat, "rb").read()
    if b"DJI_LOG_V3" not in data[:4096]:
        print("⚠ 檔頭未見 DJI_LOG_V3 標記，仍嘗試解析")

    recs = parse(data)
    print(f"記錄 {len(recs):,} 筆，檔案 {len(data):,} bytes\n")

    zeros = sum(1 for _, _, p in recs for b in p if b == 0)
    total = sum(len(p) for _, _, p in recs)
    print(f"解碼後為 0 的位元組: {100*zeros/max(total,1):.1f}%  （隨機約 0.4%，"
          f"偏高即代表金鑰正確）\n")

    by = defaultdict(list)
    for t, raw, plain in recs:
        by[t].append(plain)

    print(f"=== 型別分布（前 12）===")
    print(f"  {'型別':<8}{'筆數':>9}{'長度':>7}")
    for t, lst in sorted(by.items(), key=lambda kv: -len(kv[1]))[:12]:
        L = Counter(len(x) for x in lst).most_common(1)[0][0]
        print(f"  0x{t:02x}{len(lst):>11,}{L:>7}")

    if args.type:
        t = int(args.type, 16)
        lst = by.get(t, [])
        print(f"\n=== 型別 0x{t:02x} 解碼後（前 {args.limit} 筆）===")
        for x in lst[:args.limit]:
            print(f"  {x.hex()}")


if __name__ == "__main__":
    sys.exit(main())
