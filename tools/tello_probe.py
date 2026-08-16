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
import select
import socket
import sys
import time

# Windows 上 stdout 被重導向時預設為 cp1252，中文會直接拋 UnicodeEncodeError。
# 必須在任何輸出之前處理，否則腳本會在第一行 print 就崩掉。
for _stream in (sys.stdout, sys.stderr):
    try:
        if (_stream.encoding or "").lower().replace("-", "") != "utf8":
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

    def drain(s):
        """清空 socket 緩衝區裡任何待處理的封包，回傳被丟棄的數量。"""
        s.setblocking(False)
        n = 0
        try:
            while True:
                s.recvfrom(4096)
                n += 1
        except (BlockingIOError, OSError):
            pass
        finally:
            s.setblocking(True)
            s.settimeout(timeout)
        return n

    results = {}
    for cmd, desc in QUERIES:
        if cmd.rstrip("?") in _FORBIDDEN:
            continue

        # 送出前先清空緩衝區。無人機會在 8889 上主動推送 DJI 二進位協定封包
        # （起始位元組 0xcc），若不清掉，第一次 recvfrom 會把它當成本次指令的回應，
        # 導致其後每個查詢都收到「上一個指令」的回應，整串平移一格。
        # 這個 bug 在 2026-08-16 的首次實機測試中真的發生了，見 F06。
        dropped = drain(sock)

        try:
            sock.sendto(cmd.encode("utf-8"), (TELLO_IP, CMD_PORT))

            # 只接受文字協定的回應。二進位封包（0xcc 開頭）一律跳過並繼續等，
            # 直到逾時為止 —— 不能假設一送一收。
            deadline = time.time() + timeout
            reply = None
            skipped = dropped
            while time.time() < deadline:
                sock.settimeout(max(0.05, deadline - time.time()))
                data, addr = sock.recvfrom(2048)
                if data[:1] == b"\xcc":          # DJI 二進位協定，非本次查詢的回應
                    skipped += 1
                    continue
                reply = data.decode("utf-8", errors="replace").strip()
                break
            sock.settimeout(timeout)

            if reply is None:
                raise socket.timeout()
            results[cmd] = reply
            if verbose:
                note = f" (略過 {skipped} 個二進位封包)" if skipped else ""
                print(f"  {cmd:<16} -> {reply:<28} # {desc}{note}")
        except socket.timeout:
            results[cmd] = None
            sock.settimeout(timeout)
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


def probe_video(seconds: int, outdir: str, verbose: bool = True) -> dict:
    """
    TC-L1-05 — 視訊串流是否明文可竊聽。

    送出 streamon 後在 11111 收原始串流，檢查 H.264 NAL 起始碼，
    並把 payload 串接存成 .h264 供 ffmpeg 還原畫面。結束後送 streamoff。

    streamon / streamoff 只切換影像輸出，不會轉動馬達。
    但它們會改變裝置狀態，因此本函式僅在明確指定 --video 時執行。
    """
    result = {"packets": 0, "bytes": 0, "nal_start_codes": 0, "file": None}

    # 先綁 11111 再送 streamon，避免開頭的封包漏接
    vid = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    vid.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    vid.settimeout(3.0)
    try:
        vid.bind(("", VIDEO_PORT))
    except OSError as e:
        print(f"[!] 無法綁定 UDP {VIDEO_PORT}: {e}", file=sys.stderr)
        return result

    cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd.settimeout(4.0)
    try:
        cmd.bind(("", CMD_PORT))
    except OSError:
        pass   # 已被本行程其他 socket 佔用時仍可送出

    def send(c):
        try:
            cmd.sendto(c.encode(), (TELLO_IP, CMD_PORT))
            data, _ = cmd.recvfrom(2048)
            return data.decode("utf-8", errors="replace").strip()
        except socket.timeout:
            return "(逾時)"

    if verbose:
        print(f"\n[*] TC-L1-05 視訊串流（{seconds} 秒）")
    print(f"  command   -> {send('command')}")
    print(f"  streamon  -> {send('streamon')}")

    chunks, end = [], time.time() + seconds
    while time.time() < end:
        try:
            data, addr = vid.recvfrom(4096)
            chunks.append(data)
            result["packets"] += 1
            result["bytes"] += len(data)
        except socket.timeout:
            break

    print(f"  streamoff -> {send('streamoff')}")
    vid.close(); cmd.close()

    if chunks:
        blob = b"".join(chunks)
        # H.264 Annex-B 起始碼
        result["nal_start_codes"] = blob.count(b"\x00\x00\x00\x01") + blob.count(b"\x00\x00\x01")
        path = f"{outdir}/TC-L1-05_stream.h264" if outdir else "TC-L1-05_stream.h264"
        with open(path, "wb") as f:
            f.write(blob)
        result["file"] = path
        if verbose:
            print(f"  收到 {result['packets']} 個封包 / {result['bytes']:,} bytes")
            print(f"  H.264 NAL 起始碼: {result['nal_start_codes']} 個")
            print(f"  原始串流已存: {path}")
            print(f"  → 驗證畫面: ffmpeg -i {path} -frames:v 1 frame.png")
    elif verbose:
        print("  未收到任何視訊封包")

    return result


def probe_replay(verbose: bool = True) -> dict:
    """
    TC-L1-06 — 指令重放與來源綁定。

    先以本機埠 8889 送出一個唯讀查詢，記下**位元組完全相同**的封包，
    再從**另一個本機埠**原樣重送，觀察無人機是否照樣接受。

    同時驗證兩件事：
      - 協定有無重放保護（序號／時戳／MAC）
      - 無人機有無把控制端綁定到特定來源
    """
    QUERY = b"battery?"
    out = {"original": None, "replayed_from_alt_port": None, "alt_port": None}

    if verbose:
        print("\n[*] TC-L1-06 指令重放（唯讀查詢，不含飛行指令）")

    a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    a.settimeout(4.0)
    try:
        a.bind(("", CMD_PORT))
    except OSError as e:
        print(f"[!] 無法綁定 {CMD_PORT}: {e}", file=sys.stderr)
        return out
    try:
        a.sendto(b"command", (TELLO_IP, CMD_PORT))
        a.recvfrom(2048)
        a.sendto(QUERY, (TELLO_IP, CMD_PORT))
        data, _ = a.recvfrom(2048)
        out["original"] = data.decode("utf-8", errors="replace").strip()
        if verbose:
            print(f"  原始送出（本機埠 {CMD_PORT}）: {QUERY!r} -> {out['original']}")
    except socket.timeout:
        if verbose:
            print("  原始查詢逾時，中止重放測試")
        a.close()
        return out
    time.sleep(0.4)

    # 自不同來源埠原樣重送同一組位元組。
    #
    # 關鍵：socket a（綁在 8889）必須保持開啟並一起監聽。
    # 首次實測時只在 b 上等回應，結果誤判為「被拒絕」——
    # 實際上無人機接受了指令，只是把回應**寫死送回 8889**。
    # 必須同時監聽兩個 socket 才能分辨「拒絕執行」與「執行但回錯埠」。
    b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    b.bind(("", 0))                      # 由系統指派任意來源埠
    out["alt_port"] = b.getsockname()[1]
    try:
        b.sendto(QUERY, (TELLO_IP, CMD_PORT))
        ready, _, _ = select.select([a, b], [], [], 4.0)
        if not ready:
            out["verdict"] = "no_response"
            if verbose:
                print(f"  重放（來源埠 {out['alt_port']}）：兩個 socket 皆無回應 → 指令未被執行")
        else:
            for s in ready:
                data, _ = s.recvfrom(2048)
                reply = data.decode("utf-8", errors="replace").strip()
                where = "8889（原控制端埠）" if s is a else f"{out['alt_port']}（重放來源埠）"
                out["replayed_from_alt_port"] = reply
                out["reply_arrived_on"] = 8889 if s is a else out["alt_port"]
                if verbose:
                    print(f"  重放送出（來源埠 {out['alt_port']}）: {QUERY!r} -> {reply}")
                    print(f"  回應抵達於: {where}")
            if out.get("reply_arrived_on") == CMD_PORT:
                out["verdict"] = "accepted_reply_to_8889"
                if verbose:
                    print("  → 指令被接受並執行，但回應寫死送回 8889")
                    print("     代表：無來源綁定、無重放保護。攻擊者可自任意埠注入指令，")
                    print("           只需另在 8889 監聽即可收回應；不需回應的指令連監聽都不必。")
            else:
                out["verdict"] = "accepted_reply_to_source"
                if verbose:
                    print("  → 指令被接受，回應送回來源埠")
    except socket.timeout:
        out["verdict"] = "no_response"
    a.close()
    b.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listen", type=int, default=10, help="狀態監聽秒數（預設 10）")
    ap.add_argument("--no-listen", action="store_true", help="跳過狀態監聽")
    ap.add_argument("--timeout", type=float, default=4.0, help="單一指令逾時秒數")
    ap.add_argument("--json", metavar="FILE", help="結果另存 JSON")
    ap.add_argument("--video", type=int, metavar="SEC", default=0,
                    help="TC-L1-05：送 streamon 收 SEC 秒視訊後 streamoff（會改變裝置狀態，需明確指定）")
    ap.add_argument("--replay", action="store_true",
                    help="TC-L1-06：自不同來源埠重放唯讀查詢，測試重放保護與來源綁定")
    ap.add_argument("--outdir", default=".", help="視訊串流輸出目錄")
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

    replay = probe_replay() if args.replay else None
    video = probe_video(args.video, args.outdir) if args.video > 0 else None

    ok = sum(1 for v in results.values() if v)
    print("\n" + "=" * 68)
    print(f"[結論] 在未提供任何認證的情況下，{ok}/{len(results)} 個查詢成功回應，")
    print(f"       並被動接收 {len(states)} 筆遙測廣播。")
    print("       → 控制通道無認證、無裝置綁定。請將本輸出存入 notes/lab-journal.md，")
    print("         並同時用 Wireshark 抓包作為佐證。")
    print("=" * 68)

    if replay:
        v = replay.get("verdict")
        msg = {"accepted_reply_to_8889": "被接受並執行，回應寫死送回 8889 → 無來源綁定、無重放保護",
               "accepted_reply_to_source": "被接受，回應送回來源埠 → 無重放保護",
               "no_response": "無任何回應 → 可能有來源綁定，需以 pcap 覆核"}.get(v, v)
        print(f"[TC-L1-06] 自不同來源埠重放同一位元組序列：{msg}")
    if video:
        print(f"[TC-L1-05] 視訊 11111：{video['packets']} 封包 / "
              f"{video['bytes']:,} bytes / NAL 起始碼 {video['nal_start_codes']} 個"
              f"{' → 明文 H.264' if video['nal_start_codes'] else ''}")
    print("=" * 68)

    if args.json:
        payload = {"queries": results, "state_samples": states}
        if replay:
            payload["replay"] = replay
        if video:
            payload["video"] = video
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n[*] 已寫入 {args.json}")


if __name__ == "__main__":
    main()
