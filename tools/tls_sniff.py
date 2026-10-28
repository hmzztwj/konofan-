import socket, sys, threading, time
LOG = open(r'tools/out/tls.log', 'a', encoding='utf-8')
def handle(c, a):
    try:
        c.settimeout(3)
        data = c.recv(4096)
        LOG.write(f'[{time.strftime("%H:%M:%S")}] conn from {a} bytes={len(data)}\n')
        LOG.write(repr(data[:400]) + '\n'); LOG.flush()
        # 尝试解析 SNI
        try:
            if data[:1] == b'\x16':
                i = data.find(b'\x00\x00')
                sn = data.find(b'\x00\x00', 43)
                LOG.write('looks like TLS ClientHello\n'); LOG.flush()
        except Exception:
            pass
    except Exception as e:
        LOG.write(f'err {e}\n'); LOG.flush()
    finally:
        c.close()
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 8443)); s.listen(16)
LOG.write(f'--- listen 8443 {time.strftime("%H:%M:%S")} ---\n'); LOG.flush()
while True:
    c, a = s.accept(); threading.Thread(target=handle, args=(c, a), daemon=True).start()
