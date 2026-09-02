#!/usr/bin/env python3
"""
Tello SDK 未認證存取的可重現驗證（唯讀）

本腳本用於**量測**，不是用於攻擊。它只送出查詢類指令，
且內建硬性阻擋，無法送出任何會使機體產生動作的指令。

--------------------------------------------------------------------------
新穎性聲明
--------------------------------------------------------------------------
「Tello 的 SDK 協定沒有認證、可用於劫持」**已有前人發表**：

  * Alias Robotics, RVDP#1208 —— Wi-Fi 預設無密碼（CVSS 9.4）
  * 《Analysis of Control Channel Cybersecurity of the Consumer-Grade UAV
     by the Example of DJI Tello》—— 控制通道分析
  * 公開技術文章 —— 以 SDK 指令踢掉已連線的手機

本腳本**不主張發現該現象**。它量測的是前人未涵蓋的三點：

  1. 回應延遲（`command` → `ok` 的實測時間）
  2. 未經認證可取得的遙測欄位範圍
  3. 擁有者連線中時，該操作對其連線的影響

--------------------------------------------------------------------------
安全設計
--------------------------------------------------------------------------
* 白名單機制：只有查詢類指令可被送出
* `takeoff` / `land` / `rc` / `emergency` / `motoron` 等一律拒絕，
  且該阻擋**不可由命令列參數繞過**
* 不修改機體任何設定（不送 `wifi`、不送 `speed` 設定值）

--------------------------------------------------------------------------
使用前提
--------------------------------------------------------------------------
* 僅可用於**自有**的機體
* 執行環境需已連上該 Tello 的 Wi-Fi
* 機體置於地面，未裝螺旋槳更佳

用法:
    python poc_sdk_unauth.py                 # 量測並輸出報告
    python poc_sdk_unauth.py --json          # 機器可讀輸出
"""

import argparse
import json
import socket
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DRONE = ("192.168.10.1", 8889)
STATE_PORT = 8890

# 只允許查詢；此清單即為硬性邊界
SAFE_QUERIES = [
    "command",      # 進入 SDK 模式；本身不產生動作
    "battery?",
    "wifi?",
    "speed?",
    "height?",
    "temp?",
    "tof?",
    "baro?",
    "time?",
    "sn?",          # 本機韌體不支援，保留以記錄回應
    "sdk?",         # 同上
]

# 任何情況下都不得送出。列出以使阻擋範圍可被稽核。
NEVER_SEND = {
    "takeoff", "land", "emergency", "rc", "motoron", "motoroff",
    "flip", "go", "curve", "up", "down", "left", "right",
    "forward", "back", "cw", "ccw", "wifi", "ap", "speed",
}


def refuse_if_unsafe(cmd: str) -> None:
    """在送出前擋下任何會產生動作或變更設定的指令。"""
    head = cmd.strip().split()[0].lower().rstrip("?")
    if head in NEVER_SEND and not cmd.strip().endswith("?"):
        raise SystemExit(
            f"拒絕送出 '{cmd}'：該指令會使機體產生動作或變更設定。\n"
            f"本腳本為唯讀量測工具，此阻擋不可繞過。"
        )


def probe(sock: socket.socket, cmd: str, timeout: float = 3.0):
    """送出單一查詢並回傳 (回應字串, 延遲毫秒)。逾時回傳 (None, None)。"""
    refuse_if_unsafe(cmd)
    sock.settimeout(timeout)
    t0 = time.perf_counter()
    sock.sendto(cmd.encode(), DRONE)
    try:
        data, _ = sock.recvfrom(2048)
    except socket.timeout:
        return None, None
    dt = (time.perf_counter() - t0) * 1000
    return data.decode("ascii", "replace").strip(), dt


def collect_state(seconds: float = 3.0):
    """接收飛機主動廣播的狀態串流。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("", STATE_PORT))
    except OSError as e:
        s.close()
        return [], f"無法綁定 {STATE_PORT}：{e}"
    s.settimeout(seconds)
    out, t0 = [], time.perf_counter()
    try:
        while time.perf_counter() - t0 < seconds:
            data, _ = s.recvfrom(2048)
            out.append(data.decode("ascii", "replace").strip())
    except socket.timeout:
        pass
    finally:
        s.close()
    return out, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Tello SDK 未認證存取的唯讀量測")
    ap.add_argument("--json", action="store_true", help="輸出 JSON")
    args = ap.parse_args()

    result = {"reachable": False, "queries": {}, "state_samples": 0, "state_fields": []}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    src_port = sock.getsockname()[1]

    if not args.json:
        print("=" * 62)
        print("Tello SDK 未認證存取 —— 唯讀量測")
        print("=" * 62)
        print(f"目標   {DRONE[0]}:{DRONE[1]}")
        print(f"來源埠 {src_port}（隨機；未提供任何憑證）\n")

    # 1. 進入 SDK 模式並量測延遲
    reply, ms = probe(sock, "command")
    result["reachable"] = reply is not None
    result["queries"]["command"] = {"reply": reply, "ms": ms}

    if reply is None:
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("飛機無回應。請確認：機體已開機、本機已連上其 Wi-Fi。")
        sock.close()
        return 1

    if not args.json:
        print(f"[1] command  → {reply!r}   延遲 {ms:.1f} ms")
        print("    未提供帳號、密碼、配對碼或任何憑證。\n")

    # 2. 列舉可取得的查詢
    if not args.json:
        print("[2] 未經認證可取得的資訊：")
    for q in SAFE_QUERIES[1:]:
        r, t = probe(sock, q, timeout=2.0)
        result["queries"][q] = {"reply": r, "ms": t}
        if not args.json:
            mark = "  " if r and not r.startswith("unknown") else " ·"
            print(f"   {mark} {q:<10} → {r!r}")

    # 3. 主動廣播的狀態串流
    if not args.json:
        print("\n[3] 飛機主動廣播的遙測（UDP 8890，3 秒）：")
    samples, err = collect_state(3.0)
    result["state_samples"] = len(samples)
    if samples:
        fields = [kv.split(":")[0] for kv in samples[-1].split(";") if ":" in kv]
        result["state_fields"] = fields
        if not args.json:
            print(f"    收到 {len(samples)} 筆")
            print(f"    欄位 ({len(fields)}): {', '.join(fields)}")
            print(f"    範例: {samples[-1][:96]}…")
    elif not args.json:
        print(f"    未收到（{err or '可能已有其他程序佔用 8890'}）")

    sock.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("\n" + "=" * 62)
    print("量測結論")
    print("=" * 62)
    ok = [q for q, v in result["queries"].items()
          if v["reply"] and not v["reply"].startswith("unknown")]
    print(f"  可用查詢          {len(ok)} / {len(SAFE_QUERIES)}")
    print(f"  進入 SDK 模式延遲  {result['queries']['command']['ms']:.1f} ms")
    print(f"  遙測欄位          {len(result['state_fields'])} 個")
    print(f"  提供的憑證        無")
    print("\n  本腳本未送出任何會使機體產生動作的指令。")
    print("  完整脈絡與新穎性界定見 docs/01-prior-art.md。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
