"""Which layer answers a URL: dump Network.responseReceived cache flags + initiator.

Usage: python tools/cdp_which.py "/api/lottery/home?z=probe"
"""
import json
import sys
import time

from cdp import WS, connect, list_pages


def main():
    url_part = sys.argv[1] if len(sys.argv) > 1 else "/api/lottery/home"
    pages = [p for p in list_pages() if p.get("type") == "page"]
    if not pages:
        raise SystemExit("no page target")
    ws = WS(pages[0]["webSocketDebuggerUrl"])
    for i, m in enumerate(["Network.enable", "Runtime.enable"]):
        ws.call(100 + i, m)

    expr = ("fetch(%r).then(r=>r.text()).then(t=>t.length)"
            % (url_part + ("&" if "?" in url_part else "?") + "x=" + str(int(time.time() * 1000))))
    ws.call(200, "Runtime.evaluate", {"expression": expr, "returnByValue": True})

    tmpl = sys.argv[2] if len(sys.argv) > 2 else None
    if tmpl:
        ws.call(201, "Runtime.evaluate", {"expression": tmpl, "returnByValue": True})

    end = time.time() + 8
    ws.sock.settimeout(0.5)
    hits = []
    while time.time() < end:
        try:
            msg = json.loads(ws.recv())
        except Exception:
            continue
        meth = msg.get("method")
        p = msg.get("params", {})
        if meth == "Network.requestWillBeSent":
            r = p.get("request", {})
            if url_part.split("?")[0] in r.get("url", ""):
                init = p.get("initiator", {})
                hits.append({"id": p.get("requestId"), "req": r.get("url"),
                             "init": json.dumps(init, ensure_ascii=False)[:400]})
        elif meth == "Network.responseReceived":
            for h in hits:
                if h["id"] == p.get("requestId"):
                    r = p.get("response", {})
                    h.update({"status": r.get("status"), "mime": r.get("mimeType"),
                              "disk": r.get("fromDiskCache"), "sw": r.get("fromServiceWorker"),
                              "prefetch": r.get("fromPrefetchCache"),
                              "remote": r.get("remoteIPAddress", "") + ":" + str(r.get("remotePort", ""))})
    print("== hits:", len(hits))
    for h in hits:
        print(json.dumps(h, ensure_ascii=False))


if __name__ == "__main__":
    main()
