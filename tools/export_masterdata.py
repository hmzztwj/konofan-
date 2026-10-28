# -*- coding: utf-8 -*-
"""把已解密的 MasterData JSON 导出成 CSV，并生成一份数据总览 markdown。

输入: F:\\python_work\\逆向\\out\\masterdata\\*.json（tools/decrypt_masterdata.py 的产物）
输出: F:\\python_work\\逆向\\out\\masterdata_csv\\<表名>.csv   每表一个
      F:\\python_work\\逆向\\out\\数据总览.md                 人看的摘要
"""
import csv
import json
import os
import re

SRC = r"F:\python_work\逆向\out\masterdata"
DST = r"F:\python_work\逆向\out\masterdata_csv"
DIGEST = r"F:\python_work\逆向\out\数据总览.md"


def load(name):
    with open(os.path.join(SRC, name + ".json"), encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        return d.get("master") or [], d.get("version"), d.get("status")
    return d, None, None


def rows_of(name):
    m, v, s = load(name)
    out = []
    for r in m:
        if isinstance(r, dict):
            out.append(r)
    return out


def main():
    os.makedirs(DST, exist_ok=True)
    names = sorted(n[:-5] for n in os.listdir(SRC) if n.endswith(".json"))
    texts = {}
    for tbl in ("text", "assetname", "clienttext"):
        for r in rows_of(tbl):
            tid = r.get("id")
            if tid:
                texts[str(tid)] = r.get("text_japanese") or r.get("text") or ""
    def t(k):
        if k is None:
            return ""
        k = str(k)
        return texts.get(k, k)

    total_rows = 0
    table_rows = []
    for n in names:
        rows = rows_of(n)
        total_rows += len(rows)
        table_rows.append((n, len(rows)))
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        if not keys:
            continue
        with open(os.path.join(DST, n + ".csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                            for k, v in r.items()})

    # ---------- 总览 ----------
    L = []
    L.append("# このファン MasterData 数据总览\n")
    L.append(f"- 表数量：**{len(names)}**")
    L.append(f"- 记录总数：**{total_rows:,}**")
    L.append(f"- 每表 CSV：`out/masterdata_csv/`（UTF-8 BOM，Excel 可直接开）")
    L.append(f"- 原始 JSON：`out/masterdata/`\n")

    L.append("## 一、体量最大的表\n")
    L.append("| 表 | 行数 |\n|---|---:|")
    for n, c in sorted(table_rows, key=lambda x: -x[1])[:15]:
        L.append(f"| {n} | {c:,} |")

    L.append("\n## 二、角色（character: %d）\n" % len(rows_of("character")))
    L.append("| id | 名字 | 武器 | 生日 |\n|---:|---|---|---|")
    for r in rows_of("character"):
        L.append(f"| {r.get('id')} | {t(r.get('name'))} | {r.get('weapon_type','')} | {r.get('birthday','')} |")

    L.append("\n## 三、主线剧情（story_main: %d）\n" % len(rows_of("story_main")))
    parts = {str(r.get("part")): t(r.get("title")) for r in rows_of("main_quest_part")}
    L.append("**篇章**：" + "、".join(f"{k}={v}" for k, v in parts.items()) + "\n")
    L.append("| id | 篇 | 章 | 标题 |\n|---:|---|---:|---|")
    for r in rows_of("story_main"):
        L.append(f"| {r.get('id')} | {parts.get(str(r.get('part')), r.get('part'))} | "
                 f"{r.get('chapter')} | {t(r.get('title_text'))} |")

    ev = rows_of("story_event")
    mem = rows_of("story_member")
    L.append(f"\n## 四、活动剧情（story_event: {len(ev)}）与角色剧情（story_member: {len(mem)}）\n")
    L.append("| 类型 | 数量 | 示例标题 |\n|---|---:|---|")
    L.append(f"| 活动剧情 | {len(ev)} | {t(ev[0].get('title_text')) if ev else ''} |")
    L.append(f"| 角色剧情 | {len(mem)} | {t(mem[0].get('title_text')) if mem else ''} |")
    L.append(f"| 回忆（story_reminiscence）| {len(rows_of('story_reminiscence'))} | |")

    L.append("\n## 五、图鉴与影音\n")
    gm = rows_of("gallery_movie")
    gs = rows_of("gallery_still")
    gg = rows_of("gallery_group")
    bgm = rows_of("bgm")
    voice = rows_of("voice")
    L.append(f"- 图鉴分组 `gallery_group`：{len(gg)}")
    L.append(f"- 图鉴静图 `gallery_still`：{len(gs)}")
    L.append(f"- 图鉴影片 `gallery_movie`：{len(gm)}")
    for r in gm:
        L.append(f"  - {t(r.get('title'))}（story {r.get('story_id')}）")
    L.append(f"- BGM `bgm`：{len(bgm)} 条，cpk 名示例：" + "、".join(r.get("cpk_name", "") for r in bgm[:6]))
    L.append(f"- 语音 `voice`：{len(voice)} 条（按角色分组见 CSV）")

    L.append("\n## 六、战斗与养成数据\n")
    for n in ["battle_enemy", "battle_wave", "skill_pa", "skill_sp", "skill_ac", "equip_weapon",
              "equip_accessory", "character_piece", "dungeon_stage", "mainquest_stage",
              "huntingquest_stage", "fame_quest_stage", "expedition_drop"]:
        L.append(f"- `{n}`：{len(rows_of(n)):,} 行")

    L.append("\n## 七、运营/活动\n")
    for n in ["gacha", "campaign", "event_config", "exchange_item", "shop_item", "pack",
              "mission", "loginbonus", "roulette_loginbonus", "event_mission"]:
        L.append(f"- `{n}`：{len(rows_of(n)):,} 行")

    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"[+] CSV {len(names)} 个 -> {DST}")
    print(f"[+] 总行数 {total_rows:,}，文本表 {len(texts):,} 条")
    print(f"[+] 总览 -> {DIGEST}")


if __name__ == "__main__":
    main()
