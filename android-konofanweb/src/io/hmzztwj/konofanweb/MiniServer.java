package io.hmzztwj.konofanweb;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.RandomAccessFile;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 极小的本地 HTTP/1.1 服务器：把 app 私有目录下的 site/ 以 http://127.0.0.1:port/ 托管出来。
 * 只做 GET/HEAD、支持 Range（.pack 按块读取）、路径穿越防护、SPA 兜底。
 * 之所以不用 file://：Chromium 会以 CORS 为由拦住 ES module 与 fetch。
 */
public class MiniServer {
    private final File root;
    private final int wantPort;
    private ServerSocket server;
    private volatile boolean running;
    private int port;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    /** 最近 404 的路径，供外壳的“加载超时”诊断面板显示。 */
    private final java.util.Deque<String> misses = new java.util.concurrent.ConcurrentLinkedDeque<>();

    public java.util.List<String> recentMisses() {
        return new java.util.ArrayList<>(misses);
    }

    private static final Map<String, String> MIME = new HashMap<>();

    static {
        String[][] t = {
                {"html", "text/html; charset=utf-8"}, {"htm", "text/html; charset=utf-8"},
                {"js", "text/javascript; charset=utf-8"}, {"mjs", "text/javascript; charset=utf-8"},
                {"css", "text/css; charset=utf-8"}, {"json", "application/json; charset=utf-8"},
                {"webmanifest", "application/manifest+json"}, {"map", "application/json"},
                {"png", "image/png"}, {"jpg", "image/jpeg"}, {"jpeg", "image/jpeg"},
                {"gif", "image/gif"}, {"webp", "image/webp"}, {"svg", "image/svg+xml"},
                {"ico", "image/x-icon"}, {"bmp", "image/bmp"}, {"avif", "image/avif"},
                {"webm", "video/webm"}, {"mp4", "video/mp4"}, {"m4v", "video/mp4"},
                {"ogg", "audio/ogg"}, {"opus", "audio/ogg"}, {"oga", "audio/ogg"},
                {"mp3", "audio/mpeg"}, {"m4a", "audio/mp4"}, {"wav", "audio/wav"},
                {"flac", "audio/flac"}, {"aac", "audio/aac"},
                {"woff", "font/woff"}, {"woff2", "font/woff2"}, {"ttf", "font/ttf"},
                {"otf", "font/otf"}, {"eot", "application/vnd.ms-fontobject"},
                {"wasm", "application/wasm"}, {"atlas", "text/plain; charset=utf-8"},
                {"skel", "application/octet-stream"}, {"bin", "application/octet-stream"},
                {"pack", "application/octet-stream"}, {"dat", "application/octet-stream"},
                {"txt", "text/plain; charset=utf-8"}, {"xml", "application/xml"},
        };
        for (String[] e : t) MIME.put(e[0], e[1]);
    }

    public MiniServer(File root, int wantPort) {
        this.root = root;
        this.wantPort = wantPort;
    }

    public synchronized int start() throws IOException {
        if (running) return port;
        // 端口固定，origin 才稳定 —— localStorage 按 origin 隔离，换端口等于换存档。
        ServerSocket ss = null;
        if (wantPort > 0) {
            try {
                ss = new ServerSocket(wantPort, 256, InetAddress.getByName("127.0.0.1"));
            } catch (IOException busy) {
                android.util.Log.w("KonofanWeb", "port " + wantPort + " busy, fallback to random");
            }
        }
        if (ss == null) ss = new ServerSocket(0, 256, InetAddress.getByName("127.0.0.1"));
        server = ss;
        port = server.getLocalPort();
        running = true;
        Thread t = new Thread(new Runnable() {
            @Override public void run() { loop(); }
        }, "mini-http-accept");
        t.setDaemon(true);
        t.start();
        return port;
    }

    public int getPort() { return port; }

    public synchronized void stop() {
        running = false;
        try { if (server != null) server.close(); } catch (IOException ignored) { }
        pool.shutdownNow();
    }

    private void loop() {
        while (running) {
            try {
                final Socket s = server.accept();
                s.setSoTimeout(30000);
                pool.execute(new Runnable() {
                    @Override public void run() { handle(s); }
                });
            } catch (IOException e) {
                if (running) e.printStackTrace();
            }
        }
    }

    private void handle(Socket sock) {
        try {
            BufferedInputStream in = new BufferedInputStream(sock.getInputStream(), 8192);
            OutputStream out = new BufferedOutputStream(sock.getOutputStream(), 64 * 1024);

            String reqLine = readLine(in);
            if (reqLine == null || reqLine.isEmpty()) { sock.close(); return; }
            String[] parts = reqLine.split(" ");
            if (parts.length < 2) { sock.close(); return; }
            String method = parts[0].toUpperCase(Locale.ROOT);
            String target = parts[1];

            String range = null;
            int contentLength = 0;
            String line;
            while ((line = readLine(in)) != null && !line.isEmpty()) {
                int c = line.indexOf(':');
                if (c > 0) {
                    String k = line.substring(0, c).trim().toLowerCase(Locale.ROOT);
                    String v = line.substring(c + 1).trim();
                    if ("range".equals(k)) range = v;
                    else if ("content-length".equals(k)) {
                        try { contentLength = Integer.parseInt(v); } catch (Exception ignored) { }
                    }
                }
            }
            if ("POST".equals(method) || "PUT".equals(method) || "PATCH".equals(method)) {
                // 单机模式：客户端会把 RPC 请求 POST 过来，这里统一回一个空的成功响应，
                // 免得界面上到处弹“服务器出错 (405)”。
                byte[] body = new byte[Math.min(contentLength, 1 << 20)];
                int got = 0;
                while (got < body.length) {
                    int n = in.read(body, got, body.length - got);
                    if (n <= 0) break;
                    got += n;
                }
                String reqPath = target;
                int qi = reqPath.indexOf('?');
                if (qi >= 0) reqPath = reqPath.substring(0, qi);
                android.util.Log.i("KonofanWeb", "rpc " + method + " " + reqPath + " len=" + got);
                byte[] resp = ("{\"status\":0,\"data\":{},\"result\":{},\"error\":null}")
                        .getBytes("UTF-8");
                String CRLF = "" + (char) 13 + (char) 10;
                String head = "HTTP/1.1 200 OK" + CRLF
                        + "Content-Type: application/json; charset=utf-8" + CRLF
                        + "Content-Length: " + resp.length + CRLF
                        + "Access-Control-Allow-Origin: *" + CRLF
                        + "Connection: close" + CRLF + CRLF;
                out.write(head.getBytes("ISO-8859-1"));
                out.write(resp);
                out.flush();
                sock.close();
                return;
            }
            if (!"GET".equals(method) && !"HEAD".equals(method)) {
                sendError(out, 405, "Method Not Allowed", method);
                sock.close();
                return;
            }

            String path = target;
            int q = path.indexOf('?');
            if (q >= 0) path = path.substring(0, q);
            int h = path.indexOf('#');
            if (h >= 0) path = path.substring(0, h);
            try {
                path = URLDecoder.decode(path, "UTF-8");
            } catch (Exception ignored) { }

            // 站点自带 Service Worker（pwa-sw.js）会把 assets 缓存起来，
            // 改过的数据补丁永远不生效。本地服务下没必要缓存，直接返回空壳 SW。
            if ("/pwa-sw.js".equals(path)) {
                String CRLF2 = "" + (char) 13 + (char) 10;
                byte[] sw = ("self.addEventListener('install',function(e){self.skipWaiting()});" + CRLF2
                        + "self.addEventListener('activate',function(e){e.waitUntil(self.clients.claim())});" + CRLF2
                        + "self.addEventListener('fetch',function(){});" + CRLF2).getBytes("UTF-8");
                String swHead = "HTTP/1.1 200 OK" + CRLF2
                        + "Content-Type: text/javascript; charset=utf-8" + CRLF2
                        + "Content-Length: " + sw.length + CRLF2
                        + "Cache-Control: no-store" + CRLF2
                        + "Connection: close" + CRLF2 + CRLF2;
                out.write(swHead.getBytes("ISO-8859-1"));
                out.write(sw);
                out.flush();
                sock.close();
                return;
            }

            File f = resolve(path);
            android.util.Log.i("KonofanWeb", "req " + method + " " + path);
            if (f == null) {
                sendError(out, 403, "Forbidden", method);
                sock.close();
                return;
            }
            // 数据接口（如 /yuanban/master/text）没有扩展名，优先补 .json
            if (!f.isFile() && !f.isDirectory()) {
                String pn = path.substring(path.lastIndexOf('/') + 1);
                if (!pn.contains(".")) {
                    File j = new File(f.getParentFile(), f.getName() + ".json");
                    if (j.isFile()) f = j;
                }
            }
            if (f.isDirectory()) f = new File(f, "index.html");
            if (!f.isFile()) {
                // 只有"/"或"*/"才兜底到 index.html；其余一律 404，
                // 否则客户端把 index.html 当 JSON 解析会报 "Unexpected token '<'"。
                String name = path.substring(path.lastIndexOf('/') + 1);
                boolean wantIndex = name.isEmpty() || path.endsWith("/");
                if (wantIndex) {
                    File idx = new File(root, "index.html");
                    if (idx.isFile()) f = idx;
                }
            }
            if (!f.isFile()) {
                android.util.Log.i("KonofanWeb", "404 " + path);
                if (misses.size() > 40) misses.pollFirst();
                misses.addLast(path);
                sendError(out, 404, "Not Found: " + path, method);
                sock.close();
                return;
            }

            long total = f.length();
            long start = 0, end = total - 1;
            boolean partial = false;
            if (range != null && range.startsWith("bytes=")) {
                String r = range.substring(6).trim();
                int dash = r.indexOf('-');
                try {
                    if (dash > 0) {
                        start = Long.parseLong(r.substring(0, dash).trim());
                        String e = r.substring(dash + 1).trim();
                        end = e.isEmpty() ? total - 1 : Long.parseLong(e);
                    } else if (dash == 0 && r.length() > 1) {
                        long suffix = Long.parseLong(r.substring(1).trim());
                        start = Math.max(0, total - suffix);
                        end = total - 1;
                    }
                } catch (NumberFormatException ignored) { start = 0; end = total - 1; }
                if (start < 0) start = 0;
                if (end >= total) end = total - 1;
                if (start > end) {
                    out.write(("HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */" + total + "\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.ISO_8859_1));
                    out.flush(); sock.close(); return;
                }
                partial = true;
            }

            long len = end - start + 1;
            String mime = mimeOf(f.getName());
            StringBuilder hd = new StringBuilder();
            hd.append(partial ? "HTTP/1.1 206 Partial Content\r\n" : "HTTP/1.1 200 OK\r\n");
            hd.append("Content-Type: ").append(mime).append("\r\n");
            hd.append("Content-Length: ").append(len).append("\r\n");
            hd.append("Accept-Ranges: bytes\r\n");
            if (partial) hd.append("Content-Range: bytes ").append(start).append('-').append(end).append('/').append(total).append("\r\n");
            boolean dynamic = f.getName().endsWith(".js") || f.getName().endsWith(".json");
            hd.append(dynamic ? "Cache-Control: no-store" : "Cache-Control: max-age=600");
            hd.append("Connection: close\r\n\r\n");
            out.write(hd.toString().getBytes(StandardCharsets.ISO_8859_1));

            if (!"HEAD".equals(method)) {
                RandomAccessFile raf = new RandomAccessFile(f, "r");
                try {
                    raf.seek(start);
                    byte[] buf = new byte[64 * 1024];
                    long left = len;
                    while (left > 0) {
                        int n = raf.read(buf, 0, (int) Math.min(buf.length, left));
                        if (n <= 0) break;
                        out.write(buf, 0, n);
                        left -= n;
                    }
                } finally {
                    raf.close();
                }
            }
            out.flush();
            sock.close();
        } catch (Exception e) {
            try { sock.close(); } catch (IOException ignored) { }
        }
    }

    private File resolve(String path) throws IOException {
        String rel = path;
        while (rel.startsWith("/")) rel = rel.substring(1);
        if (rel.isEmpty()) rel = "index.html";
        File f = new File(root, rel);
        String canonRoot = root.getCanonicalPath();
        String canon = f.getCanonicalPath();
        if (!canon.equals(canonRoot) && !canon.startsWith(canonRoot + File.separator)) return null;
        return f;
    }

    private static String mimeOf(String name) {
        int dot = name.lastIndexOf('.');
        if (dot < 0) return "application/octet-stream";
        String ext = name.substring(dot + 1).toLowerCase(Locale.ROOT);
        String m = MIME.get(ext);
        return m != null ? m : "application/octet-stream";
    }

    private static void sendError(OutputStream out, int code, String msg, String method) throws IOException {
        byte[] body = (code + " " + msg).getBytes(StandardCharsets.UTF_8);
        String head = "HTTP/1.1 " + code + " " + msg + "\r\nContent-Type: text/plain; charset=utf-8\r\n"
                + "Content-Length: " + body.length + "\r\nConnection: close\r\n\r\n";
        out.write(head.getBytes(StandardCharsets.ISO_8859_1));
        if (!"HEAD".equals(method)) out.write(body);
        out.flush();
    }

    private static String readLine(InputStream in) throws IOException {
        StringBuilder sb = new StringBuilder(128);
        int c;
        while ((c = in.read()) != -1) {
            if (c == '\n') break;
            if (c != '\r') sb.append((char) c);
            if (sb.length() > 8192) break;
        }
        if (c == -1 && sb.length() == 0) return null;
        return sb.toString();
    }
}
