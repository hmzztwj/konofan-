# konofan-offline —《この素晴らしい世界に祝福を！ファンタスティックデイズ》离线化逆向工程

日服已于 **2025-01-30 停服**。这个仓库是围绕一份 2024-10 的存量客户端数据 + 5.7.0 APK
做的完整逆向作业记录与工具链，目标是**搞清楚它能不能离线跑起来、卡在哪、怎么继续**。

> 仅供学习研究。仓库内不含游戏本体与美术资源，工具输出的衍生数据请自行留存、勿再分发。

## 一、已确认的事实（都有实验支撑）

| 层 | 结论 |
|---|---|
| 客户端 | Unity 2022.3.21f1 + IL2CPP metadata v29 + Utage ADV 引擎，包名 `jp.co.sumzap.pj0007` |
| 清单层 | Addressables catalog 41 MB，31,592 个资产 / 23,069 个 bundle，自定义下载器 `Wonder.Api.BundleDownloader` |
| 资源层 | 本地缓存 2,228 个 UnityFS v8 bundle（未加密），导出 **21,790 张 PNG**，类型分布见 `docs/01` |
| 媒体层 | CRI CPK 626 + USM 7,032，**文件名是按 SHA256 加密的**，已破解命名算法并全量还原（7,658/7,658） |
| 数据层 | 279 个 `MasterData/*.data` 是 **AES-256-CBC + PKCS#7 + 固定 IV**，base64 文本；**密钥已拿到**（见 `docs/02`） |
| 剧情层 | Utage `AdvImportBook` / `AdvChapterData`，含完整 Excel 式脚本网格（`Command/Arg1/Text/Voice`），本地 5 章可读 |

## 三、ローカル版クライアント v0.1（`webapp/`）

解出来的数据不是只能看——现在有一个**能玩**的本地客户端：

```bash
python tools/build_webapp.py   # 生成 data.js + 图片索引
start webapp/index.html        # 直接双击也行（file://）
```

已实现：**冒険（43 区域 / 1,083 关卡，通关解锁）・編成（617 张卡里选 3）・回合制战斗（3 WAVE、速度序、通常/技能×2/必杀、SP 共享、敌方 weight AI）・成员图鉴（★4 342 / ★3 202 / ★2 48）**，
战斗数值全部来自 `member`/`skill_ac`/`skill_sp`/`battle_enemy`/`battle_wave`/`mainquest_stage`，背景与头像是从缓存的 bundle 里导出的真素材。

路线图与已知限制见 [`webapp/README.md`](webapp/README.md)。

## 四、密钥（从运行中的进程内存里读出来的，不是猜的）

```
AES-256 key = 851c20916d7a895bc14ceba139e3dc253486b30b858140c41c8a7e9fe99aec72
IV          = dcaa69cc863200d4eb74b4980bd60383
模式        = AES-256-CBC / PKCS#7 / 固定 IV，文件本体是 base64 文本
```

这组密钥**跨构建恒定**：5.7.0 mod 版、去 mod 版、更早的用户数据快照都能解。
取法见 `docs/02`（`/proc/<pid>/mem` 精准读 `AesEncryption.static_fields[0]`）。

## 三、CRI 媒体命名算法（已破解并验证）

```
磁盘名 = UrlEncode( Base64( SHA256( UTF8( "p8c3oOXf" + 不含扩展名的原名 ) ) ) + 原扩展名 )
```

`p8c3oOXf` 是 `ShaEncryption` 的 Salt（ObscuredString，读 `fakeValue` 即可得明文）。
验证：7,658 个磁盘文件 ↔ catalog 里 11,262 条 CRI 条目，**全部命中，0 未匹配**。

## 四、离线化到底卡在哪（这是本仓库最重要的结论）

1. **业务 API 域名已消失**：`api.konosubafd.jp` NXDOMAIN；`https://static.konosubafd.jp/versions/*.json` 还活着，
   客户端就是从这里读 `api_url` / `asset_url` 的（DTO：`Wonder.Api.CheckAPIURLResponseDTO`）。
2. **首屏资源全在服务端**：APK 只内置 6 个 bundle（shader/font/include/storyadvengine/tutorial×2），
   标题页与首页 UI 都在 23,069 个远程 bundle 里 → 连"通信错误"弹窗都画不出来，只能白屏。
3. **官方 bundle CDN 已关闭直链**：`.../bundles/5.7.0/6_.../` 与 `.../bundles/5.9.0/.../` 全部 **403**，
   只有 `versions/*.json` 还能取 → **没法补齐缺失的 20,841 个 bundle**。
4. **客户端不认自签 CA**：已把自签 CA 同时装进 `/system/etc/security/cacerts` 与
   `/apex/com.android.conscrypt/cacerts`（bind mount，root + Permissive），Android 侧任何 Java 栈都会认；
   但客户端是 Unity 原生 TLS 栈，仍然回 `SSLV3_ALERT_CERTIFICATE_UNKNOWN`（实测 19~27 次/30 秒）。
   排除证书固定：metadata 里没有 `sha256/`、`CertificatePinner`，APK 里也没有 `.pem/.crt`。

⇒ **结论**：在没有服务器协议、也没有资源 CDN 的前提下，"改造成可离线正常游玩"不是补几行代码能完成的事，
  它等价于**重写一个私服 + 重建全部客户端资源**。官方后来推出的 5 个离线版 App（`jp.co.sumzap.pj0016` 等）
  正是官方为此另做的产品。详见 `docs/05`。

## 五、仓库里有什么

```
docs/       逆向分析文档（结构、加密、媒体、安装包还原、离线化可行性、工具索引、WebView 壳补丁）
tools/      全部自写工具（Python 3.10）：解密、命名还原、catalog 解析、bundle 导出、
            AXML/dex 补丁、重打包、内存读密钥、MITM、mock server、WebView CDP 调试等
data/       清单与索引（资产清单 31,592 行、CRI 映射 7,658 行、MasterData 索引、剧情索引）
server/     mock API + TLS 中间人（当前被客户端 TLS 信任卡住，留作后续）
android-konofanweb/   WebView 壳（第一版，site/ 由 MiniServer 托管）
android-konofanmgr/   管理器壳（游戏内管理器 + 注入 bridge.js，离线补丁落在这里）
patches/site/         站点侧补丁文件（__kf_lot.js、占位 CSS）与部署说明
dist/       成品说明（去 mod 的 APK：Releases v0.1.0）
```

## 六、安卓 WebView 壳（真机可玩客户端）

WebView 壳把 `site/`（Vite 构建的离线客户端 + 本地 mock 数据）用内置 HTTP 服务
（MiniServer，`127.0.0.1:8787`）托管起来，Android 端只负责起服务 + 开 WebView。
桥接层 `bridge.js` 负责存档接管、召唤 RPC、礼物、命令下发，以及**彩票/商会等离线补丁**。

已修的三处（细节与复现步骤见 [`docs/07`](docs/07_安卓离线客户端补丁记录.md)）：

1. **教团招募报错** `Cannot read properties of undefined (reading 'guild')`：`/api/guild/home`
   必须回**扁平** `{home:{guild:null,config:{ads:{adsOpen:false}}}}`，不能套 `data`。
2. **教团/商会页「读取失败，请检查网络后再点一次」**：其实是 Vite 预载的
   `guild59-B6De0oYB.css` / `imageAnnounce-8fL6REue.css` 404，补占位 CSS 即好，与网络无关。
3. **「我的彩券」永远是空列表**：真正接管请求的是管理器注入的 `bridge.js` 前置彩票 IIFE
   （返回 `{data:{...}}`），其 `home()` 原先硬编码 `mine:[]`；已改为按天汇总票根、
   20:00 后结算（对中 6/5/4/3 位分四档），并支持「一等奖×1」这类中奖展示。

## 七、快速开始

```bash
# 1. 解密 MasterData（把 Data/ 指向你的 files/Data 目录）
python tools/decrypt_masterdata.py

# 2. 导出图片（需要 UnityCache）
python tools/extract_assets.py images out/assets

# 3. 还原 CRI 媒体文件名
python tools/cri_rename.py

# 4. 重打包 APK（去 mod）
python tools/build_clean_apk.py
```

## 八、许可

代码 MIT。游戏资源、文本、音频的版权归 Sumzap / 角川 / 相关权利方所有，本仓库不提供这些内容。
