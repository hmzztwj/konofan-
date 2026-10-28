# 03 · CRI 媒体命名 与 Utage 剧情

## 一、CRI 文件名加密

磁盘上是 `%2B4LrLB0jki28ltTAdxmkONoAZLRn1Gvc4Xy7RnP%2Fv3Q%3D.cpk` 这种 URL-encoded base64，
解码后固定 32 字节、首字节恒为 `0xFB`（所以文件名永远以 `%2B` 开头）。

### 反汇编得到的公式

`Wonder.Util.Crypt.ShaEncryption.EncryptStreamingAssetsNameString`（RVA `0x2E816D0`）：

```
SHA256.Create() → Encoding.UTF8 → String.Format("{0}{1}", Salt, 不含扩展名的原名)
                → ComputeHash → Convert.ToBase64String → Base64ToBase64Url
```

**实测用的是标准 base64（不是 base64url）**，再做 URL 转义：

```
磁盘名 = UrlEncode( Base64( SHA256( UTF8( "p8c3oOXf" + 原名去扩展名 ) ) ) + 原扩展名 )
```

### Salt 怎么来的

`ShaEncryption.static_fields[0]` 是 `ObscuredString`（CodeStage ACTk）。
不用自己重算 XOR——**读它的 `fakeValue` 字段就是明文**：

```
+0x00 klass  +0x08 monitor  +0x10 currentCryptoKey  +0x18 hiddenValue
+0x20 inited +0x28 fakeValue(明文)  +0x30 fakeValueActive
```

脚本：`tools/read_obscured.py Sha` → `p8c3oOXf`。

### 验证

7,658 个磁盘文件 ↔ catalog 11,262 条 CRI 条目，**7,658/7,658 命中，0 未匹配**，
命中键都是"不含扩展名的裸名"（`gacha_cut_410835_41`、`bgm_ingame_quest_003` 等）。
`tools/cri_rename.py` 输出 `out/cri_sorted/<分类>/<明文名>` + `data/cri_manifest.csv`。

## 二、媒体实体

| 容器 | 数量 | 说明 |
|---|---|---|
| `.cpk` | 626 | CriWare CPK，内部含多个 `HCA\0` 音频流（样本 22/56/2 条） |
| `.usm` | 7,032 | Sofdec2，`CRID` + `@UTF`；样本 752,416 B，36 个 `@SFV` 块，**0 个 `@ALP`/`@SFA`** → 纯视频，音频在配套 cpk |

- HCA 可直接用 vgmstream 解码：从 `HCA\0` 偏移截断存成 `.hca`，`vgmstream-cli -m` 识别成功（44 kHz / 2ch）。
- vgmstream **不能直接吃 .cpk**（`failed opening`）。
- `tools/cpk.py` 是自制 @UTF 解析器，但 CPK 头字段布局与所有公开实现都差 1~8 字节，未能稳定解析
  （`table_size=0x358`，字符串表实际从 0x19A 起，`CpkHeader` 在 0x1A1）。**这块没做完**。

## 三、Utage 剧情格式

缓存里有 6 个 `*.chapter.asset` bundle，内容是 Utage 的导入数据：

```
AdvChapterData   chapterName / dataList(PPtr→AdvImportBook) / settingList(角色/纹理/粒子/音效)
AdvImportBook    importGridList: List<AdvImportScenarioSheet>
AdvImportScenarioSheet  name = "…/100106.xlsx:Start"  rows: List<StringGridRow>
StringGridRow    strings[]  ← Excel 的一行
```

剧本表列：`// / // TAP / Command / Arg1 / Arg2 / 表示タグ / モーション名 / 表情 / Arg3..Arg7 /
WaitType / Text / PageCtrl / CueId / Voice / WindowType`

台词行形如：

```
Command=Character  Arg1=kazuma  Arg2=00_Anger_01$20_Expression_Serious_01
Text=危ないっ！　エーリカ！！   Voice=3100001.cue
```

导出结果（`out/story/*.md`）：

| book | 行数 | 台词 |
|---|---|---|
| 100106.book | 272 | 71 |
| 42411201.book | 321 | 112 |
| 822041.book | 297 | 110 |
| 6122023.book | 96 | 30 |
| 6011524.book | 84 | 27 |

⚠️ 说话人是 romaji 键（kazuma / megumin / aqua…），**没有 romaji→日文对照表**：
`character` 表的 name 是 `ASSET_CHARA_NAME_<id>` 这类 key，与 Utage 的键无关。

## 四、剧情可读性现状

catalog 里剧情资产 2,746 条（`.asset` 1,433 = ADV 剧本，`.prefab` 1,308 = 立绘/背景/演出），
本地只有 196 条 → **本快照只能读 5 章**。要全量剧本只能靠官方离线版（`jp.co.sumzap.pj0016` 等）。
