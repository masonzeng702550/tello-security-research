#!/usr/bin/env python3
"""
以實測封包反推 Tello 協定的 CRC 參數。

為什麼不直接沿用公開文件的參數：
    公開的 Tello 協定分析散見於各處，參數未必適用於本機的韌體版本。
    本工具改以「暴力搜尋 + 全量驗證」求解——
    若求得的參數能對本次擷取的每一個封包都算出正確校驗值，
    該參數就是被證明的，而非被假設的。

CRC8  覆蓋 byte[0:3]，結果寫在 byte[3]
CRC16 覆蓋 byte[0:-2]，結果寫在最後兩個位元組（小端序）
"""
import sys, subprocess, shutil, argparse
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_packets(pcap):
    tshark = shutil.which("tshark") or r"C:\Program Files\Wireshark\tshark.exe"
    p = subprocess.run(
        [tshark, "-r", pcap, "-Y", "udp", "-T", "fields", "-e", "data.data"],
        capture_output=True, text=True)
    out = []
    for line in p.stdout.splitlines():
        line = line.strip().replace(":", "")
        if not line:
            continue
        try:
            b = bytes.fromhex(line)
        except ValueError:
            continue
        if b and b[0] == 0xCC and len(b) >= 11:
            out.append(b)
    return out


def make_table8(poly, reflect):
    tbl = []
    for i in range(256):
        c = i
        for _ in range(8):
            if reflect:
                c = (c >> 1) ^ (poly if c & 1 else 0)
            else:
                c = ((c << 1) & 0xFF) ^ (poly if c & 0x80 else 0)
        tbl.append(c & 0xFF)
    return tbl


def crc8(data, tbl, init, reflect):
    c = init
    for b in data:
        c = tbl[(c ^ b) & 0xFF] if reflect else tbl[((c << 0) ^ b) & 0xFF]
    return c & 0xFF


def make_table16(poly, reflect):
    tbl = []
    for i in range(256):
        if reflect:
            c = i
            for _ in range(8):
                c = (c >> 1) ^ (poly if c & 1 else 0)
        else:
            c = i << 8
            for _ in range(8):
                c = ((c << 1) & 0xFFFF) ^ (poly if c & 0x8000 else 0)
        tbl.append(c & 0xFFFF)
    return tbl


def crc16(data, tbl, init, reflect):
    c = init
    for b in data:
        if reflect:
            c = (c >> 8) ^ tbl[(c ^ b) & 0xFF]
        else:
            c = ((c << 8) & 0xFFFF) ^ tbl[((c >> 8) ^ b) & 0xFF]
    return c & 0xFFFF


def solve_crc8(pkts, probe=40):
    sample = pkts[:probe]
    for reflect in (True, False):
        for poly in range(256):
            tbl = make_table8(poly, reflect)
            for init in range(256):
                if all(crc8(p[0:3], tbl, init, reflect) == p[3] for p in sample):
                    return poly, init, reflect
    return None


def solve_crc16(pkts, probe=40):
    sample = pkts[:probe]
    # 先試公開文件常見的參數，命中即省去暴力搜尋
    KNOWN = [(0x3d65, 0x3692, True), (0x8408, 0x3692, True),
             (0xa001, 0x0000, True), (0x1021, 0xffff, False)]
    for poly, init, reflect in KNOWN:
        tbl = make_table16(poly, reflect)
        if all(crc16(p[0:-2], tbl, init, reflect) ==
               int.from_bytes(p[-2:], "little") for p in sample):
            return poly, init, reflect, "已知參數命中"
    # 暴力：poly 全掃，init 取常見候選
    INITS = [0x0000, 0xffff, 0x3692, 0x1d0f, 0xb2aa, 0x89ec, 0xc6c6, 0x800d, 0x77aa]
    tiny = pkts[:4]
    for reflect in (True, False):
        for poly in range(0x10000):
            tbl = make_table16(poly, reflect)
            for init in INITS:
                if all(crc16(p[0:-2], tbl, init, reflect) ==
                       int.from_bytes(p[-2:], "little") for p in tiny):
                    if all(crc16(p[0:-2], tbl, init, reflect) ==
                           int.from_bytes(p[-2:], "little") for p in sample):
                        return poly, init, reflect, "暴力搜尋求得"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcap")
    args = ap.parse_args()

    pkts = load_packets(args.pcap)
    print(f"載入 0xcc 封包 {len(pkts):,} 個\n")
    if not pkts:
        return 1

    print("=== 求解 CRC8（標頭）===")
    r8 = solve_crc8(pkts)
    if not r8:
        print("  未求得")
        return 1
    poly8, init8, ref8 = r8
    print(f"  poly=0x{poly8:02x}  init=0x{init8:02x}  reflect={ref8}")
    tbl8 = make_table8(poly8, ref8)
    ok8 = sum(1 for p in pkts if crc8(p[0:3], tbl8, init8, ref8) == p[3])
    print(f"  全量驗證: {ok8:,}/{len(pkts):,}  ({100*ok8/len(pkts):.4f}%)")

    print("\n=== 求解 CRC16（全封包）===")
    r16 = solve_crc16(pkts)
    if not r16:
        print("  未求得")
        return 1
    poly16, init16, ref16, how = r16
    print(f"  poly=0x{poly16:04x}  init=0x{init16:04x}  reflect={ref16}   ({how})")
    tbl16 = make_table16(poly16, ref16)
    ok16 = sum(1 for p in pkts
               if crc16(p[0:-2], tbl16, init16, ref16) == int.from_bytes(p[-2:], "little"))
    print(f"  全量驗證: {ok16:,}/{len(pkts):,}  ({100*ok16/len(pkts):.4f}%)")

    print("\n=== 結論 ===")
    if ok8 == len(pkts) and ok16 == len(pkts):
        print("  兩組 CRC 皆對全部封包吻合 → 編碼器可據此建構，且已被實測資料證明")
    else:
        print("  存在不吻合的封包，需進一步分析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
