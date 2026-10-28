# 素晴管理器（konofanmgr）

一个纯本地的小后台 App，和游戏壳（`io.hmzztwj.konofanweb`）通过**共享目录**通信：

```
/sdcard/Download/konofan_manager/
  config.json   管理器 → 游戏（卡池 / 活动 / 首领 / 彩票 配置）
  gifts.json    管理器 → 游戏（待发放或收回的礼物队列）
  state.json    游戏 → 管理器（存档快照：金币、道具、成员、卡池列表、活动列表）
```

游戏壳里的 `bridge.js`（assets 内，进游戏后自动注入）每 2 秒轮询一次：
拿到礼物 → 写进存档 → 立刻 reload（否则运行中的游戏会用内存副本覆盖）→ 回 ACK 删队列；
拿到 config → 挂到 `window.__KONOFAN_MGR__`，并对 `__localRpc('releasedGachaPools')` 做过滤。

## 实测状态

| 功能 | 状态 | 实现方式 |
|---|---|---|
| ① 礼物 赠送/收回（道具） | ✅ 已验证 | `gifts.json` → 写入**游戏内礼物箱** `save.x.presents`（`{id,t,iid,n,msg,sent,exp,gm}`）→ 游戏首页「礼物」里出现待领取 → 领取后进背包（实测 +7,777 金币，`presents` 1→0、`presentLog` +1） |
| ① 礼物 赠送/收回（角色卡） | ⚠ 走背包直发 | 角色卡类别码未确认，暂时直接写 `members`；道具走礼物箱 |
| ② 彩票号码（手填 / 随机 6 位） | ⚠ 仅写入配置 | 写 `config.lottery`，游戏端可读 `window.__KONOFAN_MGR__.lottery`；彩票 UI 的数据源还没接 |
| ③ 世界BOSS / 竞技场BOSS 切换 | ⚠ 仅写入配置 | 写 `config.boss`；BOSS 表在离线包里是写死的（`worldboss59` 模块），要换 BOSS 得改那张表 |
| ④ 卡池轮换 | ✅ 已验证 | `config.activePools` → 过滤 `releasedGachaPools`（只选 1001/1003 后，卡池一览只剩这两个） |
| ⑤ 活动开关 | ⚠ 仅写入配置 | 写 `config.enabledEvents`；活动数据源是 `yuanban/master/eventcfg59.json`（142 个 id），要真正生效需要按白名单过滤这个 JSON |
| ⑥ 启动游戏 | ✅ 已验证 | Intent 拉起 `io.hmzztwj.konofanweb/.MainActivity` |

> 「⚠ 仅写入配置」= 管理器已经把选择落到 `config.json`，游戏端也能读到（`window.__KONOFAN_MGR__`），但**游戏画面还不会因此改变**，需要下一步在游戏侧拦截对应数据源。

## 下一步（按性价比排序）

1. **活动开关**：在 `bridge.js` 里 hook `fetch('/yuanban/master/eventcfg59.json')`，按 `config.enabledEvents` 过滤后返回 → 活动关卡列表立刻可控。
2. **卡池轮换补强**：现在过滤的是“已发布池”列表；如果希望把已下线的池也放出来，需要合并 `gacha59` 模块里的完整池表。
3. **BOSS 切换**：把 `worldboss59-*.js` / `pvp59-*.js` 里的 BOSS 表抽成外部 JSON，管理器选择后由服务端覆盖。
4. **彩票**：确认彩票界面读的是哪个字段，再接 `config.lottery`。

## 构建

```bash
cd android/konofanmgr && bash build_apk.sh
```
产物 `konofanmgr.apk`（25 KB，debug 签名，`io.hmzztwj.konofanmanager`）。
依赖：`F:ndroid-sdk\platformsndroid-34ndroid.jar`、`tools/buildtools/android-14`、`keystore/debug.keystore`。

## 注意

- 两个 App 都是 `targetSdk 29` + `requestLegacyExternalStorage`，才能直接读写 `/sdcard/Download/konofan_manager`。
- 改完礼物后游戏会**自动刷新一次**，属正常现象（存档换新后必须重新读）。
- 「清空存档」是不可逆操作，管理器里要二次确认。
