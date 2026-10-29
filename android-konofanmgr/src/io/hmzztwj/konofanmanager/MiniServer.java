package io.hmzztwj.konofanmanager;

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
    private static File rootStatic;
    private final int wantPort;
    private ServerSocket server;
    private volatile boolean running;
    private int port;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    /** 最近 404 的路径，供外壳的“加载超时”诊断面板显示。 */
    /** 管理器共享目录：/sdcard/Download/konofan_manager（两个 App 都用 targetSdk 29，可直接读写） */
    public static java.io.File mgrDir() {
        java.io.File d = new java.io.File(android.os.Environment.getExternalStorageDirectory(),
                "Download/konofan_manager");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    private static File rootForPatch() { return rootStatic; }

    private static String lastApplied = "";

    /** 把活动开关落到磁盘上的数据文件（写前备份一次 .full.json）：questx59.json 的 event[]、story/index.json 的 story_event[]。
     *  这样不依赖任何 HTTP 拦截，游戏读文件就是过滤后的结果。 */
    private static synchronized void applyEventPolicyToDisk() {
        try {
            java.io.File cfg = new java.io.File(mgrDir(), "config.json");
            if (!cfg.isFile()) return;
            String cfgText = new String(readAll(cfg, 1 << 20), "UTF-8");
            org.json.JSONObject c = new org.json.JSONObject(cfgText);
            String mode = c.optString("eventMode", "");
            org.json.JSONArray onArr = c.optJSONArray("enabledEvents");
            StringBuilder sb = new StringBuilder(mode).append('|');
            java.util.Set<String> on = new java.util.HashSet<>();
            for (int i = 0; onArr != null && i < onArr.length(); i++) {
                String id = onArr.getString(i);
                on.add(id);
                sb.append(id).append(',');
            }
            String sig = sb.toString();
            if (sig.equals(lastApplied)) return;
            lastApplied = sig;

            java.io.File site = rootForPatch();
            if (site == null) return;
            java.io.File qx = new java.io.File(site, "yuanban/master/questx59.json");
            java.io.File qxFull = new java.io.File(site, "yuanban/master/questx59.full.json");
            if (qx.isFile()) {
                if (!qxFull.exists()) copyFile(qx, qxFull);
                java.io.File src = qxFull.isFile() ? qxFull : qx;
                org.json.JSONObject root = new org.json.JSONObject(new String(readAll(src, 64 << 20), "UTF-8"));
                org.json.JSONArray evs = root.optJSONArray("event");
                org.json.JSONArray keep = new org.json.JSONArray();
                for (int i = 0; evs != null && i < evs.length(); i++) {
                    org.json.JSONObject e = evs.getJSONObject(i);
                    boolean live = eventLive(mode, on, e.optString("id"));
                    if (live) {
                        org.json.JSONArray ss0 = e.optJSONArray("stages");
                        for (int k = 0; ss0 != null && k < ss0.length(); k++) {
                            org.json.JSONObject st0 = ss0.getJSONObject(k);
                            org.json.JSONArray en0 = st0.optJSONArray("enemies");
                            org.json.JSONArray en1 = new org.json.JSONArray();
                            for (int m = 0; en0 != null && m < en0.length(); m++) en1.put(fixEnemyShape(en0.optString(m)));
                            st0.put("enemies", en1);
                        }
                        e.put("start", "2020/1/1 0:00");
                        e.put("end", "2035/12/31 23:59");
                        keep.put(e);
                    }
                }
                root.put("event", keep);
                writeFile(qx, root.toString().getBytes("UTF-8"));
                android.util.Log.i("KonofanWeb", "disk patch questx mode=" + mode + " keep=" + keep.length());
            }

            injectEventStages(site, mode, on);

            // 敌人模型在启动时预加载，必须把 shape 重映射落到磁盘，HTTP 层改动对预加载无效
            java.io.File b = new java.io.File(site, "yuanban/master/battle59.json");
            java.io.File bf = new java.io.File(site, "yuanban/master/battle59.full.json");
            if (b.isFile()) {
                if (!bf.exists()) copyFile(b, bf);
                java.io.File bsrc = bf.isFile() ? bf : b;
                byte[] patched = battlePatched(readAll(bsrc, 96 << 20));
                writeFile(b, patched);
            }

            java.io.File si = new java.io.File(site, "yuanban/story/index.json");
            java.io.File siFull = new java.io.File(site, "yuanban/story/index.full.json");
            if (si.isFile()) {
                if (!siFull.exists()) copyFile(si, siFull);
                java.io.File src = siFull.isFile() ? siFull : si;
                org.json.JSONObject root = new org.json.JSONObject(new String(readAll(src, 96 << 20), "UTF-8"));
                org.json.JSONArray evs = root.optJSONArray("story_event");
                org.json.JSONArray keep = new org.json.JSONArray();
                for (int i = 0; evs != null && i < evs.length(); i++) {
                    org.json.JSONObject e = evs.getJSONObject(i);
                    String eid = e.optString("event_id", e.optString("unlock_event_id", ""));
                    if (eid.isEmpty() || eventLive(mode, on, eid)) keep.put(e);
                }
                root.put("story_event", keep);
                writeFile(si, root.toString().getBytes("UTF-8"));
                android.util.Log.i("KonofanWeb", "disk patch story mode=" + mode + " keep=" + keep.length());
            }
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "apply event policy fail " + e);
        }
    }

    /** 把开启活动的关卡塞进 quest59.json 的 areas（战斗入口按 areas 查关卡，活动关卡原本不在里面）。 */
    /** battle59.json 里敌人实例的 shape 就是 spine 模型名；没有模型的 shape 换成最接近的已有模型。 */
    private static byte[] battlePatched(byte[] raw) {
        try {
            String t = new String(raw, "UTF-8");
            String Q = String.valueOf((char) 34);
            String key = Q + "shape" + Q + ":" + Q;
            StringBuilder sb = new StringBuilder(t.length() + 64);
            int i = 0, changed = 0;
            while (true) {
                int p = t.indexOf(key, i);
                if (p < 0) { sb.append(t, i, t.length()); break; }
                int q = p + key.length();
                int r = q;
                while (r < t.length() && Character.isDigit(t.charAt(r))) r++;
                if (r == q) { sb.append(t, i, q); i = q; continue; }
                String cur = t.substring(q, r);
                String fixed = fixEnemyShape(cur);
                if (!fixed.equals(cur)) changed++;
                sb.append(t, i, q).append(fixed).append('"');
                i = r + 1;
            }
            android.util.Log.i("KonofanWeb", "battle shape patch changed=" + changed);
            return sb.toString().getBytes("UTF-8");
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "battle patch fail " + e);
            return raw;
        }
    }

    private static void injectEventStages(java.io.File site, String mode, java.util.Set<String> on) {
        try {
            java.io.File q = new java.io.File(site, "yuanban/master/quest59.json");
            java.io.File qf = new java.io.File(site, "yuanban/master/quest59.full.json");
            java.io.File qx = new java.io.File(site, "yuanban/master/questx59.full.json");
            if (!q.isFile() || !qx.isFile()) return;
            if (!qf.exists()) copyFile(q, qf);
            java.io.File src = qf.isFile() ? qf : q;
            org.json.JSONObject root = new org.json.JSONObject(new String(readAll(src, 96 << 20), "UTF-8"));
            org.json.JSONArray areas = root.optJSONArray("areas");
            if (areas == null) return;
            org.json.JSONObject qxr = new org.json.JSONObject(new String(readAll(qx, 96 << 20), "UTF-8"));
            org.json.JSONArray evs = qxr.optJSONArray("event");
            org.json.JSONArray stages = new org.json.JSONArray();
            int n = 0;
            for (int i = 0; evs != null && i < evs.length(); i++) {
                org.json.JSONObject e = evs.getJSONObject(i);
                if (!eventLive(mode, on, e.optString("id"))) continue;
                org.json.JSONArray ss = e.optJSONArray("stages");
                for (int j = 0; ss != null && j < ss.length(); j++) {
                    org.json.JSONObject st = ss.getJSONObject(j);
                    org.json.JSONObject o = new org.json.JSONObject();
                    o.put("id", st.optString("id"));
                    o.put("title", st.optString("name", st.optString("title", "")));
                    o.put("stamina", st.optInt("stamina", 5));
                    o.put("power", st.optInt("power", 0));
                    o.put("graphic", st.optString("graphic", "1340"));
                    o.put("boss", st.optBoolean("boss", false));
                    org.json.JSONArray en = st.optJSONArray("enemies");
                    org.json.JSONArray en2 = new org.json.JSONArray();
                    for (int k = 0; en != null && k < en.length(); k++) {
                        en2.put(fixEnemyShape(en.optString(k)));
                    }
                    o.put("enemies", en2);
                    o.put("drops", new org.json.JSONArray());
                    o.put("unlock", 0);
                    o.put("missions", new org.json.JSONArray());
                    o.put("rewards", new org.json.JSONArray());
                    stages.put(o);
                    n++;
                }
            }
            org.json.JSONObject area = new org.json.JSONObject();
            area.put("part", 99);
            area.put("area", 99);
            area.put("unlock", 0);
            area.put("title", "活动关卡");
            org.json.JSONObject modes = new org.json.JSONObject();
            org.json.JSONObject m1 = new org.json.JSONObject();
            m1.put("image", "bg_mainquest_1_1");
            m1.put("stages", stages);
            modes.put("1", m1);
            area.put("modes", modes);
            org.json.JSONArray out = new org.json.JSONArray();
            for (int i = 0; i < areas.length(); i++) out.put(areas.getJSONObject(i));
            out.put(area);
            root.put("areas", out);
            writeFile(q, root.toString().getBytes("UTF-8"));
            android.util.Log.i("KonofanWeb", "inject event stages=" + n);
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "inject stages fail " + e);
        }
    }

    private static void writeFile(java.io.File f, byte[] data) throws java.io.IOException {
        java.io.FileOutputStream fo = new java.io.FileOutputStream(f);
        try { fo.write(data); } finally { fo.close(); }
    }

    private static void copyFile(java.io.File a, java.io.File b) throws java.io.IOException {
        writeFile(b, readAll(a, 96 << 20));
    }

    /** 读取配置里的活动开关（mode: all/off/enabled）；没有配置返回 null 表示不干预。 */
    private static String[] eventPolicy() {
        try {
            java.io.File cfg = new java.io.File(mgrDir(), "config.json");
            if (!cfg.isFile()) return null;
            org.json.JSONObject c = new org.json.JSONObject(new String(readAll(cfg, 1 << 20), "UTF-8"));
            String mode = c.optString("eventMode", "");
            if (mode.isEmpty()) return null;
            org.json.JSONArray arr = c.optJSONArray("enabledEvents");
            java.util.List<String> on = new java.util.ArrayList<>();
            for (int i = 0; arr != null && i < arr.length(); i++) on.add(arr.getString(i));
            return new String[]{mode, new org.json.JSONArray(on).toString()};
        } catch (Exception e) {
            return null;
        }
    }

    private static boolean eventLive(String mode, java.util.Set<String> on, String id) {
        if ("all".equals(mode)) return true;
        if ("off".equals(mode)) return false;
        return on.contains(id);
    }

    /** 活动剧情：story/index.json 里 story_event 只保留已开启活动对应的条目。 */
    private static java.util.List<String> modelCache = null;

    private static java.util.List<String> modelIds() {
        if (modelCache != null) return modelCache;
        java.util.List<String> out = new java.util.ArrayList<>();
        try {
            java.io.File d = new java.io.File(rootForPatch(), "sucai/yuanban/战斗/敌方单位/模型");
            String[] fs = d.list();
            java.util.Set<String> seen = new java.util.HashSet<>();
            if (fs != null) for (String f : fs) {
                int dot = f.indexOf('.');
                String id = dot > 0 ? f.substring(0, dot) : f;
                if (seen.add(id)) out.add(id);
            }
            java.util.Collections.sort(out);
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "model list fail " + e);
        }
        modelCache = out;
        android.util.Log.i("KonofanWeb", "enemy models=" + out);
        return out;
    }

    /** 事件关卡引用的敌人 id 可能在镜像里没有模型；按「同族前缀 → 数值最近 → 兜底」映射到存在的模型。 */
    private static String fixEnemyShape(String id) {
        java.util.List<String> ms = modelIds();
        if (ms.isEmpty()) return id;
        if (ms.contains(id)) return id;
        String best = null;
        for (String m : ms) {
            if (m.length() >= 3 && id.length() >= 3 && m.substring(0, 3).equals(id.substring(0, 3))) { best = m; break; }
        }
        if (best == null) {
            long want;
            try { want = Long.parseLong(id); } catch (Exception e) { want = 0; }
            long bd = Long.MAX_VALUE;
            for (String m : ms) {
                long v;
                try { v = Long.parseLong(m); } catch (Exception e) { continue; }
                long d = Math.abs(v - want);
                if (d < bd) { bd = d; best = m; }
            }
        }
        if (best == null) best = ms.get(0);
        android.util.Log.i("KonofanWeb", "enemy remap " + id + " -> " + best);
        return best;
    }

    private static byte[] storyPatchedIndex() {
        try {
            android.util.Log.i("KonofanWeb", "story handler hit root=" + rootForPatch());
            String[] pol = eventPolicy();
            android.util.Log.i("KonofanWeb", "story policy=" + (pol == null ? "null" : pol[0]));
            if (pol == null) return null;
            String mode = pol[0];
            java.util.Set<String> on = new java.util.HashSet<>();
            org.json.JSONArray arr = new org.json.JSONArray(pol[1]);
            for (int i = 0; i < arr.length(); i++) on.add(arr.getString(i));

            java.io.File f = new java.io.File(rootForPatch(), "yuanban/story/index.json");
            if (!f.isFile()) return null;
            org.json.JSONObject root = new org.json.JSONObject(new String(readAll(f, 64 << 20), "UTF-8"));
            org.json.JSONArray evs = root.optJSONArray("story_event");
            org.json.JSONArray keep = new org.json.JSONArray();
            for (int i = 0; evs != null && i < evs.length(); i++) {
                org.json.JSONObject e = evs.getJSONObject(i);
                String eid = e.optString("event_id", e.optString("unlock_event_id", ""));
                if (eid.isEmpty() || eventLive(mode, on, eid)) keep.put(e);
            }
            root.put("story_event", keep);
            android.util.Log.i("KonofanWeb", "story filter mode=" + mode + " keep=" + keep.length() + "/" + (evs == null ? 0 : evs.length()));
            return root.toString().getBytes("UTF-8");
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "story filter fail " + e);
            return null;
        }
    }

    /** 读取管理器配置并对 questx59.json 的活动生效时间做改写；没有配置就返回 null（走原文件）。 */
    private static byte[] eventPatchedQuestx() {
        try {
            java.io.File cfg = new java.io.File(mgrDir(), "config.json");
            if (!cfg.isFile()) return null;
            org.json.JSONObject c = new org.json.JSONObject(new String(readAll(cfg, 1 << 20), "UTF-8"));
            String mode = c.optString("eventMode", "");
            android.util.Log.i("KonofanWeb", "event patch candidate mode=" + mode);
            if (mode.isEmpty()) return null;
            java.util.Set<String> on = new java.util.HashSet<>();
            org.json.JSONArray arr = c.optJSONArray("enabledEvents");
            for (int i = 0; arr != null && i < arr.length(); i++) on.add(arr.getString(i));

            java.io.File f = null;
            java.io.File site = rootForPatch();
            if (site != null) f = new java.io.File(site, "yuanban/master/questx59.json");
            if (f == null || !f.isFile()) return null;

            org.json.JSONObject root = new org.json.JSONObject(new String(readAll(f, 32 << 20), "UTF-8"));
            org.json.JSONArray evs = root.optJSONArray("event");
            String LIVE_START = "2020/1/1 0:00", LIVE_END = "2035/12/31 23:59";
            org.json.JSONArray keep = new org.json.JSONArray();
            int onCount = 0;
            for (int i = 0; evs != null && i < evs.length(); i++) {
                org.json.JSONObject e = evs.getJSONObject(i);
                boolean live;
                if ("all".equals(mode)) live = true;
                else if ("off".equals(mode)) live = false;
                else live = on.contains(e.optString("id"));
                if (live) {
                    e.put("start", LIVE_START);
                    e.put("end", LIVE_END);
                    keep.put(e);
                    onCount++;
                }
            }
            root.put("event", keep);
            android.util.Log.i("KonofanWeb", "event filter mode=" + mode + " keep=" + onCount + "/" + (evs == null ? 0 : evs.length()));
            return root.toString().getBytes("UTF-8");
        } catch (Exception e) {
            android.util.Log.w("KonofanWeb", "event patch fail " + e);
            return null;
        }
    }

    private static byte[] readAll(java.io.File f, int max) throws java.io.IOException {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        java.io.FileInputStream fis = new java.io.FileInputStream(f);
        byte[] buf = new byte[8192];
        int n, total = 0;
        while ((n = fis.read(buf)) > 0 && total < max) { bos.write(buf, 0, n); total += n; }
        fis.close();
        return bos.toByteArray();
    }

    private static void write(String s, OutputStream out, String type, int len) throws java.io.IOException {
        String CRLF = "" + (char) 13 + (char) 10;
        String head = "HTTP/1.1 200 OK" + CRLF
                + "Content-Type: " + type + CRLF
                + "Content-Length: " + len + CRLF
                + "Cache-Control: no-store" + CRLF
                + "Access-Control-Allow-Origin: *" + CRLF
                + "Connection: close" + CRLF + CRLF;
        out.write(head.getBytes("ISO-8859-1"));
        if (len > 0) out.write(s.getBytes("ISO-8859-1"));
    }

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
        rootStatic = root;
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
                try {
                    if ("/__mgr/backup".equals(reqPath)) {
                        java.io.File dir = new java.io.File(mgrDir(), "saves");
                        dir.mkdirs();
                        String ts = String.valueOf(System.currentTimeMillis());
                        java.io.FileOutputStream fo = new java.io.FileOutputStream(new java.io.File(dir, "save_" + ts + ".json"));
                        fo.write(body, 0, got); fo.close();
                        java.io.File[] fs = dir.listFiles();
                        if (fs != null && fs.length > 20) {
                            java.util.Arrays.sort(fs, new java.util.Comparator<java.io.File>() {
                                public int compare(java.io.File a, java.io.File b) { return a.getName().compareTo(b.getName()); }
                            });
                            for (int k = 0; k < fs.length - 20; k++) fs[k].delete();
                        }
                        // 生成 saves/index.json 供管理器展示（时间 + 艾莉丝）
                        try {
                            org.json.JSONArray idx = new org.json.JSONArray();
                            java.io.File[] all = dir.listFiles();
                            java.util.Arrays.sort(all, new java.util.Comparator<java.io.File>() {
                                public int compare(java.io.File a, java.io.File b) { return a.getName().compareTo(b.getName()); }
                            });
                            for (java.io.File f : all) {
                                if (!f.getName().endsWith(".json")) continue;
                                org.json.JSONObject item = new org.json.JSONObject();
                                item.put("name", f.getName());
                                String nm = f.getName().replace("save_", "").replace(".json", "");
                                item.put("ts", Long.parseLong(nm));
                                try {
                                    org.json.JSONObject sv = new org.json.JSONObject(new String(readAll(f, 8 << 20), "UTF-8"));
                                    org.json.JSONObject it = sv.optJSONObject("items");
                                    if (it != null && it.has("1:1")) item.put("gold", it.optLong("1:1"));
                                } catch (Exception ignored) { }
                                idx.put(item);
                            }
                            org.json.JSONObject root = new org.json.JSONObject();
                            root.put("files", idx);
                            writeFile(new java.io.File(dir, "index.json"), root.toString().getBytes("UTF-8"));
                        } catch (Exception ignored) { }
                        android.util.Log.i("KonofanWeb", "backup saved " + ts + " bytes=" + got);
                        write("{\"ok\":true}", out, "application/json; charset=utf-8", 11);
                        out.flush(); sock.close(); return;
                    }
                    if ("/__mgr/ack-restore".equals(reqPath)) {
                        new java.io.File(mgrDir(), "restore.json").delete();
                        write("{\"ok\":true}", out, "application/json; charset=utf-8", 11);
                        out.flush(); sock.close(); return;
                    }
                    if ("/__mgr/ack-cmd".equals(reqPath)) {
                        new java.io.File(mgrDir(), "cmd.json").delete();
                        write("{\"ok\":true}", out, "application/json; charset=utf-8", 11);
                        out.flush(); sock.close(); return;
                    }
                    if ("/__mgr/state".equals(reqPath)) {
                        java.io.FileOutputStream fo = new java.io.FileOutputStream(
                                new java.io.File(mgrDir(), "state.json"));
                        fo.write(body, 0, got); fo.close();
                        write("{\"ok\":true}", out, "application/json; charset=utf-8", 11);
                        out.flush(); sock.close(); return;
                    }
                    if ("/__mgr/ack".equals(reqPath)) {
                        // 管理器礼物已被消费：按 seq 从 gifts.json 里删掉
                        java.io.File gf = new java.io.File(mgrDir(), "gifts.json");
                        if (gf.isFile()) {
                            String txt = new String(readAll(gf, 1 << 20), "UTF-8");
                            String ack = new String(body, 0, got, "UTF-8");
                            java.util.List<Long> done = new java.util.ArrayList<>();
                            try {
                                org.json.JSONObject aj = new org.json.JSONObject(ack);
                                org.json.JSONArray arr = aj.optJSONArray("seqs");
                                for (int i = 0; arr != null && i < arr.length(); i++) done.add(arr.getLong(i));
                            } catch (Exception ignored) { }
                            try {
                                org.json.JSONObject gj = new org.json.JSONObject(txt);
                                org.json.JSONArray ga = gj.optJSONArray("gifts");
                                org.json.JSONArray keep = new org.json.JSONArray();
                                for (int i = 0; ga != null && i < ga.length(); i++) {
                                    org.json.JSONObject o = ga.getJSONObject(i);
                                    if (!done.contains(o.optLong("seq", -1))) keep.put(o);
                                }
                                gj.put("gifts", keep);
                                java.io.FileOutputStream fo = new java.io.FileOutputStream(gf);
                                fo.write(gj.toString().getBytes("UTF-8")); fo.close();
                            } catch (Exception ignored) { }
                        }
                        write("{\"ok\":true}", out, "application/json; charset=utf-8", 11);
                        out.flush(); sock.close(); return;
                    }
                } catch (Exception e) {
                    android.util.Log.w("KonofanWeb", "mgr post fail " + e);
                }
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

            // 活动管理：按 config.json 的 eventMode/enabledEvents 改写 questx59.json 的活动时间窗
            String pathOnly = path.contains("?") ? path.substring(0, path.indexOf('?')) : path;
            if ("/yuanban/story/index.json".equals(pathOnly)) {
                byte[] sbody = storyPatchedIndex();
                if (sbody != null) {
                    write(new String(sbody, "ISO-8859-1"), out, "application/json; charset=utf-8", sbody.length);
                    out.flush(); sock.close(); return;
                }
            }

            if ("/yuanban/master/questx59.json".equals(pathOnly)) {
                byte[] body = eventPatchedQuestx();
                if (body != null) {
                    write(new String(body, "ISO-8859-1"), out, "application/json; charset=utf-8", body.length);
                    out.flush(); sock.close(); return;
                }
            }

            if ("/__bridge.js".equals(pathOnly)) {
                java.io.File bf = new java.io.File(rootStatic, "__bridge.js");
                if (!bf.isFile()) { sendError(out, 404, "no bridge", "GET"); return; }
                byte[] bb = readAll(bf, 4 << 20);
                String hdr = "HTTP/1.1 200 OK\r\n"
                        + "Content-Type: application/javascript; charset=utf-8\r\n"
                        + "Content-Length: " + bb.length + "\r\n"
                        + "Cache-Control: no-store\r\n"
                        + "Connection: close\r\n\r\n";
                out.write(hdr.getBytes(StandardCharsets.ISO_8859_1));
                out.write(bb);
                out.flush(); sock.close(); return;
            }
            if ("/__mgr/bridge.js".equals(pathOnly)) {
                java.io.File alt = new java.io.File(rootStatic.getParentFile(), "bridge.js");
                java.io.File use = alt;
                if (!use.isFile()) { sendError(out, 404, "no bridge", "GET"); return; }
                byte[] b = readAll(use, 4 << 20);
                String hdr = "HTTP/1.1 200 OK\r\n"
                        + "Content-Type: application/javascript; charset=utf-8\r\n"
                        + "Content-Length: " + b.length + "\r\n"
                        + "Cache-Control: no-store\r\n"
                        + "Connection: close\r\n\r\n";
                out.write(hdr.getBytes(StandardCharsets.ISO_8859_1));
                out.write(b);
            }
            if ("/__mgr/config.json".equals(pathOnly)) {
                applyEventPolicyToDisk();
            }

            if (path.equals("/__mgr/save-latest")) {
                java.io.File dir = new java.io.File(mgrDir(), "saves");
                java.io.File[] fs = dir.listFiles();
                java.io.File best = null;
                if (fs != null) for (java.io.File f2 : fs) {
                    String n2 = f2.getName();
                    if (!n2.startsWith("save_") || !n2.endsWith(".json")) continue;
                    if (best == null || f2.lastModified() > best.lastModified()) best = f2;
                }
                // 选 rank 最大的一份（合并包会自动备份出 rank1 的空档，不能只按时间取最新）
                try {
                    java.io.File richest = null; int bestRank = -1;
                    if (fs != null) for (java.io.File f3 : fs) {
                        String n3 = f3.getName();
                        if (!n3.startsWith("save_") || !n3.endsWith(".json")) continue;
                        byte[] cb = readAll(f3, 8 << 20);
                        String js = new String(cb, "UTF-8");
                        int k = js.indexOf("\"rank\":");
                        if (k < 0) continue;
                        int v = 0, j = k + 7;
                        while (j < js.length() && Character.isDigit(js.charAt(j))) { v = v * 10 + (js.charAt(j) - '0'); j++; }
                        if (v > bestRank) { bestRank = v; richest = f3; }
                    }
                    if (richest != null) best = richest;
                } catch (Exception ig2) { }
                if (best != null) {
                    byte[] sd = readAll(best, 8 << 20);
                    write(new String(sd, "ISO-8859-1"), out, "application/json; charset=utf-8", sd.length);
                    out.flush(); sock.close(); return;
                }
                write("{\"ok\":false}", out, "application/json; charset=utf-8", 11);
                out.flush(); sock.close(); return;
            }
            if (path.startsWith("/__mgr/")) {
                String name = path.substring("/__mgr/".length());
                if (name.contains("..") || name.contains("/")) { sendError(out, 400, "Bad Request", path); sock.close(); return; }
                java.io.File f = new java.io.File(mgrDir(), name);
                if (!f.isFile()) {
                    write("{\"ok\":false}", out, "application/json; charset=utf-8", 12);
                    out.flush(); sock.close(); return;
                }
                byte[] data = readAll(f, 8 << 20);
                write(new String(data, "ISO-8859-1"), out, "application/json; charset=utf-8", data.length);
                out.flush(); sock.close(); return;
            }

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
            // --- 首次启动把最新备份直接拼进 index.html，保证游戏初始化前就拿到旧档 ---
            if ("index.html".equals(f.getName()) && f.isFile() && !new File(mgrDir(), ".restored").isFile()) {
                try {
                    java.io.File sdir = new java.io.File(mgrDir(), "saves");
                    java.io.File[] sf = sdir.listFiles();
                    java.io.File bestS = null;
                    if (sf != null) for (java.io.File x : sf) {
                        String xn = x.getName();
                        if (!xn.startsWith("save_") || !xn.endsWith(".json")) continue;
                        if (bestS == null || x.lastModified() > bestS.lastModified()) bestS = x;
                    }
                    if (bestS != null) {
                        String sj = new String(readAll(bestS, 8 << 20), "UTF-8").trim();
                        if (sj.startsWith("{")) {
                            String html2 = new String(readAll(f, 8 << 20), "UTF-8");
                            String tag = "<script src=\"./__bridge.js\"></script>" + "<script>try{localStorage.setItem('oldui59.save',"
                                    + sj + ");localStorage.setItem('kf_restored_ok','1');}catch(e){}</script>";
                            String head = html2.contains("<head>") ? "<head>" : "<HEAD>";
                            html2 = html2.replaceFirst(java.util.regex.Pattern.quote(head), java.util.regex.Matcher.quoteReplacement(head + tag));
                            byte[] hb = html2.getBytes("UTF-8");
                            write(new String(hb, "ISO-8859-1"), out, "text/html; charset=utf-8", hb.length);
                            out.flush();
                            new File(mgrDir(), ".restored").createNewFile(); String kfBridgeTag = "1";
                            android.util.Log.i("KonofanWeb", "save injected bytes=" + hb.length);
                            sock.close();
                            return;
                        }
                    }
                } catch (Exception ig) {}
            }

            // anim 兜底：Open__/Close__ 这些按内容寻址的动画文件缺失时，用现成的一支顶上
            if (!f.isFile() && path.indexOf("/anim/") >= 0 && path.endsWith(".json")) {
                File fb = new File(rootStatic, "yuanban/anim/Open__03762c.json");
                if (fb.isFile()) {
                    f = fb;
                    android.util.Log.i("KonofanWeb", "anim fallback " + path);
                }
            }
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

            android.util.Log.i("KonofanWeb", "static " + path + " f=" + f.getAbsolutePath()
                    + " len=" + f.length() + " exists=" + f.isFile()
                    + " root=" + root.getAbsolutePath());
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
            hd.append((dynamic || mime.indexOf("html") >= 0) ? "Cache-Control: no-store, no-cache, must-revalidate" : "Cache-Control: max-age=600");
            hd.append("\r\n");
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
