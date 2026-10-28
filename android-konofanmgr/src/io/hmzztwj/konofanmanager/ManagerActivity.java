package io.hmzztwj.konofanmanager;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;

/**
 * 素晴管理器：一个纯本地的小后台，通过共享目录
 * /sdcard/Download/konofan_manager/ 与游戏壳（io.hmzztwj.konofanweb）通信。
 *
 *   config.json  管理器 → 游戏：卡池/活动/首领等配置
 *   gifts.json   管理器 → 游戏：待发放（或收回）的礼物队列
 *   state.json   游戏 → 管理器：存档快照（金币、成员、卡池、活动列表）
 */
public class ManagerActivity extends Activity {
    private static final String TAG = "KonofanMgr";
    private static final String GAME_PKG = "io.hmzztwj.konofanweb";
    private static final String GAME_ACT = "io.hmzztwj.konofanweb.MainActivity";

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(android.webkit.ConsoleMessage m) {
                Log.i(TAG, "js: " + m.message() + " @" + m.lineNumber());
                return true;
            }
        });
        web.addJavascriptInterface(new Bridge(), "Mgr");
        setContentView(web);
        web.loadUrl("file:///android_asset/ui/index.html");
    }

    private static File sharedDir() {
        File d = new File(Environment.getExternalStorageDirectory(), "Download/konofan_manager");
        if (!d.exists()) d.mkdirs();
        return d;
    }

    private class Bridge {
        @JavascriptInterface
        public String dir() {
            return sharedDir().getAbsolutePath();
        }

        @JavascriptInterface
        public String read(String name) {
            File f = new File(sharedDir(), name);
            if (!f.isFile()) return "";
            try {
                FileInputStream in = new FileInputStream(f);
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                byte[] b = new byte[8192];
                int n;
                while ((n = in.read(b)) > 0) bos.write(b, 0, n);
                in.close();
                return new String(bos.toByteArray(), "UTF-8");
            } catch (Exception e) {
                return "";
            }
        }

        @JavascriptInterface
        public boolean write(String name, String text) {
            try {
                FileOutputStream fo = new FileOutputStream(new File(sharedDir(), name));
                fo.write(text.getBytes("UTF-8"));
                fo.close();
                return true;
            } catch (Exception e) {
                Log.w(TAG, "write fail " + e);
                return false;
            }
        }

        @JavascriptInterface
        public void toast(String msg) {
            runOnUiThread(() -> Toast.makeText(ManagerActivity.this, msg, Toast.LENGTH_SHORT).show());
        }

        /** 启动游戏（游戏壳会自己找素材目录、起本地服务） */
        @JavascriptInterface
        public boolean launchGame() {
            try {
                Intent i = new Intent();
                i.setComponent(new ComponentName(GAME_PKG, GAME_ACT));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
                return true;
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(ManagerActivity.this,
                        "没找到游戏壳 App（" + GAME_PKG + "），请先安装 konofanweb.apk",
                        Toast.LENGTH_LONG).show());
                return false;
            }
        }
    }
}
