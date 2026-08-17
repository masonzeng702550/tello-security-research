#!/usr/bin/env python3
"""
比對兩個 mitmproxy flow 檔的請求內容。

用於 A/B 對照測試：找出兩組之間端點、欄位、payload 的差異。
輸出刻意包含「兩組相同」的項目，因為「沒有差異」本身就是結論。

用法:
    python diff_flows.py A.flow B.flow [--label-a A] [--label-b B]
"""
import sys
import argparse
from collections import Counter

from mitmproxy import io as mio
from mitmproxy import http

# Windows 主控台預設 cp950，直接 print 中文會 UnicodeEncodeError
# （本專案 tello_probe.py 已踩過同一個坑）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load(path):
    """讀出 flow 檔中所有 HTTP 請求的摘要。"""
    out = []
    with open(path, "rb") as fh:
        for f in mio.FlowReader(fh).stream():
            if not isinstance(f, http.HTTPFlow):
                continue
            req = f.request
            body = req.get_text(strict=False) or ""
            out.append({
                "host":   req.pretty_host,
                "method": req.method,
                "path":   req.path.split("?")[0],
                "query":  req.path.split("?")[1] if "?" in req.path else "",
                "body":   body,
                "ua":     req.headers.get("User-Agent", ""),
                "status": f.response.status_code if f.response else None,
                "rlen":   len(f.response.content or b"") if f.response else 0,
            })
    return out


def key(r):
    return f"{r['method']} {r['host']}{r['path']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("flow_a")
    ap.add_argument("flow_b")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    args = ap.parse_args()

    A, B = load(args.flow_a), load(args.flow_b)
    la, lb = args.label_a, args.label_b

    print(f"=== 請求數 ===\n{la}: {len(A)}    {lb}: {len(B)}\n")

    ca, cb = Counter(key(r) for r in A), Counter(key(r) for r in B)
    print("=== 端點出現次數 ===")
    print(f"{'端點':<58} {la:>4} {lb:>4}  差異")
    for k in sorted(set(ca) | set(cb)):
        d = cb[k] - ca[k]
        mark = "  =" if d == 0 else f" {d:+d}"
        print(f"{k:<58} {ca[k]:>4} {cb[k]:>4} {mark}")

    print("\n=== 僅出現於單一組的端點 ===")
    only = (set(ca) - set(cb)) | (set(cb) - set(ca))
    if not only:
        print("（無）—— 兩組打到完全相同的端點集合")
    for k in sorted(only):
        print(f"  {'只有 '+la if k in ca else '只有 '+lb}: {k}")

    print("\n=== 請求 body 逐一比對 ===")
    # 以端點分組後按序配對，找出欄位層級的差異
    for k in sorted(set(ca) & set(cb)):
        ba = [r["body"] for r in A if key(r) == k]
        bb = [r["body"] for r in B if key(r) == k]
        for i, (x, y) in enumerate(zip(ba, bb)):
            if x == y:
                print(f"  [相同] {k} #{i+1}  ({len(x)} bytes)")
            else:
                print(f"  [差異] {k} #{i+1}")
                print(f"      {la}: {x[:400]}")
                print(f"      {lb}: {y[:400]}")

    print("\n=== 回應大小 ===")
    for k in sorted(set(ca) & set(cb)):
        ra = [r["rlen"] for r in A if key(r) == k]
        rb = [r["rlen"] for r in B if key(r) == k]
        print(f"  {k:<56} {la}={ra}  {lb}={rb}")


if __name__ == "__main__":
    main()
