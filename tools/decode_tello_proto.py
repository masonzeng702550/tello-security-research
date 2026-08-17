#!/usr/bin/env python3
"""
解析 Tello App 私有二進位協定（非 SDK 文字協定）。

背景：
    F06 測的是 Tello SDK 的文字協定（8889 收發 "command"/"takeoff" 等）。
    但官方 App 實際跑的是另一套二進位協定，同樣在 UDP 8889。
    本工具解析後者，用於評估重放與注入的可行性。

封包結構（自實測流量推導，與公開的 Tello 協定分析一致）：
    byte 0      0xcc            魔術位元組
    byte 1-2    length << 3     小端序，13 bits
    byte 3      CRC8            前三個位元組的校驗
    byte 4      pktType         封包類型/方向旗標
    byte 5-6    cmdID           小端序命令碼
    byte 7-8    seq             序號，小端序
    byte 9..-3  payload
    byte -2..   CRC16

用法:
    python decode_tello_proto.py <pcap> [--limit N]
"""
import sys
import argparse
import struct
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 由實測流量觀察到的命令碼。未出現在本次擷取中的不列入，避免臆測。
CMD_NAMES = {
    0x0050: "搖桿控制 (stick)",
    0x0046: "查詢",
    0x0056: "電量查詢",
    0x0054: "設定",
    0x0026: "狀態回報",
    0x0021: "連線請求",
    0x0053: "時間同步",
}


def parse(data: bytes):
    """解析單一封包，失敗回傳 None。"""
    if len(data) < 11 or data[0] != 0xCC:
        return None
    length = struct.unpack("<H", data[1:3])[0] >> 3
    return {
        "len_field": length,
        "actual_len": len(data),
        "crc8": data[3],
        "ptype": data[4],
        "cmd": struct.unpack("<H", data[5:7])[0],
        "seq": struct.unpack("<H", data[7:9])[0],
        "payload": data[9:-2],
        "crc16": struct.unpack("<H", data[-2:])[0],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcap")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    # 以 tshark 取出欄位，避免額外的 Python 相依（scapy 等）。
    # tshark 是本專案既有的分析工具，Wireshark 安裝後即具備。
    import subprocess, shutil

    tshark = shutil.which("tshark") or r"C:\Program Files\Wireshark\tshark.exe"
    proc = subprocess.run(
        [tshark, "-r", args.pcap, "-Y", "udp",
         "-T", "fields", "-e", "frame.time_relative",
         "-e", "udp.dstport", "-e", "data.data"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        print("tshark 執行失敗：", proc.stderr[:400])
        return 1

    ctrl, telem, bad = [], [], 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or not parts[2]:
            continue
        try:
            raw = bytes.fromhex(parts[2].replace(":", ""))
        except ValueError:
            continue
        if not raw or raw[0] != 0xCC:
            continue
        info = parse(raw)
        if not info:
            bad += 1
            continue
        info["t"] = float(parts[0])
        (ctrl if parts[1] == "8889" else telem).append(info)

    t0 = min([x["t"] for x in ctrl + telem], default=0)

    for label, rows in (("手機 → 飛機（控制）", ctrl), ("飛機 → 手機（遙測）", telem)):
        print(f"\n{'='*66}\n{label}   共 {len(rows)} 個 0xcc 封包\n{'='*66}")
        if not rows:
            continue

        c = Counter(r["cmd"] for r in rows)
        print("\n-- 命令碼分布 --")
        for cmd, n in c.most_common(12):
            name = CMD_NAMES.get(cmd, "")
            print(f"   0x{cmd:04x} ({cmd:>5})  {n:>6} 筆   {name}")

        print("\n-- 序號行為（重放可行性的關鍵）--")
        by_cmd = defaultdict(list)
        for r in rows:
            by_cmd[r["cmd"]].append(r["seq"])
        for cmd, seqs in sorted(by_cmd.items(), key=lambda kv: -len(kv[1]))[:6]:
            uniq = len(set(seqs))
            name = CMD_NAMES.get(cmd, "")
            if uniq == 1:
                verdict = f"★ 固定為 {seqs[0]} —— 無防重放"
            elif uniq == len(seqs):
                verdict = f"每筆遞增/唯一（{min(seqs)}–{max(seqs)}）"
            else:
                verdict = f"{uniq} 種取值，範圍 {min(seqs)}–{max(seqs)}"
            print(f"   0x{cmd:04x} {name:<16} {len(seqs):>6} 筆 → {verdict}")

        print("\n-- 前 6 個封包 --")
        for r in rows[:6]:
            print(f"   t={r['t']-t0:7.3f}s cmd=0x{r['cmd']:04x} seq={r['seq']:<5} "
                  f"type=0x{r['ptype']:02x} payload={r['payload'].hex()}")

    print(f"\n無法解析的 0xcc 封包: {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
