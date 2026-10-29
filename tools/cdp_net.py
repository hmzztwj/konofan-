"""抓取 3 秒内 WebView 的网络请求与控制台错误（用于定位动态 chunk 加载失败）。

用法:
  python tools/cdp_net.py            # 仅监听 3 秒
  python tools/cdp_net.py click 57 178   # 先派发点击，再监听
"""
import json
import sys
import time

from cdp import WS, connect, list_pages


def main():
    pages = [p for p in list_pages() if p.get("type") == "page"]
    if not pages:
        raise SystemExit("no page target")
    ws = WS(pages[0]["webSocketDebuggerUrl"])
    for i, m in enumerate(["Runtime.enable", "Log.enable", "Network.enable"]):
        ws.call(100 + i, m)

    if len(sys.argv) >= 2 and sys.argv[1] == "click":
        x, y = float(sys.argv[2]), float(sys.argv[3])
        js = ("var el=document.elementFromPoint(%f,%f);"
              "if(el){['pointerdown','mousedown','pointerup','mouseup','click'].forEach(function(t){"
              "el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,clientX:%f,clientY:%f,pointerType:'mouse'}));});}"
              "String(el&&el.getAttribute('data-path'))" % (x, y, x, y))
        print("click ->", ws.call(200, "Runtime.evaluate", {"expression": js, "returnByValue": True})
              .get("result", {}).get("result", {}).get("value"))

    seen = {}
    fails = []
    logs = []
    end = time.time() + 4
    ws.sock.settimeout(0.5)
    while time.time() < end:
        try:
            msg = json.loads(ws.recv())
        except Exception:
            continue
        meth = msg.get("method")
        p = msg.get("params", {})
        if meth == "Network.responseReceived":
            r = p.get("response", {})
            seen[p.get("requestId")] = (r.get("status"), r.get("url"))
        elif meth == "Network.loadingFailed":
            fails.append((seen.get(p.get("requestId"), ("?", "?"))[1], p.get("errorText")))
        elif meth == "Log.entryAdded":
            e = p.get("entry", {})
            logs.append("%s: %s" % (e.get("level"), e.get("text")))
        elif meth == "Runtime.consoleAPICalled":
            logs.append("console.%s: %s" % (p.get("type"), " ".join(
                str(a.get("value", a.get("description", ""))) for a in p.get("args", []))))

    bad = [(s, u) for u in seen.values() for s in [u[0]] if s and s >= 400]
    print("== requests:", len(seen))
    for s, u in bad:
        print("  %s %s" % (s, u))
    print("== failed:", len(fails))
    for f in fails:
        print("  ", f)
    print("== logs:", len(logs))
    for l in logs[-25:]:
        print("  ", l[:300])


if __name__ == "__main__":
    main()
