"""TLS 中间人：拦截游戏发往 :443 的请求。

- 用自签 CA（tools/ca/ca.pem）签发的 srv.pem 作为服务端证书
- bootstrap（路径含 /versions/）返回我们伪造的 JSON，把 api_url 指到本机
- 其余请求原样转发给真实服务器（TLS 再加密），从而让资源和广告继续工作
- 所有请求写入 tools/out/mitm/requests.log

用法：python tools/mitm.py [--port 8443]
"""
import argparse
import datetime
import json
import os
import socket
import ssl
import threading

CA = os.path.join("tools", "ca")
OUT = os.path.join("tools", "out", "mitm")
LOG = os.path.join(OUT, "requests.log")

BOOTSTRAP = {
    "app_version": "5.7.0",
    "asset_version": "6",
    "api_url": "10.0.2.2:8080/",
    "asset_url": "static.konosubafd.jp/bundles/5.7.0/6_LYUotQvoPmrCidgI/",
    "webview_url": "static.konosubafd.jp/webview/",
    "banner_url": "static.konosubafd.jp/banners/",
    "inquiry_url": "inquiry.konosubafd.jp/",
}

LOCK = threading.Lock()


def log(obj):
    os.makedirs(OUT, exist_ok=True)
    with LOCK, open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_request(sock_file):
    line = sock_file.readline()
    if not line:
        return None
    try:
        method, path, version = line.decode("latin-1").strip().split(" ", 2)
    except ValueError:
        return None
    headers = {}
    while True:
        h = sock_file.readline()
        if not h or h in (b"\r\n", b"\n"):
            break
        k, _, v = h.decode("latin-1").partition(":")
        headers[k.strip().lower()] = v.strip()
    body = b""
    n = int(headers.get("content-length") or 0)
    if n:
        body = sock_file.read(n)
    return method, path, headers, body


def https_reply(conn, code, payload, ctype="application/json"):
    if isinstance(payload, str):
        payload = payload.encode()
    head = (
        f"HTTP/1.1 {code} OK\r\n"
        f"Content-Type: {ctype}\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Connection: close\r\n\r\n"
    ).encode()
    conn.sendall(head + payload)


def proxy(conn, host, raw_request):
    """把原始请求转发给真实服务器（TLS），再把响应原样回传。"""
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=15) as up:
        with ctx.wrap_socket(up, server_hostname=host) as tls:
            tls.sendall(raw_request)
            chunks = []
            while True:
                try:
                    b = tls.recv(65536)
                except Exception:
                    break
                if not b:
                    break
                chunks.append(b)
            data = b"".join(chunks)
    conn.sendall(data)
    return len(data)



def sni_of(sock):
    """从 ClientHello 里偷 SNI（不消费数据）。"""
    try:
        sock.settimeout(5)
        sock.recv(1, socket.MSG_PEEK)
        buf = sock.recv(4096, socket.MSG_PEEK)
    except Exception:
        return None
    try:
        if len(buf) < 45 or buf[0] != 0x16:
            return None
        p = 43
        p += 1 + buf[p]
        p += 2 + int.from_bytes(buf[p:p+2], "big")
        p += 1
        p += 2 + int.from_bytes(buf[p:p+2], "big")
        while p + 4 <= len(buf):
            t = int.from_bytes(buf[p:p+2], "big")
            ln = int.from_bytes(buf[p+2:p+4], "big")
            if t == 0:
                q = p + 4
                q += 2 + int.from_bytes(buf[q:q+2], "big")
                n = int.from_bytes(buf[q:q+2], "big")
                q += 2
                return buf[q:q+n].decode("idna", "ignore")
            p += 4 + ln
    except Exception:
        return None
    return None

def handle(conn, addr):
    try:
        conn.settimeout(20)
        f = conn.makefile("rb")
        req = read_request(f)
        if not req:
            return
        method, path, headers, body = req
        host = (headers.get("host") or "").split(":")[0]
        raw = (
            f"{method} {path} HTTP/1.1\r\n"
            + "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            + "\r\n"
        ).encode("latin-1") + body

        rec = {
            "t": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "host": host,
            "method": method,
            "path": path,
            "body_len": len(body),
            "body": body.decode("utf-8", "replace")[:2000] if body else "",
        }

        if "/versions/" in path and "konosubafd" in host:
            payload = json.dumps(BOOTSTRAP, ensure_ascii=False)
            rec["action"] = "bootstrap"
            log(rec)
            https_reply(conn, 200, payload)
            return

        if host in ("10.0.2.2", "127.0.0.1", "localhost") or "konosubafd" in host:
            # 游戏 API（我们把它指到本机了）→ 统一返回空壳
            rec["action"] = "mock-api"
            log(rec)
            https_reply(conn, 200, json.dumps({"status": 0, "data": {}}))
            return

        rec["action"] = "proxy"
        try:
            n = proxy(conn, host, raw)
            rec["proxy_bytes"] = n
        except Exception as e:
            rec["proxy_error"] = str(e)
        log(rec)
    except Exception as e:
        log({"t": datetime.datetime.now().isoformat(timespec="milliseconds"),
             "error": str(e), "peer": str(addr)})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8443)
    args = ap.parse_args()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(os.path.join(CA, "srv.pem"), os.path.join(CA, "srv.key"))
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen(50)
    print(f"mitm on 127.0.0.1:{args.port}", flush=True)
    while True:
        c, a = srv.accept()
        _sni = sni_of(c)
        try:
            c = ctx.wrap_socket(c, server_side=True)
        except Exception as e:
            log({"sni": _sni, "error": f"tls {e}"})
            c.close()
            continue
        threading.Thread(target=handle, args=(c, a), daemon=True).start()


if __name__ == "__main__":
    main()
