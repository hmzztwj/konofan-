# このファン Web —— 安卓壳（手机可玩）

把 `sqweb_offline/site`（别人做的单机版 Web 客户端）装进一个安卓 App：**内置本地 HTTP 服务 + WebView 全屏加载**，装到手机上点开就能玩，不需要电脑、不需要浏览器。

## 为什么不用 file://

- 客户端用 `location.hostname === 'localhost' || '127.0.0.1'` 判断"单机模式"，`file://` 进不去；
- Chromium 在 `file://` 下会以 CORS 拦掉 ES module、`fetch()`、Service Worker。

所以壳里跑了一个最小的静态文件服务（`MiniServer`），监听 `127.0.0.1` 随机端口，WebView 加载 `http://127.0.0.1:<port>/`。顺带支持 Range 请求，视频（webm）能拖动进度。

## 目录

```
android/konofanweb/
├── AndroidManifest.xml          # package io.hmzztwj.konofanweb，minSdk 24 / targetSdk 29
├── src/io/hmzztwj/konofanweb/
│   ├── MainActivity.java        # WebView 外壳、沉浸式全屏、返回键、缺素材提示
│   └── MiniServer.java          # 本地静态服务（GET/HEAD + Range、MIME、防目录穿越）
├── res/values/strings.xml
├── res/mipmap-xxxhdpi/ic_launcher.png
├── keystore/debug.keystore      # 调试签名（口令都是 android）
├── build_apk.sh                 # aapt2 → javac → d8 → zipalign → apksigner
└── konofanweb.apk               # 产物（约 33 KB，v1/v2/v3 已签名）
```

## 构建

```bash
cd /f/python_work/逆向/android/konofanweb && bash build_apk.sh
```

依赖：`F:\android-sdk`（`platforms/android-34/android.jar`、`jdk-17`、`platform-tools`）+ `F:\python_work\逆向\tools\buildtools\android-14`（aapt2 / zipalign / d8.jar / apksigner.jar，来自 `https://mirrors.cloud.tencent.com/AndroidSDK/build-tools_r34-windows.zip`）。

注意：aapt2/d8/zipalign 是 Windows 原生程序，**参数里不能有中文路径**，脚本会先复制到 `C:/kwbuild` 再构建。

## 装到手机

1. 安装 `konofanweb.apk`（`adb install -r konofanweb.apk`，或直接拷到手机点开）。
2. 放素材，二选一：
   - **adb**：`adb push sqweb_offline/site/. /sdcard/Android/data/io.hmzztwj.konofanweb/files/site/`
   - **文件管理器**（无需 adb）：把 `site` 整个文件夹拷到手机 `Download/konofanweb/site/`，App 会自动优先用这个目录（需要授予"存储"权限；Android 13+ 因权限收紧，仍建议用 adb 或数据线方式）。
3. 打开 App。首屏是作者做的启动动画，之后进游戏。

素材约 **9.1 GB**（`site/` 里 `yuanban/packs` 6.7 GB + `sucai` 2.3 GB 是大头），手机要留够空间。

App 找素材的顺序：`外部私有目录/site` → `/sdcard/Download/konofanweb/site` → `/sdcard/Download/site` → `内部目录/site`，取第一个含 `index.html` 的。

## 已实现

- 横屏全屏（沉浸式，隐藏状态栏/导航栏）、常亮
- 本地服务：Range（视频拖动）、SPA 回落（无扩展名 → index.html）、目录穿越防护
- 返回键：先网页后退，到根再弹"退出游戏？"
- console.log/warn/error 全部转到 logcat：`adb logcat -s KonofanWeb`
- 缺 `index.html` 时弹窗直接显示目标路径与 adb 命令

## 已验证（MuMu，Android 15 / x86_64，Chrome 110 WebView）

- 安装 → 启动 → 启动动画 → 公告弹窗 → **主界面**（冒险者头像、等级、体力 10/10、金币 2000 万、左右两列功能入口、底部 7 个导航）
- **冒险 → 主线任务 → 1 部 → 1 章 → 1 章-1 → 关卡详情 → 队伍编成（战力 3384/推荐 1200）→ 出发 → 战斗场景**
  （3 WAVE、计时 1:47、AUTO/倍速/菜单、技能栏 双重吸取之触 5% / 创造之水 / 束缚 / 攻击、敌人卷心菜、[启程]和真 切入演出）全部正常
- 素材 10.8 GB（10,821 个文件）推送后可完全离线跑，无 404
- 局域网/本机服务：Range 请求正常（webm 可拖动）、`master/xxx` 无扩展名自动补 `.json`

### 已知问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `教团招募` 小窗报 `Cannot read properties of undefined (reading 'guild')` | 与服务器强相关的功能，单机 RPC 未实现该接口 | 无视，或后续在本地 RPC 里补桩 |
| 点「挑战」提示战力不足后无反应 | 队伍战力 < 关卡推荐战力（游戏自身的门槛） | 升级/强化后再来，或存档里调 `mstate[*].exp`（会同步提升等级） |
| 存档里没有默认出战队伍 | `save.party = null` | 进一次「队伍编成」选出战队，或手动置 `save.party = 0` |
| 素材没放全会卡在 99% | 客户端要校验全部 pack | 用 `push_site.bat` 推全量 |

### 调试

开了 `WebView.setWebContentsDebuggingEnabled(true)`，可以接 CDP：

```bash
ADB=/f/android-sdk/platform-tools/adb.exe
PID=$($ADB -s 127.0.0.1:16384 shell pidof io.hmzztwj.konofanweb | tr -d "
")
$ADB -s 127.0.0.1:16384 forward tcp:9223 localabstract:webview_devtools_remote_$PID
python tools/cdp.py eval "location.hash"
python tools/cdp.py tap 669 538          # 用可信鼠标事件点按（CSS 像素）
python tools/cdp.py shot out/shot.png
```

注意：MuMu 里 `adb shell input tap` 对 WebView 无效（页面只吃鼠标事件），要用 CDP 的 `Input.dispatchMouseEvent`。

## 版权

游戏素材与 Web 客户端均为原作者 / 官方版权物，本壳只做本地封装，**仅供自己离线游玩，不要公开分发**。
