# dist

二进制不放进 git，走 Releases 分发：

**https://github.com/hmzztwj/konofan-/releases/download/v0.1.0/konofan_v570_demod.apk**

| 文件 | 大小 | 说明 |
|---|---|---|
| `konofan_v570_demod.apk` | 243,365,231 B | 去 mod 的 5.7.0 客户端，797 条目，v1/v2/v3 签名，MuMu Android 15 验证启动 |

构建方法：`tools/build_clean_apk.py`，细节见 `docs/04_安装包还原.md`。

> 该包**仍然无法离线游玩**：业务 API 已消失、bundle CDN 403、本地缺 20,841 个 bundle。
> 原因与证据见 `docs/05_离线化可行性.md`。
