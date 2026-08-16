#!/usr/bin/env python3
"""
Tello 控制通道唯讀探測工具。

用途：在不讓無人機起飛的前提下，驗證控制通道「無認證」這件事。
只送查詢類指令（battery? / sdk? / sn? …）與監聽狀態廣播，**不含任何飛行指令**。
這是刻意的設計：先在地面把無認證存取記錄成證據，飛行測試是另一件事、另一套安全準備。

前提：
    1. 無人機已開機（指示燈閃爍）
    2. 本機已連上 Tello 自建的 Wi-Fi AP（SSID 形如 TELLO-XXXXXX）
    3. 連上後本機通常沒有外部網路 —— 這是正常的，也是研究重點之一

用法：
    python tello_probe.py                 # 探測 + 監聽 10 秒狀態
    python tello_probe.py --listen 30     # 監聽 30 秒
    python tello_probe.py --no-listen     # 只做指令探測
    python tello_probe.py --json out.json # 結果另存 JSON

倫理：僅可對自己持有的無人機執行。見 docs/03-ethics-legal.md。
"""

import argparse
import json
import socket
import sys
import time

TELLO_IP = "192.168.10.1"
CMD_PORT = 8889          # 命令（雙向）
STATE_PORT = 8890        # 狀態廣播（無人機 → 本機）
VIDEO_PORT = 11111       # H.264 視訊串流

# 唯讀查詢指令。'command' 是進入 SDK 模式的必要前置，本身不會使無人機移動。
QUERIES = [
    ("command", "進入 SDK 模式（同時證明無需任何認證即可成為控制端）"),
    ("sdk?",    "SDK 版本"),
    ("sn?",     "機身序號"),
    ("battery?", "電量 %"),
    ("wifi?",   "Wi-Fi 訊噪比"),
    ("speed?",  "目前速度設定"),
    ("time?",   "飛行時間"),
    ("height?", "相對高度"),
    ("temp?",   "機身溫度"),
    ("baro?",   "氣壓計高度"),
    ("tof?",    "ToF 測距"),
    ("attitude?", "姿態（pitch/roll/yaw）"),
    ("acceleration?", "三軸加速度"),
]

# 明確排除的指令。若要做飛行測試，請另外撰寫腳本並先完成 docs/03-ethics-legal.md 的檢查表。
_FORBIDDEN = {"takeoff", "land", "emergency", "up", "down", "left", "right",
              "forward", "back", "cw", "ccw", "flip", "go", "curve", "rc"}


def probe(timeout: float = 4.0, verbose: bool = True) -> dict:
    """依序送出唯讀查詢並收集回應。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.bind(("", CMD_PORT))
    except OSError as e:
        print(f"[!] 無法綁定 UDP {CMD_PORT}: {e}", file=sys.stderr)
        print("    可能是另一個程式（官方 App？其他腳本？）正在佔用。", file=sys.stderr)
        return {}

    results = {}
    for cmd, desc in QUERIES:
        if cmd.rstrip("?") in _FORBIDDEN:
            continue
        try:
            sock.sendto(cmd.encode("utf-8"), (TELLO_IP, CMD_PORT))
            data, addr = sock.recvfrom(2048)
            reply = data.decode("utf-8", errors="replace").strip()
            results[cmd] = reply
            if verbose:
                print(f"  {cmd:<16} -> {reply:<28} # {desc}")
        except socket.timeout:
            results[cmd] = None
            if verbose:
                print(f"  {cmd:<16} -> (逾時)                      # {desc}")
        time.sleep(0.25)

    sock.close()
    return results


def listen_state(seconds: int = 10, verbose: bool = True) -> list:
    """監聽 8890 狀態廣播。這條通道無需送出任何指令即可被動接收 —— 純竊聽。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    try:
        sock.bind(("", STATE_PORT))
    except OSError as e:
        print(f"[!] 無法綁定 UDP {STATE_PORT}: {e}", file=sys.stderr)
        return []

    samples, end = [], time.time() + seconds
    if verbose:
        print(f"\n[*] 被動監聽 UDP {STATE_PORT} 共 {seconds} 秒（不送出任何指令）…")
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(4096)
            raw = data.decode("utf-8", errors="replace").strip()
            samples.append({"from": addr[0], "raw": raw})
            if verbose and len(samples) <= 3:
                print(f"  [{addr[0]}] {raw}")
        except socket.timeout:
            continue
    sock.close()

    if verbose:
        print(f"[*] 收到 {len(samples)} 筆狀態廣播")
        if samples:
            fields = [kv.split(":")[0] for kv in samples[-1]["raw"].split(";") if ":" in kv]
            print(f"[*] 遙測欄位（{len(fields)} 個）: {', '.join(fields)}")
    return samples


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listen", type=int, default=10, help="狀態監聽秒數（預設 10）")
    ap.add_argument("--no-listen", action="store_true", help="跳過狀態監聽")
    ap.add_argument("--timeout", type=float, default=4.0, help="單一指令逾時秒數")
    ap.add_argument("--json", metavar="FILE", help="結果另存 JSON")
    args = ap.parse_args()

    print("=" * 68)
    print(" Tello 控制通道唯讀探測  —  僅限自有設備")
    print(f" 目標 {TELLO_IP}  cmd/{CMD_PORT}  state/{STATE_PORT}  video/{VIDEO_PORT}")
    print("=" * 68)

    print("\n[*] 唯讀指令探測（未提供任何憑證、金鑰或配對程序）")
    results = probe(timeout=args.timeout)

    if not results or all(v is None for v in results.values()):
        print("\n[!] 全部逾時。檢查：無人機是否開機？本機是否已連上 TELLO-XXXXXX？")
        print("    Windows 可用: netsh wlan show interfaces")
        sys.exit(1)

    states = [] if args.no_listen else listen_state(args.listen)

    ok = sum(1 for v in results.values() if v)
    print("\n" + "=" * 68)
    print(f"[結論] 在未提供任何認證的情況下，{ok}/{len(results)} 個查詢成功回應，")
    print(f"       並被動接收 {len(states)} 筆遙測廣播。")
    print("       → 控制通道無認證、無裝置綁定。請將本輸出存入 notes/lab-journal.md，")
    print("         並同時用 Wireshark 抓包作為佐證。")
    print("=" * 68)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"queries": results, "state_samples": states}, f,
                      ensure_ascii=False, indent=2)
        print(f"\n[*] 已寫入 {args.json}")


if __name__ == "__main__":
    main()
