# このファン Web —— 安卓壳（手机可玩）

把 `sqweb_offline/site`（单机版 Web 客户端）装进一个安卓 App：**内置本地 HTTP 服务 + WebView 全屏加载**，装到手机上点开就能玩，不需要电脑、不需要浏览器。

APK 只有 **45 KB**，素材单独放（约 10.8 GB）。

## 为什么不用 file://

- 客户端用 `location.hostname === 'localhost' || '127.0.0.1'` 判断「单机模式」，`file://` 进不去；
- Chromium 在 `file://` 下会以 CORS 拦掉 ES module、`fetch()`、Service Worker。

所以壳里跑了一个最小的静态文件服务（`MiniServer`），监听 `127.0.0.1:8787`，WebView 加载 `http://127.0.0.1:8787/`。
**端口固定**很关键：`localStorage`（存档 `oldui59.save`）按 origin 隔离，端口一变存档就"消失"。

## 启动流程（不会出白屏）

```
启动
 ├─ 找素材目录（外部私有目录/site → Download/konofanweb/site → Download/site）
 │    └─ 找不到 → 原生页面：「还没有游戏数据」+ 目标路径 + adb 命令 + [重试][导入素材]
 ├─ 起服务 → 盖一层「正在加载游戏…」原生遮罩（显示素材路径与文件数）
 ├─ 每 0.5s 轮询 location.hash，出现 #/xxx 就撤掉遮罩（≈15 秒进主界面）
 └─ 60 秒还没进 → 「加载超时」+ 最近 404 列表 + [重试][导入素材]
```

任何一步失败都停在**原生状态页**上，看得见文字、点得到按钮，绝不会只剩一片白。

## 目录

```
android/konofanweb/
├── AndroidManifest.xml          # package io.hmzztwj.konofanweb，minSdk 24 / targetSdk 29
├── src/io/hmzztwj/konofanweb/
│   ├── MainActivity.java        # 启动流程、状态遮罩、zip 导入、返回键
│   └── MiniServer.java          # 本地静态服务（GET/HEAD + Range、MIME、防目录穿越、404 记录）
├── res/values/strings.xml
├── res/mipmap-xxxhdpi/ic_launcher.png
├── keystore/debug.keystore      # 调试签名（口令都是 android）
├── build_apk.sh                 # aapt2 → javac → d8 → zipalign → apksigner
├── push_site.bat                # Windows 一键把 site 推到模拟器/手机
└── konofanweb.apk               # 产物（约 45 KB，v1/v2/v3 已签名）
```

## 构建

```bash
cd /f/python_work/逆向/android/konofanweb && bash build_apk.sh
```

依赖：`F:\android-sdk`（`platforms/android-34/android.jar`、`jdk-17`、`platform-tools`）+ `F:\python_work\逆向\tools\buildtools\android-14`（aapt2 / zipalign / d8.jar / apksigner.jar，来自 `https://mirrors.cloud.tencent.com/AndroidSDK/build-tools_r34-windows.zip`）。

注意：aapt2/d8/zipalign 是 Windows 原生程序，**参数里不能有中文路径**，脚本会先复制到 `C:/kwbuild` 再构建。

## 装到模拟器 / 手机

1. `adb install -r konofanweb.apk`（或把 APK 拷进手机点开安装）。
2. 放素材，三选一：
   - **一键脚本**：电脑上双击 `push_site.bat`（内部就是 `adb push`，约 5 分钟 / 40 MB/s）；
   - **adb 手打**：`adb push sqweb_offline/site/. /sdcard/Android/data/io.hmzztwj.konofanweb/files/site/`
   - **手机端 zip 导入**：把 site 打包成 zip 放进 `Download/`，打开 App 点「导入素材」，App 自己解压（边解压边显示进度）。
3. 打开 App，看到「正在加载游戏…」约 15 秒后进主界面。

素材约 **10.8 GB**（`yuanban/packs` 6.7 GB + `sucai` 2.3 GB 是大头），手机要留够空间。
**卸载 App 会连同这个目录一起删掉**，重装后必须重新推素材。

## 已实现

- 固定端口本地服务：Range（webm 拖动）、无扩展名自动补 `.json`、严格 404、POST 统一回空 RPC（消除满屏「服务器出错 405」）
- 启动状态遮罩 + 60 秒超时诊断（含最近 404 列表）
- zip 导入素材（`Download/*.zip`，支持 `site/` 前缀，带进度）
- 横屏全屏（沉浸式）、常亮；返回键先网页后退，到根再弹「退出游戏？」
- console.log/warn/error 转到 logcat：`adb logcat -s KonofanWeb`
- WebView 远程调试已开（`chrome://inspect` / CDP）

## 已验证（MuMu 12，Android 15 / x86_64，Chrome 110 WebView）

| 场景 | 结果 |
|---|---|
| 无素材启动 | ✅ 原生页「还没有游戏数据」+ 目标路径 + adb 命令 + 按钮（**不是白屏**） |
| 有素材启动 | ✅ 「正在加载游戏…」遮罩（显示 10135 个文件）→ 约 15 秒自动撤罩 → 公告 + 主界面 |
| 重启后存档 | ✅ 修好固定端口后，`exp` 等改动跨重启保留 |
| 主界面 | ✅ 冒险者、等级、体力 10/10、金币 2000 万、左右两列入口、底部 7 导航 |
| 冒险 → 主线任务 | ✅ 1 部 / 2 部、章节解锁条件 |
| 1 章-1 → 关卡详情 | ✅ 敌人卷心菜+狼、掉落、体力 10→5、跳过券 |
| 队伍编成 | ✅ 前排 3 人、后排「等级 8 后解放」、综合战力、推荐战力 1200 |
| 战斗 | ✅ 1/3 WAVE、倒计时、AUTO/倍速/菜单、SP 槽、4 个技能键、敌我血条、伤害数字 |
| 战斗结算 | ✅ 胜负结算页（再战 / 返回关卡 / 前往成员强化） |

## 卡池一览是空白的？—— 已修（横幅补丁 + SW 空壳）

**症状**：召唤 → 卡池一览，几条格子长得一模一样、没有任何池名。

**根因（两层）**
1. 站点数据里 37 个卡池的 `banner` 全指向同一张占位图 `sprite/webp/TitleBG__13d146.webp`（画面上印「ゲームタイトル配置」）；渲染代码把格子当**纯图片**画，`label` 只用于无障碍，所以看不到字。
2. 站点注册了 Service Worker（`pwa-sw.js`，cache `oldui-pwa-shell-*`），改过的 `local-rpc.js` 会被缓存住，改了也不生效。

**修法**
- `tools/patch_gacha_banners.py`：Pillow 生成 37 张 801×481 横幅（池名 + 开放信息 + ID），输出到 `site/yuanban/gacha/banner/pool_<id>.webp`；并在 `local-rpc.js` 的 `poolsCache = list;` 前注入
  ```js
  for (var _pi = 0; _pi < list.length; _pi++) list[_pi].banner = 'gacha/banner/pool_' + list[_pi].id + '.webp';
  ```
  原文件备份为 `local-rpc.js.bak`，`--restore` 可还原。
- App 侧：MiniServer 对 `/pwa-sw.js` 返回**空壳 SW**（`skipWaiting` + `clients.claim` + 空 fetch），并对 `.js`/`.json` 返回 `Cache-Control: no-store` ⇒ 以后改数据补丁不用再手动清缓存。

**已备好**：`gacha-banners.zip`（391 KB）= 37 张 webp + 补丁脚本，解到 `site/` 根目录即可。


## 已知问题

| 现象 | 原因 |
|---|---|
| 主页「教团招募」小窗报 `reading 'guild'` | 纯服务端功能，单机版没有，关掉即可 |
| 点「挑战」没反应 / 退回主页 | 游戏自身门槛：综合战力 < 推荐战力时按钮禁用；队伍为空（`save.party` 为 null）时退回主页 |
| 1 章-1 初始战力 1185 < 推荐 1200 | 游戏平衡，去「角色 → 强化」吃经验书升到 Lv.20+ 即可 |
| 首次进战斗要下载素材包 | 正常，战斗场景素材按需加载（本地服务，秒级） |

## 调试

```bash
adb logcat -s KonofanWeb                      # 服务端请求 + JS 控制台
adb forward tcp:9223 localabstract:webview_devtools_remote_<pid>
curl http://127.0.0.1:9223/json               # 注意：只有 /json，没有 /json/list
python tools/cdp.py eval "location.hash"      # 见仓库 tools/cdp.py
```

MuMu 下 `adb shell input tap` 对 WebView **无效**（页面只吃鼠标事件），必须用 CDP 的 `Input.dispatchMouseEvent`。
