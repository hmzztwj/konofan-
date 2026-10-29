package io.hmzztwj.konofanmanager;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * このファン Web 安卓外壳。
 *
 * 1) 在 127.0.0.1 起迷你 HTTP 服务，把 site/ 当游戏根目录（file:// 会被 Chromium 的 CORS 拦住）；
 * 2) WebView 全屏加载 http://127.0.0.1:port/；
 * 3) 全程盖一层原生状态页：缺素材 / 解压中 / 加载中 / 加载超时 都有明确文字与按钮，
 *    避免出现「白屏 / 卡在 99%」这种没法自救的状态。
 */
public class GameActivity extends Activity {

    private static final String TAG = "KonofanWeb";

    /** 素材候选目录（相对外部私有目录、/sdcard/Download），按顺序探测。 */
    private static final String[] SITE_CANDIDATES = {"site", "konofanweb/site", "konofanweb"};

    private FrameLayout root;
    private WebView webView;
    private LinearLayout overlay;
    private TextView statusText;
    private TextView detailText;
    private ProgressBar spinner;
    private Button retryBtn;
    private Button importBtn;

    private MiniServer server;
    private String siteRoot;
    private volatile boolean pageReady = false;
    private int pollTicks = 0;
    private final Handler ui = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        hideSystemUi();

        root = new FrameLayout(this);
        setContentView(root, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        buildWebView();
        buildOverlay();
        startServerThenLoad();
    }

    // ------------------------------------------------------------------ UI

    private void buildWebView() {
        webView = new WebView(this);
        webView.setBackgroundColor(Color.BLACK);
        WebView.setWebContentsDebuggingEnabled(true);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (url.startsWith("http://127.0.0.1:")) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, req.getUrl()));
                } catch (Exception e) {
                    Log.w(TAG, "no handler for " + url);
                }
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage m) {
                Log.i(TAG, "js " + m.messageLevel() + ": " + m.message()
                        + " @" + m.sourceId() + ":" + m.lineNumber());
                return true;
            }
        });

        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void buildOverlay() {
        overlay = new LinearLayout(this);
        overlay.setOrientation(LinearLayout.VERTICAL);
        overlay.setGravity(Gravity.CENTER);
        overlay.setBackgroundColor(Color.rgb(18, 20, 26));
        overlay.setPadding(dp(48), dp(28), dp(48), dp(24));

        TextView title = new TextView(this);
        title.setText("このファン Web");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);

        statusText = new TextView(this);
        statusText.setTextColor(Color.rgb(200, 208, 224));
        statusText.setTextSize(16);
        statusText.setGravity(Gravity.CENTER);
        statusText.setPadding(0, dp(12), 0, dp(10));

        spinner = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        spinner.setIndeterminate(true);
        spinner.setVisibility(View.GONE);
        LinearLayout.LayoutParams plp = new LinearLayout.LayoutParams(dp(320), dp(6));
        plp.bottomMargin = dp(6);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER);
        buttons.setPadding(0, dp(6), 0, dp(10));

        retryBtn = new Button(this);
        retryBtn.setText("重试");
        retryBtn.setOnClickListener(v -> startServerThenLoad());

        importBtn = new Button(this);
        importBtn.setText("导入素材");
        importBtn.setOnClickListener(v -> showImportDialog());

        LinearLayout.LayoutParams blp = new LinearLayout.LayoutParams(dp(130), dp(46));
        blp.leftMargin = dp(6);
        blp.rightMargin = dp(6);
        buttons.addView(retryBtn, blp);
        buttons.addView(importBtn, blp);

        detailText = new TextView(this);
        detailText.setTextColor(Color.rgb(126, 136, 156));
        detailText.setTextSize(12);
        detailText.setPadding(0, dp(4), 0, dp(4));

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(detailText);

        overlay.addView(title);
        overlay.addView(statusText);
        overlay.addView(spinner, plp);
        overlay.addView(buttons);
        overlay.addView(new View(this), new LinearLayout.LayoutParams(1, 1));
        overlay.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        root.addView(overlay, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private void setStatus(String status, String detail, boolean busy) {
        statusText.setText(status);
        if (detail != null) detailText.setText(detail);
        spinner.setVisibility(busy ? View.VISIBLE : View.GONE);
        retryBtn.setVisibility(busy ? View.GONE : View.VISIBLE);
        importBtn.setVisibility(busy ? View.GONE : View.VISIBLE);
        overlay.setVisibility(View.VISIBLE);
    }

    private void hideOverlay() {
        overlay.setVisibility(View.GONE);
    }

    // -------------------------------------------------------------- startup

    private void startServerThenLoad() {
        pageReady = false;
        pollTicks = 0;
        setStatus("正在准备本地服务…", "", true);

        new Thread(() -> {
            File dir = findSiteDir();
            if (dir == null) {
                ui.post(() -> setStatus("还没有游戏数据", missingDetail(), false));
                return;
            }
            siteRoot = dir.getAbsolutePath();
            try {
                if (server != null) server.stop();
                server = new MiniServer(dir, 8787);
                server.start();
            } catch (Exception e) {
                Log.e(TAG, "server failed", e);
                ui.post(() -> setStatus("本地服务启动失败", String.valueOf(e), false));
                return;
            }
            final String url = "http://127.0.0.1:" + server.getPort() + "/";
            Log.i(TAG, "serving " + siteRoot + " at " + url);
            ui.post(() -> {
                setStatus("正在加载游戏…",
                        siteRoot + "\n" + countFiles(siteRoot) + " 个文件", true);
                webView.loadUrl(url);
                schedulePoll();
            });
        }, "server-start").start();
    }

    private File findSiteDir() {
        List<File> bases = new ArrayList<>();
        File legacy = new File("/sdcard/Android/data/io.hmzztwj.konofanweb/files/site");
        if (legacy.isDirectory() && new File(legacy, "index.html").isFile()) return legacy;
        File priv = getExternalFilesDir(null);
        if (priv != null) bases.add(priv);
        bases.add(new File(Environment.getExternalStorageDirectory(), "Download"));
        for (File base : bases) {
            for (String sub : SITE_CANDIDATES) {
                File f = new File(base, sub);
                if (new File(f, "index.html").isFile()) {
                    Log.i(TAG, "site root: " + f);
                    return f;
                }
            }
        }
        return null;
    }

    private String missingDetail() {
        File priv = getExternalFilesDir(null);
        String target = (priv != null ? priv.getAbsolutePath()
                : "/sdcard/Android/data/io.hmzztwj.konofanweb/files") + "/site";
        return "把 sqweb_offline 里的 site 目录整个复制到：\n" + target
                + "\n\n电脑上用 adb 推：\nadb push site/. " + target + "/"
                + "\n\n或者把打包好的 zip 放到 Download 目录，然后点「导入素材」。";
    }

    /** 把 assets/bridge.js 落到 files 目录，服务器按 /__mgr/bridge.js 下发，任何 reload 都能重新加载。 */
    private void copyBridgeToFiles() {
        try {
            java.io.InputStream is = getAssets().open("bridge.js");
            java.io.File out = new java.io.File(getFilesDir(), "bridge.js");
            java.io.FileOutputStream fo = new java.io.FileOutputStream(out);
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) fo.write(buf, 0, n);
            fo.close(); is.close();
            Log.i(TAG, "bridge copied -> " + out);
        } catch (Exception e) {
            Log.w(TAG, "bridge copy failed: " + e);
        }
    }

    /** 注入管理器桥（assets/bridge.js），失败不影响游戏本体。 */
    private void injectBridge() {
        try {
            java.io.InputStream is = getAssets().open("bridge.js");
            java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
            is.close();
            String js = new String(bos.toByteArray(), "UTF-8");
            webView.evaluateJavascript(js, v -> Log.i(TAG, "bridge injected: " + v));
        } catch (Exception e) {
            Log.w(TAG, "bridge inject failed: " + e);
        }
    }

    /** 轮询 location.hash：游戏是 hash 路由，真正进入会变成 #/home。 */
    private void schedulePoll() {
        ui.postDelayed(() -> {
            if (pageReady) return;
            pollTicks++;
            if (pollTicks % 6 == 3) injectBridge();   // 反复注入，SPA 重写文档会丢全局
            webView.evaluateJavascript(
                    "(function(){try{var c=document.querySelector('canvas');if(c&&c.width>200)return '#/ready';return location.hash||''}catch(e){return 'ERR'}})()",
                    value -> {
                        String hash = value == null ? "" : value.replace("\"", "");
                        if (hash.startsWith("#/") && hash.length() > 2) {
                            pageReady = true;
                            hideOverlay();
                            copyBridgeToFiles();
        injectBridge();
                            return;
                        }
                        if (pollTicks > 40) {           // ~20 秒仍无 hash：只要服务已通就先放行
                            pageReady = true; hideOverlay(); injectBridge(); return;
                        }
                        if (pollTicks > 120) {          // ~60 秒
                            onLoadTimeout(hash);
                            return;
                        }
                        if (pollTicks % 10 == 0) {
                            statusText.setText("正在加载游戏… 已等待 " + (pollTicks / 2) + " 秒");
                        }
                        schedulePoll();
                    });
        }, 500);
    }

    private void onLoadTimeout(String hash) {
        StringBuilder sb = new StringBuilder();
        sb.append("页面地址：").append(hash.isEmpty() ? "(空)" : hash).append('\n');
        sb.append("素材目录：").append(siteRoot).append('\n');
        sb.append("文件数：").append(siteRoot == null ? "-" : countFiles(siteRoot)).append('\n');
        List<String> missing = server == null ? new ArrayList<>() : server.recentMisses();
        if (!missing.isEmpty()) {
            sb.append("\n最近 404：\n");
            for (int i = 0; i < Math.min(8, missing.size()); i++) {
                sb.append("  ").append(missing.get(i)).append('\n');
            }
            sb.append("\n多半是素材没复制全，重新推一次 site 目录后点重试。");
        } else {
            sb.append("\n服务端没记录到 404，可能是素材不完整或版本不匹配。\n点重试，或重新导入素材。");
        }
        setStatus("加载超时", sb.toString(), false);
    }

    // --------------------------------------------------------------- import

    private void showImportDialog() {
        File dl = new File(Environment.getExternalStorageDirectory(), "Download");
        List<File> zips = new ArrayList<>();
        File[] all = dl.listFiles();
        if (all != null) {
            for (File f : all) {
                String n = f.getName().toLowerCase(Locale.ROOT);
                if (f.isFile() && n.endsWith(".zip")) zips.add(f);
            }
        }
        final List<File> found = zips;
        String[] items = new String[found.size() + 1];
        items[0] = "查看手动复制说明";
        for (int i = 0; i < found.size(); i++) {
            items[i + 1] = "解压 " + found.get(i).getName()
                    + "（" + (found.get(i).length() / 1024 / 1024) + " MB）";
        }
        new AlertDialog.Builder(this)
                .setTitle("导入素材")
                .setItems(items, (d, which) -> {
                    if (which == 0) {
                        new AlertDialog.Builder(this)
                                .setTitle("手动复制")
                                .setMessage(missingDetail())
                                .setPositiveButton("知道了", null)
                                .show();
                    } else {
                        importZip(found.get(which - 1));
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void importZip(File zip) {
        setStatus("正在解压素材…", zip.getName(), true);
        new Thread(() -> {
            File dest = new File(getExternalFilesDir(null), "site");
            long total = 0;
            int files = 0;
            try (ZipFile zf = new ZipFile(zip)) {
                Enumeration<? extends ZipEntry> en = zf.entries();
                byte[] buf = new byte[1 << 16];
                while (en.hasMoreElements()) {
                    ZipEntry e = en.nextElement();
                    String name = e.getName();
                    if (name.startsWith("site/")) name = name.substring(5);
                    if (name.isEmpty() || name.endsWith("/")) continue;
                    File out = new File(dest, name);
                    File parent = out.getParentFile();
                    if (parent != null && !parent.exists() && !parent.mkdirs()) continue;
                    try (InputStream in = zf.getInputStream(e);
                         FileOutputStream os = new FileOutputStream(out)) {
                        int n;
                        while ((n = in.read(buf)) > 0) {
                            os.write(buf, 0, n);
                            total += n;
                        }
                    } catch (Exception ignored) {
                    }
                    files++;
                    if (files % 200 == 0) {
                        final int f = files;
                        final long t = total;
                        ui.post(() -> statusText.setText(
                                "正在解压素材… " + f + " 个文件 / " + (t >> 20) + " MB"));
                    }
                }
                final int f = files;
                final long t = total;
                ui.post(() -> {
                    setStatus("解压完成", f + " 个文件 / " + (t >> 20) + " MB\n点「重试」进入游戏", false);
                    startServerThenLoad();
                });
            } catch (Exception e) {
                Log.e(TAG, "unzip failed", e);
                ui.post(() -> setStatus("解压失败", String.valueOf(e), false));
            }
        }, "unzip").start();
    }

    // ---------------------------------------------------------------- utils

    private int countFiles(String dir) {
        int[] n = {0};
        countInto(new File(dir), n, 0);
        return n[0];
    }

    private void countInto(File d, int[] n, int depth) {
        if (depth > 5 || n[0] > 20000) return;
        File[] list = d.listFiles();
        if (list == null) return;
        for (File f : list) {
            if (f.isDirectory()) countInto(f, n, depth + 1);
            else n[0]++;
        }
    }

    private int dp(int v) {
        return Math.round(getResources().getDisplayMetrics().density * v);
    }

    private void hideSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (overlay.getVisibility() == View.VISIBLE) {
                finish();
                return true;
            }
            if (webView.canGoBack()) {
                webView.goBack();
            } else {
                new AlertDialog.Builder(this)
                        .setMessage("退出游戏？")
                        .setPositiveButton("退出", (d, w) -> finish())
                        .setNegativeButton("继续玩", null)
                        .show();
            }
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onDestroy() {
        if (server != null) server.stop();
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
