package io.hmzztwj.konofanweb;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;

import java.io.File;

/**
 * 外壳：起本地 HTTP 服务托管 site/ → 用 WebView 全屏加载 http://127.0.0.1:port/。
 * 之所以走 127.0.0.1 而不是 file://：客户端把 localhost/127.0.0.1 当作单机模式开关，
 * 而且 ES module、fetch、Service Worker 在 file:// 下都被 Chromium 拦住。
 */
public class MainActivity extends Activity {
    private static final String TAG = "KonofanWeb";
    private static final int PORT = 8787;

    private WebView webView;
    private MiniServer server;
    private FrameLayout root;
    private TextView hint;
    private final Handler ui = new Handler(Looper.getMainLooper());

    /** 候选素材根目录：优先 App 私有外部目录，其次手机公共 Download（可以用文件管理器直接拷进去）。 */
    private File[] siteCandidates() {
        java.util.ArrayList<File> list = new java.util.ArrayList<File>();
        File base = getExternalFilesDir(null);
        if (base == null) base = getFilesDir();
        list.add(new File(base, "site"));
        list.add(new File("/sdcard/Download/konofanweb/site"));
        list.add(new File("/sdcard/Download/site"));
        File internal = new File(getFilesDir(), "site");
        list.add(internal);
        return list.toArray(new File[0]);
    }

    private File siteDir() {
        File[] cands = siteCandidates();
        for (File f : cands) {
            if (new File(f, "index.html").isFile()) return f;
        }
        return cands[0];
    }

    /** targetSdk 29 + requestLegacyExternalStorage：在 Android 10 及以下直接可读 /sdcard/Download。 */
    private void ensureReadPermission() {
        if (Build.VERSION.SDK_INT >= 23) {
            if (checkSelfPermission("android.permission.READ_EXTERNAL_STORAGE")
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{"android.permission.READ_EXTERNAL_STORAGE"}, 1);
            }
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        hideSystemUi();

        root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        setContentView(root);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.BLACK);
        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        hint = new TextView(this);
        hint.setTextColor(Color.parseColor("#c9d1e0"));
        hint.setTextSize(15f);
        hint.setPadding(48, 48, 48, 48);
        hint.setText("准备中…");
        root.addView(hint, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        WebView.setWebContentsDebuggingEnabled(true);
        configureWebView();
        ensureReadPermission();

        File site = siteDir();
        if (!site.isDirectory()) site.mkdirs();
        File index = new File(site, "index.html");
        if (!index.isFile()) {
            showSetup(site);
            return;
        }
        startAndLoad(site);
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setLoadsImagesAutomatically(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        if (Build.VERSION.SDK_INT >= 21) {
            CookieManager.getInstance().setAcceptCookie(true);
            CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        }
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                String scheme = u.getScheme() == null ? "" : u.getScheme();
                if (scheme.equals("http") || scheme.equals("https")) {
                    String host = u.getHost() == null ? "" : u.getHost();
                    if (host.equals("127.0.0.1") || host.equals("localhost")) return false;
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, u));
                    } catch (Exception ignored) { }
                    return true;
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                hint.setVisibility(View.GONE);
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage m) {
                Log.i(TAG, "js " + m.message() + " @" + m.sourceId() + ":" + m.lineNumber());
                return true;
            }
        });
    }

    private void startAndLoad(final File site) {
        hint.setText("正在启动本地服务…");
        hint.setVisibility(View.VISIBLE);
        new Thread(new Runnable() {
            @Override public void run() {
                try {
                    server = new MiniServer(site, PORT);
                    final int port = server.start();
                    Log.i(TAG, "serving " + site + " on http://127.0.0.1:" + port + "/");
                    ui.post(new Runnable() {
                        @Override public void run() {
                            webView.loadUrl("http://127.0.0.1:" + port + "/");
                        }
                    });
                } catch (Exception e) {
                    Log.e(TAG, "server start failed", e);
                    final String msg = String.valueOf(e);
                    ui.post(new Runnable() {
                        @Override public void run() {
                            hint.setText("本地服务启动失败：" + msg);
                            hint.setVisibility(View.VISIBLE);
                        }
                    });
                }
            }
        }, "mini-http-start").start();
    }

    /** 首次启动：告诉用户把 site 推到哪里（adb push / 文件管理器均可）。 */
    private void showSetup(final File site) {
        hint.setVisibility(View.GONE);
        String path = site.getAbsolutePath();
        String msg = "还没有游戏数据。\n\n"
                + "把网页版的数据目录（含 index.html 的那个 site 文件夹）放到：\n\n"
                + path + "\n\n"
                + "用电脑执行：\n"
                + "adb push 本地site/. " + path + "/\n\n"
                + "或者用手机文件管理器把 site 文件夹整体复制到上面这个位置，然后点「重新加载」。\n\n"
                + "（数据约 8.5 GB，放完就是完全离线可玩）";
        new AlertDialog.Builder(this)
                .setTitle("このファン Web — 初始化")
                .setMessage(msg)
                .setPositiveButton("重新加载", new DialogInterface.OnClickListener() {
                    @Override public void onClick(DialogInterface d, int w) {
                        File idx = new File(site, "index.html");
                        if (idx.isFile()) {
                            hint.setVisibility(View.VISIBLE);
                            hint.setText("正在启动本地服务…");
                            startAndLoad(site);
                        } else {
                            showSetup(site);
                        }
                    }
                })
                .setNegativeButton("退出", new DialogInterface.OnClickListener() {
                    @Override public void onClick(DialogInterface d, int w) { finish(); }
                })
                .setCancelable(false)
                .show();
    }

    private void hideSystemUi() {
        View decor = getWindow().getDecorView();
        decor.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (webView != null && webView.canGoBack()) {
                webView.goBack();
                return true;
            }
            if (webView != null) {
                new AlertDialog.Builder(this)
                        .setMessage("退出游戏？")
                        .setPositiveButton("退出", new DialogInterface.OnClickListener() {
                            @Override public void onClick(DialogInterface d, int w) { finish(); }
                        })
                        .setNegativeButton("继续玩", null)
                        .show();
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) webView.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (server != null) server.stop();
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
