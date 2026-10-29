# patches/site — 站点侧补丁怎么用

仓库里不放 `site/`（约 10 GB，是 Vite 构建产物 + 离线数据）。这里只放**需要覆盖/新增**的少量文件，
以及它们该落在哪。完整背景见 [`docs/07`](../../docs/07_安卓离线客户端补丁记录.md)。

设备路径（管理器壳）：

```
/storage/emulated/0/Android/data/io.hmzztwj.konofanmanager/files/site
```

`__bridge.js` 的**真身**在 APK 资产里，推送只用于现场验证：

```
android-konofanmgr/build_apk.sh   # 装回新包后才永久生效
```

## 文件对照

| 本目录 | 落到设备 | 作用 |
|---|---|---|
| `__kf_lot.js` | `site/__kf_lot.js` | `/api/guild/*` 扁平兜底（`{home:{guild:null,config:{ads:{adsOpen:false}}}}`）、买票号码 `rand6()`、彩票数据兜底 |
| `guild59-B6De0oYB.css` | `site/assets/guild59-B6De0oYB.css` | 占位 CSS。缺它时 Vite `__vitePreload` reject，教团页只显示「读取失败，请检查网络后再点一次」 |
| `imageAnnounce-8fL6REue.css` | `site/assets/imageAnnounce-8fL6REue.css` | 同上，公告图片模块 |

> CSS 内容就一行注释：`/* offline bundle: stylesheet not shipped (placeholder so dynamic import succeeds) */`。
> 游戏界面是 PixiJS canvas，样式表基本不参与绘制，空文件没有副作用。

## 部署

```bash
export MSYS_NO_PATHCONV=1
ADB=/f/android-sdk/platform-tools/adb.exe
D=/storage/emulated/0/Android/data/io.hmzztwj.konofanmanager/files/site

$ADB push __kf_lot.js  "$D/__kf_lot.js"
$ADB push guild59-B6De0oYB.css    "$D/assets/guild59-B6De0oYB.css"
$ADB push imageAnnounce-8fL6REue.css "$D/assets/imageAnnounce-8fL6REue.css"

# index.html 里 __kf_lot.js 的 ?v= 要跟着改（WebView 会缓存）
$ADB shell am force-stop io.hmzztwj.konofanmanager
$ADB shell am start -n io.hmzztwj.konofanmanager/.GameActivity
```

彩票的「我的彩券」逻辑不在这里，在 `android-konofanmgr/assets/bridge.js` 的前置 IIFE —— 改那里、重打包。
