"""本地假 API：把游戏请求全部记录下来，返回可配置的 JSON。

用法：python tools/mock_api.py [--port 8080] [--reply tools/out/mock/reply.json]

- 所有请求追加写 tools/out/mock/requests.log（含方法、路径、头、body 的 utf-8/hex）
- body 原文也按序号存到 tools/out/mock/req_0001.bin
- 返回体：默认 {"status":0,"data":{}}，可用 --reply 指定一个 JSON 文件作为模板
"""
import argparse
import datetime
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.path.join("tools", "out", "mock")
REPLY = {"status": 0, "data": {}}
SEQ = [0]

BOOTSTRAP = json.dumps({
    "app_version": "5.7.0",
    "asset_version": "6",
    "api_url": "http://10.0.2.2:8080/",
    "asset_url": "static.konosubafd.jp/bundles/5.7.0/6_LYUotQvoPmrCidgI/",
    "webview_url": "static.konosubafd.jp/webview/",
    "banner_url": "static.konosubafd.jp/banners/",
    "inquiry_url": "inquiry.konosubafd.jp/",
})



class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self, method):
        if "versions/" in self.path:
            body = BOOTSTRAP.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            os.makedirs(OUT, exist_ok=True)
            with open(os.path.join(OUT, "requests.log"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": datetime.datetime.now().isoformat(timespec="milliseconds"),
                                    "n": 0, "method": method, "path": self.path,
                                    "note": "bootstrap-json"}, ensure_ascii=False) + "\n")
            print("[boot] %s %s" % (method, self.path), flush=True)
            return
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        SEQ[0] += 1
        idx = SEQ[0]
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "req_%04d.bin" % idx), "wb") as f:
            f.write(body)
        try:
            txt = body.decode("utf-8")
        except Exception:
            txt = None
        rec = {
            "t": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "n": idx,
            "method": method,
            "path": self.path,
            "headers": dict(self.headers.items()),
            "body_len": len(body),
            "body_utf8": txt if txt is not None else None,
            "body_hex": body[:512].hex() if txt is None else None,
        }
        with open(os.path.join(OUT, "requests.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("[%d] %s %s (%d B)" % (idx, method, self.path, len(body)), flush=True)

        payload = json.dumps(REPLY, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(payload)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--reply", default=None)
    a = ap.parse_args()
    global REPLY
    if a.reply and os.path.exists(a.reply):
        REPLY = json.load(open(a.reply, encoding="utf-8"))
        print("reply template:", a.reply)
    os.makedirs(OUT, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print("mock api on http://127.0.0.1:%d/" % a.port, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
